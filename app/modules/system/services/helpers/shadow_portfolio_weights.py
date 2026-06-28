from __future__ import annotations

"""Estimate position weight percentages from quotes (for shadow mirroring)."""

from typing import Any

from app.domain.enums import MarketCode


def build_weights_from_watchlist(
    *,
    user_id: int,
    watchlist_service: Any,
    market_service: Any,
    market: MarketCode = MarketCode.CN,
    default_shares: float = 100.0,
) -> dict[str, float]:
    """Build symbol -> weight % from user watchlist quotes (portfolio detail convention)."""
    if not user_id or watchlist_service is None or market_service is None:
        return {}
    try:
        symbols = [
            str(s).strip()
            for s in watchlist_service.list_symbols(user_id=user_id)
            if str(s).strip()
        ]
    except Exception:
        return {}
    if not symbols:
        return {}
    try:
        stocks = list(market_service.list_quotes(market, symbols) or [])
    except Exception:
        return {}
    stock_map = {str(s.get("code") or s.get("symbol") or ""): s for s in stocks}
    total_value = 0.0
    values: dict[str, float] = {}
    for sym in symbols:
        row = stock_map.get(sym) or {}
        try:
            price = float(row.get("price") or 0)
        except (TypeError, ValueError):
            price = 0.0
        if price <= 0:
            continue
        value = price * default_shares
        values[sym.upper()] = value
        total_value += value
    if total_value <= 0:
        return {}
    return {sym: round(val / total_value * 100.0, 2) for sym, val in values.items()}


def merge_position_weights(*maps: dict[str, float] | None) -> dict[str, float]:
    """Later maps override earlier keys."""
    out: dict[str, float] = {}
    for m in maps:
        if not m:
            continue
        for k, v in m.items():
            key = str(k).strip().upper()
            if key and v is not None:
                out[key] = float(v)
    return out


def build_cost_basis_map(
    holdings: list[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Symbol (upper) -> avg_cost / pnl_pct from portfolio trade ledger."""
    out: dict[str, dict[str, Any]] = {}
    for row in holdings or []:
        code = str(row.get("code") or row.get("symbol") or "").strip().upper()
        if not code:
            continue
        out[code] = {
            "avg_cost": float(row.get("avg_cost") or 0),
            "pnl_pct": float(row.get("pnl_pct") or 0),
            "shares": int(row.get("shares") or 0),
            "cost": float(row.get("cost") or 0),
        }
    return out


def estimate_position_weights(
    holding_codes: list[str],
    quotes: list[dict[str, Any]] | None,
    *,
    default_shares: float = 100.0,
) -> dict[str, float]:
    """Map symbol -> exposure % using price * default_shares (same convention as portfolio snapshot)."""
    quote_map: dict[str, dict[str, Any]] = {}
    for row in quotes or []:
        code = str(row.get("code") or row.get("symbol") or "").strip().upper()
        if code:
            quote_map[code] = row

    values: dict[str, float] = {}
    total = 0.0
    for raw in holding_codes:
        sym = str(raw).strip().upper()
        if not sym:
            continue
        row = quote_map.get(sym) or {}
        try:
            price = float(row.get("price") or row.get("close") or 0)
        except (TypeError, ValueError):
            price = 0.0
        if price <= 0:
            continue
        value = price * default_shares
        values[sym] = value
        total += value

    if total <= 0:
        return {}
    return {sym: round(val / total * 100.0, 2) for sym, val in values.items()}
