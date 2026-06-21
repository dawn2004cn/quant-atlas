"""Cache infrastructure — use ``get_cache_manager()`` as the unified L1+L2 entry."""

from app.infrastructure.cache.cache_manager import CacheManager, get_cache_manager
from app.infrastructure.cache.global_cache import GlobalCache, get_global_cache
from app.infrastructure.memory_cache import MemoryCache, get_cache

__all__ = [
    "CacheManager",
    "GlobalCache",
    "MemoryCache",
    "get_cache",
    "get_cache_manager",
    "get_global_cache",
]
