"""Per-route API rate limiting using HybridRateLimiter (Redis + memory fallback).

Phase 5 enhancement: Replaces stub with actual token-bucket enforcement.
"""

from __future__ import annotations

from typing import Any

from flask import Flask, request, jsonify

from app.core.hybrid_rate_limiter import HybridRateLimiter
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int

logger = get_logger(__name__)

_EXEMPT_PREFIXES = (
    "/api/v1/system/health",
    "/api/v1/health",
    "/system/health",
    "/static/",
    "/api/v1/system/task-messages",
    "/api/v1/system/active-jobs",
    "/api/v1/jarvis/proactive",
    "/api/v1/markets/",
    "/api/v1/data/",
    "/api/v1/stock-groups",
)

_DEFAULT_MAX_REQUESTS = get_runtime_int("API_RATE_LIMIT_MAX", 300)
_DEFAULT_WINDOW = get_runtime_int("API_RATE_LIMIT_WINDOW", 60)  # seconds
_DEFAULT_BLOCK = get_runtime_int("API_RATE_LIMIT_BLOCK", 300)   # seconds


def _rate_limit_key() -> str:
    """Build a rate-limit key from user identity or IP."""
    try:
        from flask_login import current_user
        if current_user.is_authenticated:
            return f"user:{current_user.id}"
    except Exception:
        pass
    ip = (request.environ.get("HTTP_X_FORWARDED_FOR") or
          request.environ.get("HTTP_X_REAL_IP") or
          request.remote_addr or "unknown")
    return f"ip:{ip.split(',')[0].strip()}"


def _is_exempt(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


def init_api_rate_limit_middleware(app: Flask) -> None:
    """Install rate-limit enforcement as before_request hook."""

    limiter = HybridRateLimiter(
        namespace="api",
        window=int(_DEFAULT_WINDOW),
        max_attempts=_DEFAULT_MAX_REQUESTS,
    )

    @app.before_request
    def _enforce_api_rate_limit() -> Any | None:
        path = request.path
        if request.method in ("OPTIONS", "HEAD"):
            return None
        if _is_exempt(path):
            return None
        if not (path.startswith("/api/") or path.startswith("/v2/")):
            return None

        key = _rate_limit_key()
        allowed = limiter.allow(key)
        if not allowed:
            logger.warning("Rate limit exceeded: key=%s path=%s", key, path)
            resp = jsonify({
                "success": False,
                "error": "请求频率过高，请稍后再试",
                "meta": {"retry_after_seconds": 0},
            })
            resp.status_code = 429
            resp.headers["Retry-After"] = "0"
            resp.headers["X-RateLimit-Limit"] = str(_DEFAULT_MAX_REQUESTS)
            return resp
        return None

    logger.info(
        "Rate limit middleware installed: %d req/%ds, %ds block",
        _DEFAULT_MAX_REQUESTS,
        _DEFAULT_WINDOW,
        _DEFAULT_BLOCK,
    )
