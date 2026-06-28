from __future__ import annotations

"""Convert domain quote entities to canonical API payloads."""

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.dto.market_data_dto import QuoteDTO

from app.domain.entities import StockQuote
from app.domain.shared.symbol_normalizer import SymbolNormalizer

_CHANGE_PCT_KEYS = ("change_pct", "pct_chg", "pct_change", "change_percent", "chenge")
_CHANGE_AMOUNT_KEYS = ("change_amount", "change", "chg", "chenge_amount")
_SYMBOL_KEYS = ("symbol", "code", "ticker", "stock_code")


def _first_float(data: dict[str, Any], keys: tuple[str, ...], default: float = 0.0) -> float:
    for key in keys:
        if key not in data or data[key] is None:
            continue
        try:
            return float(data[key])
        except (TypeError, ValueError):
            continue
    return default


def _first_str(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def canonical_quote_payload(
    raw: dict[str, Any],
    *,
    market: str | None = None,
) -> dict[str, Any]:
    """Normalize quote dict field names for API consumers (symbol/code, change_pct)."""
    out = dict(raw)
    market_code = str(market or out.get("market") or "CN").strip().upper()
    symbol_raw = _first_str(out, _SYMBOL_KEYS)
    if symbol_raw:
        canonical = SymbolNormalizer.to_db_code(symbol_raw, market_code)
        out["code"] = canonical
        out["symbol"] = canonical
        out["code6"] = SymbolNormalizer.to_code6(canonical)
    change_pct = _first_float(out, _CHANGE_PCT_KEYS)
    change_amount = _first_float(out, _CHANGE_AMOUNT_KEYS)
    out["change_pct"] = round(change_pct, 6)
    out["change_amount"] = round(change_amount, 6)
    out["change"] = out["change_amount"]
    if market_code:
        out["market"] = market_code
    return out


def canonical_quote_list(
    items: list[dict[str, Any]],
    *,
    market: str | None = None,
) -> list[dict[str, Any]]:
    """Normalize a list of quote dicts."""
    return [canonical_quote_payload(item, market=market) for item in items]


_PANORAMA_LIST_KEYS = ("gainers", "losers", "amounts", "turnovers")


def canonical_panorama_dict(
    data: dict[str, Any],
    *,
    market: str | None = None,
) -> dict[str, Any]:
    """Normalize panorama ranking lists (symbol/code, change_pct)."""
    out = dict(data)
    market_code = str(market or out.get("market") or "CN").strip().upper()
    for key in _PANORAMA_LIST_KEYS:
        items = out.get(key)
        if not isinstance(items, list):
            continue
        rows: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                raw = item
            elif hasattr(item, "model_dump"):
                raw = item.model_dump()
            else:
                raw = dict(item)
            rows.append(canonical_quote_payload(raw, market=market_code))
        out[key] = rows
    out["market"] = market_code
    return out


def panorama_row_to_quote_dto(raw: dict[str, Any], *, market: str) -> QuoteDTO:
    """Build domain QuoteDTO from a provider ranking row."""
    from app.domain.dto.market_data_dto import QuoteDTO

    c = canonical_quote_payload(raw, market=market)
    return QuoteDTO(
        code=str(c.get("code") or c.get("symbol") or ""),
        name=str(c.get("name") or ""),
        price=float(c.get("price", 0) or 0),
        change_pct=float(c.get("change_pct", 0) or 0),
        change_amount=float(c.get("change_amount", 0) or 0),
        volume=int(c.get("volume", 0) or 0),
        amount=float(c.get("amount", 0) or 0),
        turnover=float(c.get("turnover", 0) or 0),
    )


def quote_to_dict(quote: StockQuote) -> dict[str, Any]:
    payload = asdict(quote)
    payload["market"] = quote.market.value
    return canonical_quote_payload(payload, market=quote.market.value)
