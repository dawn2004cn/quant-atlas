from __future__ import annotations

"""Backward-compatible re-export; canonical implementation lives in ``app.domain.shared``."""

from pathlib import Path

from app.domain.shared.tdx_paths import TdxLocalPaths, resolve_tdx_root

__all__ = ["TdxLocalPaths", "resolve_tdx_root", "resolve_tdx_root_configured"]


def resolve_tdx_root_configured(raw: str | Path | None = None) -> Path | None:
    """Resolve a TDX PC install dir: explicit path, else ``TDX_ROOT_PATH`` settings."""
    found = resolve_tdx_root(str(raw) if raw is not None else None)
    if found is not None:
        return found
    try:
        from app.config import get_settings

        return resolve_tdx_root(getattr(get_settings(), "tdx_root_path", None))
    except Exception:
        return None
