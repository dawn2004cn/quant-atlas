from __future__ import annotations
"""Datetime normalization and arithmetic utilities."""


import re
from datetime import datetime, timedelta, time as pytime
from typing import Any
from zoneinfo import ZoneInfo


def is_trading_time_cn(dt: datetime | None = None) -> bool:
    """Check if the given time is within A-share trading hours."""
    now = dt or datetime.now()
    if now.weekday() >= 5:
        return False
    curr_time = now.time()
    morning_start = pytime(9, 15)
    morning_end = pytime(11, 35)
    afternoon_start = pytime(13, 0)
    afternoon_end = pytime(15, 30)
    return (morning_start <= curr_time <= morning_end) or (afternoon_start <= curr_time <= afternoon_end)


def is_cn_trading_time(dt: datetime | None = None) -> bool:
    """Alias for is_trading_time_cn."""
    return is_trading_time_cn(dt)


def is_trading_date(d: datetime) -> bool:
    """Check if the given date is a trading day (not weekend)."""
    return d.weekday() < 5


def norm_date(v: Any) -> str:
    """Normalize various date formats to YYYY-MM-DD."""
    s = str(v or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    if re.match(r"^\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s[:10]


def add_months(d: datetime, months: int) -> datetime:
    """Add months to a datetime object, safely handling month overflow."""
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, 28)
    return datetime(y, m, day)


def default_history_window(days: int = 365) -> tuple[str, str]:
    """Return (start_date, end_date) tuple for history queries.

    This is a pure utility function with no infrastructure dependencies.
    """
    end = datetime.now().date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


_SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def shanghai_now() -> datetime:
    """Return current Shanghai time (UTC+8)."""
    return datetime.now(tz=_SHANGHAI_TZ)


def shanghai_today() -> str:
    """Return today's date in Shanghai timezone as YYYY-MM-DD."""
    return datetime.now(tz=_SHANGHAI_TZ).strftime("%Y-%m-%d")