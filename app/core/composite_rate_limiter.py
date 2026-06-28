"""Composite-key rate limiter for API endpoints.

Provides a decorator that limits requests by a composite key of
(user_id, endpoint, IP_address) — more granular than IP-only or
user-only limiting. Prevents a single user from hammering expensive
endpoints (backtest, AI research) while still allowing rate limits
per endpoint.

Designed to complement flask-limiter (which is IP-keyed) with
application-level composite keying.
"""

from __future__ import annotations

import functools
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any
from collections.abc import Callable

from flask import request
from flask_login import current_user

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LimitRule:
    """A single rate limit rule."""

    max_calls: int
    window_seconds: int
    key_prefix: str = ""  # optional prefix for the composite key
    status_code: int = 429
    message: str = "Rate limit exceeded. Please try again later."


# Default rules for sensitive endpoints
DEFAULT_RULES = [
    LimitRule(max_calls=10, window_seconds=60, key_prefix="backtest"),       # 10 backtests/min
    LimitRule(max_calls=5, window_seconds=60, key_prefix="ai_research"),     # 5 AI calls/min
    LimitRule(max_calls=30, window_seconds=60, key_prefix="general"),        # 30 general/min
]


class CompositeRateLimiter:
    """Thread-safe in-memory composite-key rate limiter."""

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = {}
        self._locks: dict[str, Lock] = {}
        self._global_lock = Lock()
        self._rules: list[LimitRule] = list(DEFAULT_RULES)

    def add_rule(self, rule: LimitRule) -> None:
        self._rules.append(rule)

    def _get_lock(self, key: str) -> Lock:
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = Lock()
            return self._locks[key]

    def _clean_bucket(self, bucket: list[float], now: float, window: int) -> list[float]:
        cutoff = now - window
        return [t for t in bucket if t > cutoff]

    def is_allowed(self, key: str, rule: LimitRule, now: float | None = None) -> bool:
        """Check if a request identified by *key* is allowed under *rule*."""
        ts = now or time.time()
        lock = self._get_lock(key)
        with lock:
            with self._global_lock:
                if key not in self._buckets:
                    self._buckets[key] = []
                bucket = self._buckets[key]

            bucket = self._clean_bucket(bucket, ts, rule.window_seconds)
            allowed = len(bucket) < rule.max_calls

            if allowed:
                bucket.append(ts)
                with self._global_lock:
                    self._buckets[key] = bucket

            return allowed

    def get_remaining(self, key: str, rule: LimitRule, now: float | None = None) -> int:
        """Return remaining calls for the key under the rule."""
        ts = now or time.time()
        lock = self._get_lock(key)
        with lock:
            with self._global_lock:
                bucket = self._buckets.get(key, [])
            bucket = self._clean_bucket(bucket, ts, rule.window_seconds)
            remaining = max(0, rule.max_calls - len(bucket))
            return remaining


# Singleton
_composite_limiter = CompositeRateLimiter()


def composite_key() -> str:
    """Build a composite key from user_id + endpoint + IP."""
    user = current_user
    user_id = str(getattr(user, "id", "anonymous")) if hasattr(user, "id") else "anonymous"
    endpoint = request.endpoint or request.path
    ip = request.remote_addr or "unknown"
    return f"{user_id}:{endpoint}:{ip}"


def require_rate_limit(*rules: LimitRule):
    """Decorator to apply composite-key rate limiting to an endpoint.

    Usage::

        @bp.post("/backtest/run")
        @login_required
        @require_rate_limit(
            LimitRule(max_calls=5, window_seconds=60, key_prefix="bt"),
        )
        def run_backtest():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            key = composite_key()
            now = time.time()
            for rule in rules:
                if not _composite_limiter.is_allowed(key, rule, now):
                    logger.warning(
                        "Rate limit exceeded: key=%s rule=%s/%ds",
                        key, rule.max_calls, rule.window_seconds,
                    )
                    from flask import jsonify
                    return jsonify({
                        "error": rule.message,
                        "retry_after": rule.window_seconds,
                    }), rule.status_code
            return fn(*args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator


def get_rate_limiter() -> CompositeRateLimiter:
    """Return the singleton limiter for inspection/testing."""
    return _composite_limiter
