"""Dual-track authentication middleware.

Runs before every request to resolve identity from:
  1. Authorization: Bearer <token> (JWT)
  2. Flask-Login session cookie
  3. httpOnly qa_token cookie (JWT)

Sets g.identity_subject and g.identity_source for request tracing.
Does NOT block anonymous requests -- api_auth_required decorator does that.
"""
from __future__ import annotations

from flask import g, request

from app.core.logger import get_logger
from app.infrastructure.auth.jwt_token_service import decode_access_token, jwt_auth_enabled

logger = get_logger(__name__)

_COOKIE_NAME = "qa_token"


def install(app):
    """Register the before_request hook on the Flask app."""

    @app.before_request
    def _resolve_identity():
        g.identity_subject = None
        g.identity_source = None

        auth_header = (request.headers.get("Authorization") or "").strip()
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if jwt_auth_enabled():
                try:
                    payload = decode_access_token(token)
                    g.identity_subject = payload["sub"]
                    g.identity_source = "jwt"
                    return
                except Exception:
                    pass

        qa_token = (request.cookies.get(_COOKIE_NAME) or "").strip()
        if qa_token and jwt_auth_enabled():
            try:
                payload = decode_access_token(qa_token)
                g.identity_subject = payload["sub"]
                g.identity_source = "jwt_cookie"
                return
            except Exception:
                pass

        try:
            from flask_login import current_user

            if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
                g.identity_subject = str(current_user.get_id())
                g.identity_source = "cookie"
        except Exception:
            pass