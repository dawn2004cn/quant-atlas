"""API v2 authentication routes (JWT token issue + refresh + profile + logoff)."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.application.errors import AuthorizationError, ValidationError
from app.infrastructure.auth.jwt_token_service import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    jwt_auth_enabled,
)

from ..auth_guard import api_auth_required, resolve_api_user
from ..responses import success_response

_COOKIE_NAME = "qa_token"


def _token_response(*, access_token: str, refresh_token: str, expires_in: int, meta: dict | None = None):
    """Build a token response that bypasses the SENSITIVE_FIELDS serializer filter.

    The standard ``success_response`` strips ``access_token``/``refresh_token`` to
    prevent accidental leakage in normal API responses. Auth endpoints are the
    explicit exception — issuing tokens IS their purpose.
    """
    payload = {
        "success": True,
        "ok": True,
        "status": "success",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        },
        "error": None,
        "meta": meta,
    }
    return jsonify(payload)


def create_auth_blueprint(ctx) -> Blueprint:
    bp = Blueprint("v2_auth", __name__)

    def _cookie_secure() -> bool:
        # Follow Flask session cookie policy (dev HTTP must stay non-Secure).
        return bool(current_app.config.get("SESSION_COOKIE_SECURE", False))

    def _set_token_cookie(resp, token: str, max_age: int):
        resp.set_cookie(
            _COOKIE_NAME, token,
            httponly=True,
            secure=_cookie_secure(),
            samesite="Strict",
            max_age=max_age,
            path="/",
        )

    @bp.post("/auth/token")
    def issue_token():
        if not jwt_auth_enabled():
            raise ValidationError("API JWT is not configured (set API_JWT_SECRET)")
        if ctx.auth_service is None:
            raise ValidationError("auth_service unavailable")
        body = request.get_json(silent=True) or {}
        username = str(body.get("username") or "").strip()
        password = str(body.get("password") or "")
        if not username or not password:
            raise ValidationError("username and password are required")
        user = ctx.auth_service.authenticate(username, password)
        if user is None:
            raise AuthorizationError("invalid_credentials")
        access_token, expires_in = create_access_token(
            user_id=int(user.user_id),
            username=user.username,
            role=user.role,
        )
        refresh_token, _ = create_refresh_token(
            user_id=int(user.user_id),
            username=user.username,
            role=user.role,
        )
        resp = _token_response(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            meta={"username": user.username, "role": user.role},
        )
        _set_token_cookie(resp, access_token, expires_in)
        return resp

    @bp.post("/auth/token/refresh")
    def refresh_token():
        """Exchange a valid refresh token for a new access + refresh token pair."""
        if not jwt_auth_enabled():
            raise ValidationError("API JWT is not configured (set API_JWT_SECRET)")
        body = request.get_json(silent=True) or {}
        raw_token = str(body.get("refresh_token") or "").strip()
        if not raw_token:
            raw_token = (request.cookies.get(_COOKIE_NAME) or "").strip()
        if not raw_token:
            raise ValidationError("refresh_token is required")
        claims = decode_refresh_token(raw_token)
        new_access, expires_in = create_access_token(
            user_id=int(claims["sub"]),
            username=str(claims.get("username") or ""),
            role=str(claims.get("role") or "viewer"),
        )
        new_refresh, _ = create_refresh_token(
            user_id=int(claims["sub"]),
            username=str(claims.get("username") or ""),
            role=str(claims.get("role") or "viewer"),
        )
        resp = _token_response(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=expires_in,
        )
        _set_token_cookie(resp, new_access, expires_in)
        return resp

    @bp.post("/auth/logoff")
    def logoff():
        """Clear JWT cookie (client-side token invalidation)."""
        resp, code = success_response(data={"message": "logged_off"})
        resp.set_cookie(_COOKIE_NAME, "", httponly=True, secure=_cookie_secure(),
                        samesite="Strict", max_age=0, path="/")
        return resp

    @bp.get("/auth/me")
    @api_auth_required
    def auth_me():
        user = resolve_api_user()
        return success_response(
            data={
                "user_id": int(user.id),
                "username": user.username,
                "role": user.role,
            }
        )

    return bp
