from __future__ import annotations
"""Legacy re-exports from canonical MemoryCache.

All new code should import from ``app.infrastructure.memory_cache``.
"""

from app.infrastructure.memory_cache import (
    MemoryCache,
    CacheEntry,
    cache_key,
    cached,
    cached_method,
    get_cache,
)

CacheService = MemoryCache
_global_cache = get_cache()
__all__ = [
    "CacheService",
    "CacheEntry",
    "cache_key",
    "cached",
    "cached_method",
    "get_cache",
]
