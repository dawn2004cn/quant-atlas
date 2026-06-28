"""API authentication guard -- Flask session or Bearer JWT or httpOnly Cookie."""

from __future__ import annotations

from functools import wraps
from typing import Any, TypeVar
from collections.abc import Callable

from flask import Request, g, request

from app.application.errors import AuthorizationError
from app.core.logger import get_logger
from app.core.middleware.resilience import set_user_id
from app.infrastructure.auth.jwt_token_service import decode_access_token, jwt_auth_enabled

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_COOKIE_NAME = "qa_token"


def user_from_bearer_token(req: Request | None = None) -> Any | None:
    """Resolve SessionUser from Authorization: Bearer header or qa_token cookie."""
    if not jwt_auth_enabled():
        return None
    active = req if req is not None else request

    # 1) Try Authorization header
    header = (active.headers.get("Authorization") or "").strip()
    token = ""
    if header.lower().startswith("bearer "):
        token = header[7:].strip()

    # 2) Fallback to qa_token cookie (httpOnly, set by /auth/token)
    if not token:
        token = (active.cookies.get(_COOKIE_NAME) or "").strip()

    if not token:
        return None
    try:
        claims = decode_access_token(token)
    except AuthorizationError:
        return None
    from app.presentation.web.models import SessionUser

    return SessionUser(
        int(claims["sub"]),
        str(claims.get("username") or ""),
        str(claims.get("role") or "viewer"),
    )


def resolve_api_user() -> Any | None:
    """Authenticated principal via Flask-Login session or Bearer JWT or httpOnly Cookie."""
    try:
        from flask_login import current_user

        if current_user.is_authenticated:
            return current_user
    except Exception:
        logger.debug("Flask-Login not available, falling back to JWT auth")
    return user_from_bearer_token()


def api_auth_required(view: F) -> F:
    """Require session login or valid Bearer JWT or qa_token cookie."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        user = resolve_api_user()
        if user is None:
            raise AuthorizationError("authentication_required")
        g.api_user = user
        set_user_id(str(user.id))
        return view(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
