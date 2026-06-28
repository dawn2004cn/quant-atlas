"""API rate limiting middleware for Quant Atlas backend.

Provides per-route and per-client rate limiting with Redis or
in-memory backend. Defaults to in-memory token bucket for
situations where Redis is not configured.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any
from collections.abc import Callable

from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Per-route rate limit configuration."""
    max_requests: int = 100
    window_seconds: float = 60.0
    block_seconds: float = 300.0
    exempt_paths: list[str] = field(default_factory=list)


class TokenBucket:
    """In-memory token bucket rate limiter."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RateLimiter:
    """Per-client rate limiter with IP/API-key awareness."""

    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()
        self._buckets: dict[str, tuple[TokenBucket, float]] = {}
        self._lock = threading.Lock()

    def _client_key(self) -> str:
        ip = (request.environ.get("HTTP_X_FORWARDED_FOR") or
              request.environ.get("HTTP_X_REAL_IP") or
              request.remote_addr or
              "127.0.0.1")
        forwarded = ip.split(",")[0].strip() if ip else "127.0.0.1"
        auth = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key", "")
        fingerprint = f"{forwarded}|{auth[:20]}|{api_key[:20]}"
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]

    def _should_exempt(self) -> bool:
        path = request.path
        for exempt in self.config.exempt_paths:
            if path.startswith(exempt):
                return True
        return False

    def is_allowed(self) -> bool:
        if self._should_exempt():
            return True
        key = self._client_key()
        now = time.monotonic()
        with self._lock:
            if key in self._buckets:
                bucket, blocked_until = self._buckets[key]
                if blocked_until > now:
                    return False
            else:
                rate = self.config.max_requests / self.config.window_seconds
                bucket = TokenBucket(rate=rate, burst=self.config.max_requests)
            if bucket.consume():
                self._buckets[key] = (bucket, 0.0)
                return True
            else:
                self._buckets[key] = (bucket, now + self.config.block_seconds)
                return False

    def cleanup_expired(self) -> None:
        """Remove expired bucket entries (call from background task)."""
        now = time.monotonic()
        with self._lock:
            expired = [k for k, (_, blocked) in self._buckets.items()
                       if blocked > 0 and blocked < now]
            for k in expired:
                del self._buckets[k]


# Singleton instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        from app.core.runtime_config import get_runtime_int
        config = RateLimitConfig(
            max_requests=get_runtime_int("API_RATE_LIMIT_MAX", 100),
            window_seconds=float(get_runtime_int("API_RATE_LIMIT_WINDOW", 60)),
            block_seconds=float(get_runtime_int("API_RATE_LIMIT_BLOCK", 300)),
            exempt_paths=["/api/v1/system/health", "/api/v1/health", "/static/"],
        )
        _rate_limiter = RateLimiter(config)
    return _rate_limiter


def rate_limit(
    max_requests: int | None = None,
    window_seconds: float | None = None,
    block_seconds: float | None = None,
):
    """Decorator for per-route rate limiting overrides."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter = get_rate_limiter()
            if max_requests is not None:
                limiter.config.max_requests = max_requests
            if window_seconds is not None:
                limiter.config.window_seconds = window_seconds
            if block_seconds is not None:
                limiter.config.block_seconds = block_seconds
            if not limiter.is_allowed():
                return jsonify({
                    "success": False,
                    "error": "Rate limit exceeded. Try again later.",
                    "meta": {"retry_after_seconds": int(get_rate_limiter().config.block_seconds)},
                }), 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def init_rate_limiter(app: Flask) -> None:
    """Install rate limiter as global before_request hook."""

    @app.before_request
    def _enforce_rate_limit() -> None:
        if request.method in ("OPTIONS", "HEAD"):
            return
        limiter = get_rate_limiter()
        if not limiter._should_exempt():
            if not limiter.is_allowed():
                from flask import abort
                abort(429, description="Rate limit exceeded")

    # Periodic cleanup thread
    import threading as _threading
    def _cleanup_loop() -> None:
        while True:
            time.sleep(300)  # every 5 minutes
            get_rate_limiter().cleanup_expired()
    cleanup_thread = _threading.Thread(target=_cleanup_loop, daemon=True)
    cleanup_thread.start()

    logger.info("Rate limiter initialized: %d req/%.0fs, %.0fs block",
                get_rate_limiter().config.max_requests,
                get_rate_limiter().config.window_seconds,
                get_rate_limiter().config.block_seconds)
