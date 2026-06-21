from __future__ import annotations
"""Backward-compatible re-export; canonical implementation lives in ``app.domain.shared``."""

from app.domain.shared.tdx_paths import TdxLocalPaths, resolve_tdx_root

__all__ = ["TdxLocalPaths", "resolve_tdx_root"]
