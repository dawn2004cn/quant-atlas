from __future__ import annotations

"""Backward-compatible re-export; canonical implementation lives in ``app.domain.shared``."""

from app.domain.shared.eastmoney_parser import EastmoneyParser

__all__ = ["EastmoneyParser"]
