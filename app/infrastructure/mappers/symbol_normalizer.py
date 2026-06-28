from __future__ import annotations

"""Backward-compatible re-export; canonical implementation lives in ``app.domain.shared``."""

from app.domain.shared.symbol_normalizer import SymbolNormalizer, get_symbol_normalizer

__all__ = ["SymbolNormalizer", "get_symbol_normalizer"]
