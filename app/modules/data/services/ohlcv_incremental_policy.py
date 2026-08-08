from __future__ import annotations
"""Idempotent incremental sync: overlap window, dedupe, multi-store cursor."""

from datetime import date, timedelta
from typing import Any, Callable

from app.core.runtime_config import get_runtime_int

RowFilter = Callable[[list[dict[str, Any]], str | None], list[dict[str, Any]]]


def incremental_overlap_days() -> int:
    """Re-sync last N calendar days on each incremental run (corrections + anti-gap)."""
    return max(
        0,
        get_runtime_int(
            "TIMESERIES_INCREMENTAL_OVERLAP_DAYS",
            get_runtime_int("TDX_SYNC_INCREMENTAL_OVERLAP_DAYS", 5),
        ),
    )


def min_latest_date_str(*values: str | None) -> str | None:
    """Earliest latest date string among stores (lagging store drives incremental cursor)."""
    parsed = [parse_trade_date(v) for v in values if v]
    parsed = [d for d in parsed if d is not None]
    if not parsed:
        return None
    return min(parsed).isoformat()


def parse_trade_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()[:10]
    if len(s) < 10:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def incremental_cursor_start(
    latest: date | None,
    end_d: date,
    lookback_days: int,
    *,
    overlap_days: int | None = None,
) -> date | None:
    """
    Compute inclusive sync start date.

    - No rows in store: ``end_d - lookback_days``.
    - Has latest: ``latest - overlap`` (re-write overlap for idempotency).
    - Returns ``None`` only when ``end_d`` is before cursor (already fresh).
    """
    ov = incremental_overlap_days() if overlap_days is None else max(0, overlap_days)
    if latest is None:
        return end_d - timedelta(days=lookback_days)
    start = latest - timedelta(days=ov)
    if start > end_d:
        return None
    return start


def filter_rows_incremental(
    rows: list[dict[str, Any]],
    latest: str | None,
    *,
    overlap_days: int | None = None,
) -> list[dict[str, Any]]:
    """Keep bars on/after ``latest - overlap`` (TDX dayk / timeseries)."""
    if not rows:
        return []
    latest_d = parse_trade_date(latest)
    if latest_d is None:
        return rows
    ov = incremental_overlap_days() if overlap_days is None else max(0, overlap_days)
    cutoff = (latest_d - timedelta(days=ov)).isoformat()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = str(r.get("date") or "")[:10]
        if d and d >= cutoff:
            out.append(r)
    return out


def make_incremental_row_filter(
    overlap_days: int | None = None,
) -> RowFilter:
    ov = overlap_days

    def _filter(rows: list[dict[str, Any]], latest: str | None) -> list[dict[str, Any]]:
        return filter_rows_incremental(rows, latest, overlap_days=ov)

    return _filter


def dedupe_bars_by_date(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Last row wins per ``date`` (stable sort by date)."""
    by_date: dict[str, dict[str, Any]] = {}
    for r in bars:
        d = str(r.get("date") or r.get("trade_date") or "")[:10]
        if not d:
            continue
        by_date[d] = r
    return [by_date[k] for k in sorted(by_date)]


def tdx_lday_tail_bars(mode: str, latest: str | None) -> int | None:
    """Enough tail bars to cover overlap window + buffer."""
    if mode in ("full", "backfill") or not latest:
        return None
    ov = incremental_overlap_days()
    base = get_runtime_int("TDX_SYNC_LDAY_TAIL", 120)
    return max(60, base, ov * 4 + 30)


def verify_bars_cover_window(
    bars: list[dict[str, Any]],
    start_d: date,
    end_d: date,
    *,
    code: str = "",
) -> dict[str, Any]:
    """Light check: TDX returned bars intersecting [start_d, end_d]."""
    if not bars:
        return {"ok": False, "reason": "empty_bars", "code": code}
    dates = [str(b.get("date") or "")[:10] for b in bars if b.get("date")]
    if not dates:
        return {"ok": False, "reason": "no_dates", "code": code}
    max_d = max(dates)
    min_d = min(dates)
    start_s = start_d.isoformat()
    end_s = end_d.isoformat()
    if max_d < start_s:
        return {"ok": False, "reason": "max_before_start", "code": code, "min": min_d, "max": max_d}
    return {"ok": True, "code": code, "min": min_d, "max": max_d, "count": len(bars)}
