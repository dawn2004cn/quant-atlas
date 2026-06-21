from __future__ import annotations

from app.core.runtime_config import get_runtime

"""Global Redis Cache for generic data caching."""


import json
import os
import logging
from typing import Any, Callable
import redis
from app.infrastructure.redis_client import RedisClientPool, delete_keys_by_pattern


from app.infrastructure.cache.coalesce import get_or_set_coalesced
from app.core.logger import get_logger

logger = get_logger(__name__)

_redis_url: str | None = None
_default_ttl = 300


class GlobalCache:
    """Global Redis-based cache for any data with automatic JSON serialization."""

    _instance = None
    _client = None
    _available = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        global _redis_url
        url = get_runtime("REDIS_URL", "")
        if not url:
            logger.error("REDIS_URL not set. GlobalCache unavailable.")
            self._client = None
            self._available = False
            return
        _redis_url = url
        try:
            self._client = RedisClientPool.get(_redis_url).client
            self._client.ping()
            self._available = True
            logger.info("GlobalCache: Redis connected")
        except Exception as e:
            self._client = None
            self._available = False
            logger.warning(f"GlobalCache: Redis unavailable ({e})")

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        if not self._available or not self._client:
            return default
        try:
            val = self._client.get(key)
            if val is None:
                return default
            return json.loads(val)
        except json.JSONDecodeError:
            return val
        except Exception as e:
            logger.debug(f"GlobalCache get error for {key}: {e}")
            return default

    def set(self, key: str, value: Any, ttl: int = _default_ttl) -> bool:
        """Set value in cache with TTL."""
        if not self._available or not self._client:
            return False
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.debug(f"GlobalCache set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._available or not self._client:
            return False
        try:
            self._client.delete(key)
            return True
        except Exception:
            return False

    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: int = _default_ttl) -> Any:
        """Get value from cache or compute and cache it."""

        def _get() -> Any | None:
            return self.get(key)

        def _set(value: Any) -> None:
            self.set(key, value, ttl)

        return get_or_set_coalesced(key, get_value=_get, set_value=_set, factory=factory)

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all keys starting with prefix."""
        if not self._available or not self._client:
            return 0
        try:
            return delete_keys_by_pattern(self._client, f"{prefix}*")
        except Exception as e:
            logger.warning(f"GlobalCache invalidate error for {prefix}: {e}")
            return 0


_global_cache: GlobalCache | None = None


def get_global_cache() -> GlobalCache:
    """Get the global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = GlobalCache()
    return _global_cache


def cached(key_prefix: str, ttl: int = _default_ttl):
    """Decorator to cache function results.

    Usage:
        @cached("user_profile_", ttl=600)
        def get_user_profile(user_id):
            return fetch_from_db(user_id)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            cache = get_global_cache()
            key = f"{key_prefix}{args[0]}" if args else f"{key_prefix}{kwargs.get('id', 'default')}"
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator


__all__ = ["GlobalCache", "get_global_cache", "cached"]