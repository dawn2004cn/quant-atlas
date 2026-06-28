"""Legacy re-exports from canonical MemoryCache.

All new code should import from ``app.infrastructure.memory_cache``.
"""

# Lazy import to avoid domain -> infrastructure dependency at module load time
# This re-export shim reads from the canonical cache so existing callers still work.
from typing import Any


def __getattr__(name: str) -> Any:
    """Dynamically resolve names from the requested names from the canonical cache module."""
    if name in ("CacheService", "CacheEntry", "MemoryCache", "cache_key", "cached", "cached_method", "get_cache"):
        import importlib
        mod = importlib.import_module("app.infrastructure.memory_cache")
        return getattr(mod, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


# For static analysis / IDE - these will be resolved via __getattr__ at runtime
# Do not assign real values here as it would create module-level imports
CacheService = "MemoryCache"  # type: ignore[assignment]
CacheEntry = "CacheEntry"  # type: ignore[assignment]
cache_key = "cache_key"  # type: ignore[assignment]
cached = "cached"  # type: ignore[assignment]
cached_method = "cached_method"  # type: ignore[assignment]
get_cache = "get_cache"  # type: ignore[assignment]

__all__ = [
    "CacheService",
    "CacheEntry",
    "cache_key",
    "cached",
    "cached_method",
    "get_cache",
]
