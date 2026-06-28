from __future__ import annotations

"""Request/Response middleware for async services."""


import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from app.core.logger import get_logger
from app.infrastructure.memory_cache import get_cache

logger = get_logger(__name__)


async def timing_middleware(func: Callable) -> Callable:
    """Middleware to log request timing."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.debug(f"{func.__name__} completed in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
            raise
    return wrapper


class RequestCache:
    """Request-scoped deduplication cache backed by canonical MemoryCache (L1)."""

    _PREFIX = "reqcache:"

    def __init__(self, ttl_seconds: int = 60):
        self._ttl = ttl_seconds
        self._l1 = get_cache()

    def _key(self, key: str) -> str:
        return f"{self._PREFIX}{key}"

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        return self._l1.get(self._key(key))

    def set(self, key: str, value: Any) -> None:
        """Set cached value."""
        self._l1.set(self._key(key), value, ttl=self._ttl)

    def clear(self) -> None:
        """Clear all request cache entries."""
        self._l1.invalidate_pattern(self._PREFIX)


# Global request cache
_request_cache = RequestCache()


def cache_request(key_func: Callable[[Any], str]):
    """Decorator to cache async request results.

    Usage:
        @cache_request(lambda args: f"quote:{args[1]}")
        async def get_quote(self, code: str):
            return await self._fetch_quote(code)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = key_func((args, kwargs))
            cached = _request_cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached

            result = await func(*args, **kwargs)
            _request_cache.set(cache_key, result)
            return result
        return wrapper
    return decorator


class RetryPolicy:
    """Retry policy for failed async operations."""

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_base: float = 1.0,
        backoff_multiplier: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.backoff_multiplier = backoff_multiplier
        self.exceptions = exceptions

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry policy."""
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = self.backoff_base * (self.backoff_multiplier ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)

        raise last_exception


# For backwards compatibility
import asyncio


def with_retry(
    max_attempts: int = 3,
    backoff: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """Decorator to add retry logic to async functions.

    Usage:
        @with_retry(max_attempts=3, backoff=2.0)
        async def fetch_data(url):
            return await http.get(url)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            policy = RetryPolicy(max_attempts, backoff, exceptions)
            return await policy.execute(func, *args, **kwargs)
        return wrapper
    return decorator
