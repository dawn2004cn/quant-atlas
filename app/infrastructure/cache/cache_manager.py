from __future__ import annotations
"""Unified L1 (memory) + L2 (Redis) cache facade."""

from typing import Any
from collections.abc import Callable

from app.infrastructure.cache.coalesce import get_or_set_coalesced

from app.core.logger import get_logger
from app.infrastructure.cache.global_cache import get_global_cache
from app.infrastructure.memory_cache import MemoryCache, get_cache

logger = get_logger(__name__)

_manager: CacheManager | None = None


class CacheManager:
    """Single entry for hot-path caching: MemoryCache (L1) + GlobalCache (L2)."""

    def __init__(
        self,
        memory: MemoryCache | None = None,
        redis_ttl: int = 300,
        memory_ttl: int = 60,
    ) -> None:
        self._memory = memory or get_cache()
        self._redis = get_global_cache()
        self._redis_ttl = redis_ttl
        self._memory_ttl = memory_ttl

    def get(self, key: str, default: Any = None) -> Any:
        hit = self._memory.get(key)
        if hit is not None:
            return hit
        hit = self._redis.get(key)
        if hit is not None:
            self._memory.set(key, hit, self._memory_ttl)
            return hit
        return default

    def set(self, key: str, value: Any, *, ttl: int | None = None, memory_ttl: int | None = None) -> None:
        redis_ttl = ttl if ttl is not None else self._redis_ttl
        l1_ttl = memory_ttl if memory_ttl is not None else self._memory_ttl
        self._memory.set(key, value, l1_ttl)
        self._redis.set(key, value, redis_ttl)

    def delete(self, key: str) -> None:
        self._memory.delete(key)
        self._redis.delete(key)

    def get_or_set(self, key: str, factory: Callable[[], Any], *, ttl: int | None = None) -> Any:
        redis_ttl = ttl if ttl is not None else self._redis_ttl

        def _get() -> Any | None:
            return self.get(key)

        def _set(value: Any) -> None:
            if value is not None:
                self.set(key, value, ttl=redis_ttl)

        return get_or_set_coalesced(key, get_value=_get, set_value=_set, factory=factory)

    def invalidate_prefix(self, prefix: str) -> int:
        self._memory.invalidate_pattern(prefix)
        return self._redis.invalidate_prefix(prefix)

    def stats(self) -> dict[str, Any]:
        return {
            "memory": self._memory.stats(),
            "redis_available": self._redis._available,
        }


def get_cache_manager() -> CacheManager:
    global _manager
    if _manager is None:
        _manager = CacheManager()
    return _manager


__all__ = ["CacheManager", "get_cache_manager"]
