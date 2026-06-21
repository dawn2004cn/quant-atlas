from __future__ import annotations
"""China A-share session dates (SSE calendar via AkShare), with safe fallbacks."""


import threading
from datetime import date as date_type

_cache_lock = threading.Lock()
_loaded: bool = False
_trade_dates: frozenset[str] | None = None


def _parse_iso_date(ds: str) -> date_type | None:
    s = (ds or "")[:10]
    if len(s) != 10 or s[4] != "-" or s[7] != "-":
        return None
    try:
        return date_type(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None


def is_weekday_calendar(ds: str) -> bool:
    """Mon–Fri on civil calendar（仅剔除周末，不含法定节假日）。"""
    d = _parse_iso_date(ds)
    if d is None:
        return False
    return d.weekday() < 5


def _get_sse_trade_dates() -> frozenset[str] | None:
    global _loaded, _trade_dates
    with _cache_lock:
        if _loaded:
            return _trade_dates
        _loaded = True
        try:
            import akshare as ak

            df = ak.tool_trade_date_hist_sina()
            col = df["trade_date"].astype(str).str.slice(0, 10)
            _trade_dates = frozenset(col.tolist())
        except Exception:
            _trade_dates = None
        return _trade_dates


def is_cn_equity_trading_day(date_str: str) -> bool:
    """
    True 表示上交所日历中的交易日（与沪深 A 股常规休市对齐）。
    AkShare 不可用时退化为「仅剔除周末」；日期超出日历上下限时亦同。
    """
    ds = (date_str or "")[:10]
    if len(ds) != 10:
        return False

    cal = _get_sse_trade_dates()
    if cal:
        if ds in cal:
            return True
        mn, mx = min(cal), max(cal)
        if ds < mn or ds > mx:
            return is_weekday_calendar(ds)
        return False
    return is_weekday_calendar(ds)
