from __future__ import annotations
"""Mapper for Tencent quote payload to domain entities.

``qt.gtimg.cn`` text fields are delimited by ``~``; amount ``f37`` is in **10k yuan**, total market cap ``f45`` is in **100M yuan**,
volume ``f6`` is in **hands** (converted to shares ``×100`` for storage).
"""


from datetime import datetime

from app.domain.entities import StockQuote
from app.domain.enums import MarketCode


def _split_gtimg_fields(line: str) -> list[str]:
    if '="' not in line:
        return []
    rest = line.split('="', 1)[1]
    inner = rest.split('"', 1)[0] if '"' in rest else rest.rstrip(";\n")
    return inner.split("~")


def _f(items: list[str], idx: int, default: float = 0.0) -> float:
    try:
        if idx < 0 or idx >= len(items):
            return default
        raw = (items[idx] or "").strip()
        if not raw:
            return default
        return float(raw)
    except (TypeError, ValueError):
        return default


class TencentQuoteMapper:
    """Parse raw Tencent quote payload into StockQuote objects."""

    @staticmethod
    def parse_payload(payload: str, market: MarketCode) -> list[StockQuote]:
        quotes: list[StockQuote] = []
        if not payload:
            return quotes
        for line in payload.strip().split("\n"):
            quote = TencentQuoteMapper.parse_line(line, market)
            if quote is not None:
                quotes.append(quote)
        return quotes

    @staticmethod
    def parse_line(line: str, market: MarketCode) -> StockQuote | None:
        items = _split_gtimg_fields(line)
        if len(items) < 40:
            return None
        try:
            code = (items[2] or "").strip()
            if not code:
                return None
            name = items[1] or code
            price = _f(items, 3)
            prev_close = _f(items, 4)
            open_price = _f(items, 5)
            vol_hands = _f(items, 6)
            volume_shares = vol_hands * 100.0
            change_amount = _f(items, 31)
            change_pct = _f(items, 32)
            high_price = _f(items, 33)
            low_price = _f(items, 34)
            amount_wan = _f(items, 37)
            amount_yuan = amount_wan * 10_000.0
            turnover_pct = _f(items, 38)
            pe = _f(items, 39)
            amplitude = _f(items, 43)
            total_cap_yi = _f(items, 45)
            total_mcap_yuan = total_cap_yi * 1e8
            pb = _f(items, 46)
            volume_ratio = _f(items, 64)
            return StockQuote(
                code=code,
                name=name,
                market=market,
                price=price,
                change_pct=change_pct,
                volume=volume_shares,
                amount=amount_yuan,
                turnover=turnover_pct,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                source="tencent",
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                change_amount=change_amount,
                prev_close=prev_close,
                volume_ratio=volume_ratio,
                amplitude=amplitude,
                pe=pe,
                pb=pb,
                total_market_cap=total_mcap_yuan,
                industry="",
            )
        except (ValueError, IndexError):
            return None


_default_mapper: TencentQuoteMapper | None = None


def get_tencent_quote_mapper() -> TencentQuoteMapper:
    """Get default mapper."""
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = TencentQuoteMapper()
    return _default_mapper


__all__ = ["TencentQuoteMapper", "get_tencent_quote_mapper", "_split_gtimg_fields", "_f"]
