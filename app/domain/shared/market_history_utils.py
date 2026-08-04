from __future__ import annotations

"""Pure helpers for OHLCV history rows."""

from typing import Any


def clamp_history_date_range(
    start: str,
    end: str,
    *,
    max_points: int | None = None,
    chart_width: int | None = None,
    count: int | None = None,
    max_calendar_days: int = 800,
) -> tuple[str, str]:
    """Narrow calendar window before DB fetch when the client caps output points."""
    from datetime import date, datetime, timedelta

    from app.domain.shared.bar_sampler import resolve_sample_target

    target = resolve_sample_target(
        max_points if max_points and max_points > 0 else None,
        chart_width if chart_width and chart_width > 0 else None,
    )
    if target is None and count and count > 0:
        target = int(count)
    if not target:
        return start[:10], end[:10]

    try:
        end_dt = datetime.strptime(end[:10], "%Y-%m-%d").date()
        start_dt = datetime.strptime(start[:10], "%Y-%m-%d").date()
    except ValueError:
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=min(max_calendar_days, int(target * 2.2) + 40))
        return start_dt.isoformat(), end_dt.isoformat()

    cal_days = min(max_calendar_days, int(target * 2.2) + 40)
    if (end_dt - start_dt).days > cal_days:
        start_dt = end_dt - timedelta(days=cal_days)
    return start_dt.isoformat(), end_dt.isoformat()


def filter_sort_history(
    history: list[dict[str, Any]],
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    """Keep only [start, end] by trade date and sort ascending."""
    if not history:
        return []
    s0, e0 = start[:10], end[:10]
    out: list[dict[str, Any]] = []
    for h in history:
        d = h.get("date") or h.get("Date")
        if d is None:
            continue
        ds = str(d)[:10]
        if ds < s0 or ds > e0:
            continue
        out.append(h)
    out.sort(key=lambda x: str(x.get("date") or x.get("Date"))[:10])
    return out
