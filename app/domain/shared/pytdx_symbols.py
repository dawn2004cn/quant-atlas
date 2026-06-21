from __future__ import annotations
"""A 股代码 ↔ pytdx market 参数（domain 纯逻辑）。"""

from app.domain.shared.symbol_normalizer import SymbolNormalizer


def market_code_from_symbol(symbol: str) -> int:
    """pytdx 标准行情 market：0=深圳，1=上海。"""
    cn = SymbolNormalizer.to_db_code(symbol, market="CN")
    raw = cn.split(":", 1)[1] if ":" in cn else cn
    mkt = raw[:2].lower() if len(raw) >= 2 else "sz"
    if mkt == "sh" or raw.startswith("6"):
        return 1
    return 0


def code6_from_symbol(symbol: str) -> str:
    cn = SymbolNormalizer.to_db_code(symbol, market="CN")
    raw = cn.split(":", 1)[1] if ":" in cn else cn
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[-6:].zfill(6)


def quote_tuple_from_symbol(symbol: str) -> tuple[int, str]:
    return (market_code_from_symbol(symbol), code6_from_symbol(symbol))
