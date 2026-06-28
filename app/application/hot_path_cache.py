"""Legacy re-exports. Use ``app.infrastructure.memory_cache`` for new code."""
from app.infrastructure.memory_cache import MemoryCache

HotPathCache = MemoryCache
get_hot_path_cache = __import__("app.infrastructure.memory_cache", fromlist=["get_cache"]).get_cache
CacheTier = None
CachePolicy = None
POLICIES = {}

__all__ = ["CacheTier", "CachePolicy", "POLICIES", "HotPathCache", "get_hot_path_cache"]
