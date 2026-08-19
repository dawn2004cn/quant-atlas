"""A-share trading session windows for TDX realtime quote feed."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

_SH = ZoneInfo("Asia/Shanghai")

# 用户指定：集合竞价+连续竞价 9:15-11:30；下午 13:00-15:00
_MORNING_OPEN = time(9, 15)
_MORNING_CLOSE = time(11, 30)
_AFTERNOON_OPEN = time(13, 0)
_AFTERNOON_CLOSE = time(15, 0)


def cn_now() -> datetime:
    return datetime.now(tz=_SH)


def is_cn_tdx_quote_session(dt: datetime | None = None) -> bool:
    """True during A-share quote-active window (weekday 9:15-11:30 / 13:00-15:00 CST)."""
    now = dt or cn_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=_SH)
    else:
        now = now.astimezone(_SH)
    if now.weekday() >= 5:
        return False
    t = now.time()
    in_morning = _MORNING_OPEN <= t <= _MORNING_CLOSE
    in_afternoon = _AFTERNOON_OPEN <= t <= _AFTERNOON_CLOSE
    return in_morning or in_afternoon


def cn_session_trade_date(dt: datetime | None = None) -> str:
    """YYYY-MM-DD for the current CN session calendar day."""
    now = dt or cn_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=_SH)
    else:
        now = now.astimezone(_SH)
    return now.strftime("%Y-%m-%d")


__all__ = [
    "cn_now",
    "cn_session_trade_date",
    "is_cn_tdx_quote_session",
]
