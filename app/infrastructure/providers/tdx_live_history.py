"""Merge TDX lday history with intraday quote from Redis (today's bar)."""

from __future__ import annotations

from typing import Any

from app.domain.shared.cn_trading_session import cn_session_trade_date, is_cn_tdx_quote_session


def _bar_date(bar: dict[str, Any]) -> str:
    raw = bar.get("date") or bar.get("Date") or ""
    return str(raw)[:10]


def merge_intraday_bar(
    bars: list[dict[str, Any]],
    quote: dict[str, Any] | None,
    *,
    trade_date: str | None = None,
) -> list[dict[str, Any]]:
    """Append or update today's OHLCV using live TDX/Redis quote."""
    if not quote or not is_cn_tdx_quote_session():
        return bars
    td = (trade_date or cn_session_trade_date())[:10]
    price = float(quote.get("price") or 0)
    if price <= 0:
        return bars
    open_p = float(quote.get("open_price") or quote.get("open") or price)
    high_p = float(quote.get("high_price") or quote.get("high") or price)
    low_p = float(quote.get("low_price") or quote.get("low") or price)
    vol = float(quote.get("volume") or quote.get("vol") or 0)
    amt = float(quote.get("amount") or 0)
    live = {
        "date": td,
        "open": open_p,
        "high": max(high_p, open_p, price),
        "low": min(low_p, open_p, price) if low_p > 0 else min(open_p, price),
        "close": price,
        "volume": vol,
        "amount": amt,
        "source": str(quote.get("source") or "tdx_live"),
    }
    if not bars:
        return [live]
    out = [dict(b) for b in bars]
    last_date = _bar_date(out[-1])
    if last_date == td:
        prev = out[-1]
        out[-1] = {
            **prev,
            "open": float(prev.get("open") or open_p),
            "high": max(float(prev.get("high") or 0), live["high"], price),
            "low": min(
                float(prev.get("low") or price) if float(prev.get("low") or 0) > 0 else price,
                live["low"],
                price,
            ),
            "close": price,
            "volume": max(float(prev.get("volume") or 0), vol),
            "amount": max(float(prev.get("amount") or 0), amt),
            "source": "tdx_lday+live",
        }
    elif last_date < td:
        out.append(live)
    return out


__all__ = ["merge_intraday_bar"]
