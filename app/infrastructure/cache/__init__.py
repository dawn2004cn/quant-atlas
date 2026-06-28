"""Cache infrastructure — use ``get_cache_manager()`` as the unified L1+L2 entry."""

from app.infrastructure.cache.cache_manager import CacheManager, get_cache_manager
from app.infrastructure.cache.global_cache import GlobalCache, get_global_cache

__all__ = [
    "CacheManager",
    "GlobalCache",
    "get_cache_manager",
    "get_global_cache",
]
