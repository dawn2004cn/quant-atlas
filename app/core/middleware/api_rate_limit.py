"""Per-route API rate limiting using HybridRateLimiter (Redis + memory fallback)."""

from __future__ import annotations

from typing import Any

from flask import Flask, request

from app.core.hybrid_rate_limiter import HybridRateLimiter
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int
from app.presentation.api.responses import error_response

logger = get_logger(__name__)

_EXEMPT_PREFIXES = (
    "/api/v1/system/health",
    "/api/v1/health",
    "/system/health",
    "/api/v1/system/task-messages",
    "/api/v1/system/active-jobs",
    "/api/v1/jarvis/proactive",
    "/api/v1/markets/",
    "/api/v1/compliance/",
    "/api/v1/retail-assistant/",
    "/api/v1/data/",
    "/api/v1/stock-groups",
)


def _rate_limit_key() -> str:
    try:
        from flask_login import current_user

        if current_user.is_authenticated:
            return f"user:{current_user.id}"
    except Exception:
        logger.debug("api rate limit: user key fallback to IP", exc_info=True)
    return f"ip:{request.remote_addr or 'unknown'}"


def _is_exempt(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


def init_api_rate_limit_middleware(app: Flask) -> None:
    pass
