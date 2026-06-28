from __future__ import annotations
"""Align events (news, signals) to a unified daily market clock for chart overlays."""

from datetime import date, datetime, timedelta
from typing import Any
from collections.abc import Callable

from app.domain.shared.symbol_normalizer import SymbolNormalizer

TradingDayFn = Callable[[str], bool]


def _parse_event_datetime(raw: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.isdigit():
        try:
            ts = int(text)
            if ts > 10_000_000_000:
                ts //= 1000
            return datetime.fromtimestamp(ts)
        except (OSError, OverflowError, ValueError):
            return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(text[: len(fmt.replace("%", "0"))], fmt)
        except ValueError:
            continue
    if len(text) >= 10 and text[4] in "-/" and text[7] in "-/":
        try:
            return datetime.strptime(text[:10].replace("/", "-"), "%Y-%m-%d")
        except ValueError:
            return None
    return None


def _weekday_trading_day(date_str: str) -> bool:
    ds = (date_str or "")[:10]
    try:
        d = datetime.strptime(ds, "%Y-%m-%d").date()
    except ValueError:
        return False
    return d.weekday() < 5


def _iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _walk_to_trading_day(
    start: date,
    *,
    is_trading_day: TradingDayFn,
    max_steps: int = 400,
) -> date:
    cur = start
    for _ in range(max_steps):
        if is_trading_day(_iso(cur)):
            return cur
        cur -= timedelta(days=1)
    return start


def _session_date_for_cn(dt: datetime, is_trading_day: TradingDayFn) -> date:
    """Map civil timestamp to the A-share daily bar key (pre-open -> prior session)."""
    civil = dt.date()
    if dt.hour < 9 or (dt.hour == 9 and dt.minute < 30):
        civil -= timedelta(days=1)
    return _walk_to_trading_day(civil, is_trading_day=is_trading_day)


def _session_date_default(dt: datetime, is_trading_day: TradingDayFn) -> date:
    civil = dt.date()
    if dt.hour < 9:
        civil -= timedelta(days=1)
    return _walk_to_trading_day(civil, is_trading_day=is_trading_day)


class DateAligner:
    """Force-align timestamps to ``market_time_slot`` for UI overlays."""

    @staticmethod
    def default_trading_day_fn(market: str) -> TradingDayFn:
        return _weekday_trading_day

    @staticmethod
    def align_daily(
        published_at: str,
        *,
        market: str = "CN",
        symbol: str | None = None,
        is_trading_day: TradingDayFn | None = None,
    ) -> dict[str, str]:
        mkt = (market or "CN").upper()
        fn = is_trading_day or DateAligner.default_trading_day_fn(mkt)
        dt = _parse_event_datetime(published_at)
        if dt is None:
            return {
                "date": "",
                "granularity": "day",
                "market": mkt,
                "symbol": SymbolNormalizer.to_db_code(symbol) if symbol else "",
            }
        if mkt == "CN":
            slot_date = _session_date_for_cn(dt, fn)
        else:
            slot_date = _session_date_default(dt, fn)
        norm_symbol = ""
        if symbol:
            norm_symbol = SymbolNormalizer.to_db_code(symbol) if mkt == "CN" else str(symbol).strip()
        return {
            "date": _iso(slot_date),
            "granularity": "day",
            "market": mkt,
            "symbol": norm_symbol,
        }

    @staticmethod
    def attach_market_time_slot(
        item: dict[str, Any],
        *,
        market: str,
        symbol: str | None = None,
        is_trading_day: TradingDayFn | None = None,
    ) -> dict[str, Any]:
        out = dict(item)
        published = str(
            out.get("published_at")
            or out.get("date")
            or out.get("time")
            or out.get("trade_date")
            or ""
        )
        sym = symbol or out.get("symbol") or out.get("code")
        out["market_time_slot"] = DateAligner.align_daily(
            published,
            market=market,
            symbol=str(sym) if sym else None,
            is_trading_day=is_trading_day,
        )
        return out


__all__ = ["DateAligner", "TradingDayFn"]
