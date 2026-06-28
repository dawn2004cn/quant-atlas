from __future__ import annotations

"""Legacy re-exports from canonical MemoryCache.

All new code should import from ``app.infrastructure.memory_cache``.
"""

# Lazy import to avoid domain -> infrastructure dependency at module load time
# This re-export shim reads from the canonical cache so existing callers still work.
from typing import Any


def __getattr__(name: str) -> Any:
    """Dynamically resolve names from the canonical cache module."""
    if name in ("CacheService", "CacheEntry", "MemoryCache", "cache_key", "cached", "cached_method", "get_cache"):
        import importlib
        mod = importlib.import_module("app.infrastructure.memory_cache")
        return getattr(mod, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


CacheService = MemoryCache  # type: ignore[name-defined]  # deferred via __getattr__
_global_cache = get_cache()  # type: ignore[name-defined]
__all__ = [
    "CacheService",
    "CacheEntry",
    "cache_key",
    "cached",
    "cached_method",
    "get_cache",
]
