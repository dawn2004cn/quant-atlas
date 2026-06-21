from __future__ import annotations

import json
import hashlib
import time
from datetime import datetime
from typing import Any, Callable, TypeVar
from functools import wraps

from app.infrastructure.cache.coalesce import get_or_set_coalesced
from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CacheEntry:
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds


class MemoryCache:
    """Canonical in-memory cache with bounded size.

    Uses TTLCache internally to prevent unbounded memory growth.
    Replaces CacheService, HotPathCache, RequestCache, and
    cache_result decorator.
    """

    def __init__(self, default_ttl: int = 300, maxsize: int = 10000):
        try:
            from cachetools import TTLCache
            self._store: TTLCache = TTLCache(maxsize=maxsize, ttl=default_ttl)
        except ImportError:
            # Fallback: bounded dict with manual eviction
            self._store: dict[str, CacheEntry] = {}
            self._maxsize = maxsize
            self._default_ttl = default_ttl
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        # cachetools TTLCache: 'in' check + get is safe (no expiry race)
        if hasattr(self._store, 'get') and not isinstance(self._store, dict):
            # TTLCache path (cachetools)
            if key not in self._store:
                self._misses += 1
                return None
            value = self._store[key]
            self._hits += 1
            return value
        # Fallback dict path (CacheEntry objects)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired():
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None):
        effective_ttl = ttl or self._default_ttl
        if hasattr(self._store, 'update'):
            # cachetools TTLCache path
            self._store[key] = value
        else:
            # Fallback dict path
            if len(self._store) >= self._maxsize:
                # Evict oldest entry
                oldest_key = min(self._store, key=lambda k: self._store[k].created_at)
                del self._store[oldest_key]
            self._store[key] = CacheEntry(value, effective_ttl)

    def delete(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()

    def get_or_compute(self, key: str, compute_fn: Callable[[], T], ttl: int | None = None) -> T:
        effective_ttl = ttl or self._default_ttl

        def _get() -> T | None:
            return self.get(key)

        def _set(value: T) -> None:
            self.set(key, value, effective_ttl)

        return get_or_set_coalesced(key, get_value=_get, set_value=_set, factory=compute_fn)

    def invalidate_pattern(self, pattern: str):
        if hasattr(self._store, 'keys'):
            keys = [k for k in self._store if pattern in str(k)]
            for k in keys:
                self._store.pop(k, None)

    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "total_keys": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total * 100:.1f}%" if total else "0%",
        }


def cache_key(*args, **kwargs) -> str:
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func: Callable):
        cache = get_cache()
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            return cache.get_or_compute(key, lambda: func(*args, **kwargs), ttl)
        return wrapper
    return decorator


def cached_method(ttl: int = 300):
    """Decorator to cache instance method results."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cache = getattr(self, "_cache", None) or get_cache()
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            return cache.get_or_compute(key, lambda: func(self, *args, **kwargs), ttl)
        return wrapper
    return decorator


_global_cache = MemoryCache()


def get_cache() -> MemoryCache:
    return _global_cache


def clear_cache():
    _global_cache.clear()


__all__ = [
    "MemoryCache",
    "CacheEntry",
    "cache_key",
    "cached",
    "cached_method",
    "get_cache",
    "clear_cache",
]
