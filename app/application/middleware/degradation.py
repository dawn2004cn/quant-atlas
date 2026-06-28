from __future__ import annotations
"""Graceful degradation and fallback mechanisms for new architecture."""


import asyncio
from typing import Any, TypeVar
from collections.abc import Callable
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""
    enabled: bool = True
    max_retries: int = 3
    backoff_seconds: float = 1.0
    timeout_seconds: float = 30.0
    fallback_value: Any = None


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._state = "closed"  # closed, open, half_open

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if self._last_failure_time:
                if datetime.now() - self._last_failure_time > timedelta(seconds=self.recovery_timeout):
                    self._state = "half_open"
                    return False
            return True
        return False

    def record_success(self):
        """Record successful call."""
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self):
        """Record failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.is_open:
            raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception:
            self.record_failure()
            raise


class GracefulDegradation:
    """Graceful degradation with fallback chains."""

    def __init__(self):
        self._fallbacks: dict[str, Callable] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def register_fallback(self, primary_func: str, fallback_func: Callable):
        """Register a fallback function for a primary function."""
        self._fallbacks[primary_func] = fallback_func

    def register_circuit_breaker(self, name: str, **config):
        """Register a circuit breaker."""
        self._circuit_breakers[name] = CircuitBreaker(**config)

    async def execute_with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Callable | None = None,
        circuit_breaker_name: str | None = None,
        **kwargs
    ) -> Any:
        """Execute function with fallback and circuit breaker."""
        # Check circuit breaker
        if circuit_breaker_name and circuit_breaker_name in self._circuit_breakers:
            cb = self._circuit_breakers[circuit_breaker_name]
            if cb.is_open:
                logger.warning(f"Circuit breaker {circuit_breaker_name} is open, using fallback")
                if fallback_func:
                    return await fallback_func() if asyncio.iscoroutinefunction(fallback_func) else fallback_func()
                return None

        # Try primary function
        try:
            if asyncio.iscoroutinefunction(primary_func):
                return await primary_func(**kwargs)
            return primary_func(**kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed: {e}, trying fallback")

            # Try fallback
            if fallback_func:
                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func()
                    return fallback_func()
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    return None

            # Record failure in circuit breaker
            if circuit_breaker_name and circuit_breaker_name in self._circuit_breakers:
                self._circuit_breakers[circuit_breaker_name].record_failure()

            return None


# Global degradation handler
_degradation = GracefulDegradation()


def get_degradation_handler() -> GracefulDegradation:
    """Get global degradation handler."""
    return _degradation


def with_fallback(fallback_func: Callable = None, circuit_breaker: str = None):
    """Decorator to add fallback to a function."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await _degradation.execute_with_fallback(
                func,
                fallback_func,
                circuit_breaker,
                **kwargs
            )
        return wrapper
    return decorator


class CacheWithFallback:
    """Cache with fallback to compute function."""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._ttl = ttl_seconds

    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable,
        ttl: int | None = None
    ) -> Any:
        """Get from cache or compute."""
        now = datetime.now()
        ttl = ttl or self._ttl

        # Check cache
        if key in self._cache:
            value, timestamp = self._cache[key]
            if now - timestamp < timedelta(seconds=ttl):
                return value

        # Compute
        try:
            if asyncio.iscoroutinefunction(compute_func):
                value = await compute_func()
            else:
                value = compute_func()
        except Exception as e:
            logger.warning(f"Compute failed, checking cache even if expired: {e}")
            if key in self._cache:
                return self._cache[key][0]
            return None

        # Store in cache
        self._cache[key] = (value, now)
        return value

    def invalidate(self, key: str):
        """Invalidate a cache entry."""
        self._cache.pop(key, None)

    def clear(self):
        """Clear all cache."""
        self._cache.clear()


# Global cache instances
_quote_cache = CacheWithFallback(ttl_seconds=60)
_analysis_cache = CacheWithFallback(ttl_seconds=300)


def get_quote_cache() -> CacheWithFallback:
    """Get quote cache instance."""
    return _quote_cache


def get_analysis_cache() -> CacheWithFallback:
    """Get analysis cache instance."""
    return _analysis_cache
