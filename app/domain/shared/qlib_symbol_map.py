from __future__ import annotations

"""平台标的 ↔ Qlib instrument（domain 纯逻辑）。"""

from app.domain.enums import MarketCode
from app.domain.shared.symbol_normalizer import SymbolNormalizer


def cn_to_qlib_instrument(symbol: str) -> str:
    code = SymbolNormalizer.normalize_code(symbol)
    mid = SymbolNormalizer.market_id(symbol)
    prefix = "SH" if mid == 1 else ("BJ" if mid == 2 else "SZ")
    return f"{prefix}{code}"


def to_qlib_instrument(symbol: str, market: MarketCode) -> str:
    if market is MarketCode.CN:
        return cn_to_qlib_instrument(symbol)
    return symbol.strip().upper()


def qlib_instrument_to_symbol(instrument: str, market: MarketCode) -> str:
    u = (instrument or "").strip().upper()
    if market is not MarketCode.CN:
        return u
    if len(u) >= 8 and u.startswith("SH") and u[2:].isdigit():
        return u[2:]
    if len(u) >= 8 and u.startswith("SZ") and u[2:].isdigit():
        return u[2:]
    return SymbolNormalizer.normalize_code(instrument)
