from __future__ import annotations
"""Rate Limiter for API protection."""


import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_calls: int = 100          # Max calls per window
    window_seconds: int = 60      # Time window in seconds
    block_duration: int = 0      # Block duration in seconds (0 = no block)


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens."""
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now


class RateLimiter:
    """Rate limiter with multiple strategies."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.RLock()
        self._blocked_until: dict[str, float] = {}

    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create bucket for key."""
        with self._lock:
            if key not in self._buckets:
                refill_rate = self.config.max_calls / self.config.window_seconds
                self._buckets[key] = TokenBucket(
                    capacity=self.config.max_calls,
                    refill_rate=refill_rate
                )
            return self._buckets[key]

    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed.

        Returns:
            (allowed, info_dict)
        """
        # Check if blocked
        if key in self._blocked_until:
            if time.time() < self._blocked_until[key]:
                return False, {"blocked": True, "remaining": 0}
            else:
                del self._blocked_until[key]

        bucket = self._get_bucket(key)
        allowed = bucket.consume(1)

        if not allowed and self.config.block_duration > 0:
            with self._lock:
                self._blocked_until[key] = time.time() + self.config.block_duration

        return allowed, {"tokens": bucket.tokens, "blocked": False}

    def check(self, key: str) -> bool:
        """Simple check - just returns allowed status."""
        return self.is_allowed(key)[0]


class RateLimitRegistry:
    """Registry for multiple rate limiters."""

    _limiters: dict[str, RateLimiter] = {}
    _lock = threading.Lock()

    @classmethod
    def get(
        cls,
        name: str,
        max_calls: int = 100,
        window_seconds: int = 60
    ) -> RateLimiter:
        """Get or create a rate limiter."""
        with cls._lock:
            if name not in cls._limiters:
                config = RateLimitConfig(
                    max_calls=max_calls,
                    window_seconds=window_seconds
                )
                cls._limiters[name] = RateLimiter(config)
            return cls._limiters[name]

    @classmethod
    def check(cls, name: str, key: str) -> bool:
        """Quick check if key is allowed."""
        if name in cls._limiters:
            return cls._limiters[name].check(key)
        return True


def rate_limit(
    limiter_name: str = "default",
    max_calls: int = 100,
    window_seconds: int = 60
):
    """Decorator to add rate limiting to a function.

    Usage:
        @rate_limit("api_calls", max_calls=10, window_seconds=60)
        def fetch_data():
            return api.get()
    """
    limiter = RateLimitRegistry.get(limiter_name, max_calls, window_seconds)

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Use first argument or function name as key
            key = str(args[0]) if args else func.__name__

            allowed, info = limiter.is_allowed(key)
            if not allowed:
                raise RateLimitExceeded(f"Rate limit exceeded for {key}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


# Per-user rate limiter for API endpoints
user_rate_limiter = RateLimitRegistry.get("user_api", max_calls=60, window_seconds=60)


def limit_user_calls(user_id: str, max_calls: int = 60) -> bool:
    """Check if user has exceeded rate limit."""
    return user_rate_limiter.check(user_id)


__all__ = [
    "RateLimitConfig",
    "TokenBucket",
    "RateLimiter",
    "RateLimitRegistry",
    "rate_limit",
    "RateLimitExceeded",
    "limit_user_calls"
]