from __future__ import annotations
"""Assess K-line session coverage for analysis confidence."""

from datetime import date, timedelta
from typing import Callable

TradingDayFn = Callable[[str], bool]


def _parse_iso(ds: str) -> date | None:
    s = (ds or "")[:10]
    if len(s) != 10:
        return None
    try:
        return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None


def _iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _weekday_trading_day(ds: str) -> bool:
    d = _parse_iso(ds)
    return d is not None and d.weekday() < 5


def iter_sessions(start: date, end: date, is_trading_day: TradingDayFn) -> list[str]:
    out: list[str] = []
    cur = start
    while cur <= end:
        ds = _iso(cur)
        if is_trading_day(ds):
            out.append(ds)
        cur += timedelta(days=1)
    return out


def count_stale_sessions(latest: date, as_of: date, is_trading_day: TradingDayFn) -> int:
    if latest >= as_of:
        return 0
    sessions = iter_sessions(latest + timedelta(days=1), as_of, is_trading_day)
    return len(sessions)


def assess_bar_coverage(
    bar_dates: list[str],
    *,
    lookback_days: int = 30,
    as_of: date | None = None,
    is_trading_day: TradingDayFn | None = None,
) -> dict[str, object]:
    """Compare expected vs actual trading sessions in lookback window."""
    fn = is_trading_day or _weekday_trading_day
    today = as_of or date.today()
    start = today - timedelta(days=max(lookback_days, 1))
    expected = iter_sessions(start, today, fn)
    expected_set = set(expected)
    normalized = sorted({str(d)[:10] for d in bar_dates if d})
    actual_dates = [d for d in normalized if d in expected_set]
    expected_count = len(expected)
    actual_count = len(actual_dates)
    coverage_pct = round(actual_count / expected_count * 100.0, 1) if expected_count else 0.0

    latest = _parse_iso(normalized[-1]) if normalized else None
    latest_str = _iso(latest) if latest else ""
    stale_gap = count_stale_sessions(latest, today, fn) if latest else expected_count

    if expected_count == 0:
        level = "unknown"
        warning = "无法计算覆盖度（交易日历不可用）。"
        penalty = 0.15
    elif coverage_pct >= 92 and stale_gap <= 1:
        level = "good"
        warning = ""
        penalty = 0.0
    elif coverage_pct >= 75 and stale_gap <= 3:
        level = "partial"
        warning = f"近 {lookback_days} 日 K 线覆盖 {coverage_pct:.0f}%，结论置信度可能略降。"
        penalty = 0.08
    else:
        level = "poor"
        missing = max(expected_count - actual_count, 0)
        warning = (
            f"近 {lookback_days} 日仅覆盖 {actual_count}/{expected_count} 个交易日"
            f"（{coverage_pct:.0f}%），缺失约 {missing} 根 K 线"
            f"{f'，最新数据 {latest_str}' if latest_str else ''}。"
            "本结论基于不完整数据，置信度低。"
        )
        penalty = 0.22 if stale_gap <= 5 else 0.3

    return {
        "lookback_days": lookback_days,
        "expected_sessions": expected_count,
        "actual_sessions": actual_count,
        "coverage_pct": coverage_pct,
        "latest_bar_date": latest_str,
        "stale_session_gap": stale_gap,
        "level": level,
        "warning": warning,
        "confidence_penalty": penalty,
    }


__all__ = ["assess_bar_coverage", "TradingDayFn"]
