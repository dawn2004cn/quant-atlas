from __future__ import annotations
"""Performance helpers — domain cache delegates to canonical MemoryCache."""

from functools import wraps
import time
from typing import Any, Callable, Optional

from app.core.logger import get_logger
from app.infrastructure.memory_cache import CacheEntry, MemoryCache, get_cache

logger = get_logger(__name__)


class CachedDomainService:
    """Domain service with caching."""

    def __init__(self, cache: Optional[MemoryCache] = None):
        self._cache = cache or get_cache()

    def cache_result(
        self,
        key: str,
        fn: Callable,
        ttl: int = 300,
        *args,
        **kwargs,
    ) -> Any:
        return self._cache.get_or_compute(key, lambda: fn(*args, **kwargs), ttl)


def cached(ttl: int = 300, key_fn: Optional[Callable] = None):
    """Decorator for caching function results."""
    cache = get_cache()

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cache_key = key_fn(*args, **kwargs) if key_fn else f"{fn.__name__}:{args}:{kwargs}"
            return cache.get_or_compute(cache_key, lambda: fn(*args, **kwargs), ttl)

        wrapper.cache = cache
        return wrapper

    return decorator


def timed(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug("%s took %.4fs", fn.__name__, elapsed)
        return result

    return wrapper


class PerformanceMetrics:
    def __init__(self):
        self._metrics: dict[str, list[float]] = {}

    def record(self, operation: str, duration: float) -> None:
        self._metrics.setdefault(operation, []).append(duration)

    def get_stats(self, operation: str) -> dict:
        durations = self._metrics.get(operation, [])
        if not durations:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        return {
            "count": len(durations),
            "avg": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
        }

    def get_all_stats(self) -> dict:
        return {op: self.get_stats(op) for op in self._metrics}


_global_metrics = PerformanceMetrics()


def get_domain_cache() -> MemoryCache:
    return get_cache()


def get_performance_metrics() -> PerformanceMetrics:
    return _global_metrics


__all__ = [
    "CacheEntry",
    "MemoryCache",
    "CachedDomainService",
    "cached",
    "timed",
    "PerformanceMetrics",
    "get_domain_cache",
    "get_performance_metrics",
]
