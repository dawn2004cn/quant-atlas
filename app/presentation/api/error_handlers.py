from __future__ import annotations
"""Global API error handlers."""


import logging
import uuid
from urllib.parse import urlparse
from flask import Flask, has_request_context, jsonify, request, redirect, url_for
from flask_login import LoginManager
from werkzeug.exceptions import HTTPException, NotFound, Forbidden, BadRequest, Unauthorized, UnprocessableEntity

from ...application.errors import ApplicationError, ValidationError, AuthorizationError, NotFoundError
from app.core.exceptions import CoreError
from app.domain.exceptions import AppError
from app.presentation.api_errors import APIException
from .actionable_error_catalog import enrich_error_payload
from .degraded_response import apply_degraded_headers
from ..http_static import is_static_asset_request

from app.core.logger import get_logger

logger = get_logger(__name__)


def _request_id() -> str:
    if has_request_context():
        return request.headers.get("X-Request-ID") or request.environ.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
    return str(uuid.uuid4())


def _error_payload(code: str, message: str, details: dict[str, object]) -> dict[str, object]:
    rid = _request_id()
    details = dict(details)
    details["request_id"] = rid
    return {
        "success": False,
        "data": None,
        "error": message,
        "meta": {
            "code": code,
            "request_id": rid,
            **details,
        },
        "status": "error",
        "request_id": rid,
    }


def _with_request_id(payload: dict[str, object]) -> dict[str, object]:
    rid = _request_id()
    payload["request_id"] = rid
    error = payload.get("error")
    if isinstance(error, dict):
        details = error.get("details")
        if isinstance(details, dict):
            details["request_id"] = rid
    return payload


def map_application_error(error):
    return _with_request_id(error.to_payload()), error.status_code


def map_validation_error(error):
    """Map a ValidationError to a 400 JSON response."""
    from app.application.errors import ValidationError as VE
    if isinstance(error, VE):
        payload = _with_request_id(error.to_payload())
        return enrich_error_payload(payload), 400
    payload = _with_request_id({"error": {"code": "validation_error", "message": str(error)}})
    return enrich_error_payload(payload), 400


def map_authorization_error(error):
    return _with_request_id(error.to_payload()), error.status_code


def _static_http_response(error: HTTPException):
    """Let Werkzeug serve a plain 404/4xx for missing static files (correct MIME)."""
    return error.get_response()


def map_http_error(error: HTTPException) -> tuple[dict, int]:
    """Map werkzeug HTTP exceptions to standardized error format."""
    code_map = {
        400: ("validation_error", "Bad Request"),
        401: ("unauthorized", "Authentication required"),
        403: ("forbidden", "Access denied"),
        404: ("not_found", "Resource not found"),
        422: ("unprocessable", "Invalid request data"),
    }
    code, message = code_map.get(error.code, ("http_error", error.description or "HTTP error"))
    payload = _error_payload(code, message, {"path": request.path})
    return enrich_error_payload(payload), error.code


def map_unexpected_error(error: Exception) -> tuple[dict, int]:
    """Map unexpected exceptions to standardized error format."""
    logger.exception("Unhandled exception: %s", error)
    payload = enrich_error_payload(
        _error_payload("internal_error", "Internal server error", {})
    )
    return payload, 500


def _map_core_error(error: CoreError) -> tuple[dict[str, object], int]:
    payload = _error_payload(error.error_code, error.message, error.details)
    return enrich_error_payload(payload), error.status_code


def _app_error_status_code(error: AppError) -> int:
    code = getattr(type(error), "CODE", None) or getattr(error, "code", "APP_ERROR")
    if str(code).endswith("NOT_FOUND"):
        return 404
    mapping = {
        "INSUFFICIENT_FUNDS": 400,
        "INVALID_OPERATION": 400,
        "STRATEGY_NOT_ENABLED": 400,
        "DATA_VALIDATION_ERROR": 400,
        "EXECUTION_ERROR": 400,
        "INSUFFICIENT_QUOTA": 400,
        "MARKET_CLOSED": 409,
        "RATE_LIMIT_EXCEEDED": 429,
        "REPOSITORY_ERROR": 503,
        "SERVICE_ERROR": 503,
        "SERVICE_UNAVAILABLE": 503,
        "CRITICAL_SECURITY_ERROR": 500,
        "INVALID_CONFIGURATION": 500,
    }
    return mapping.get(code, 400)


def _map_app_error(error: AppError) -> tuple[dict[str, object], int]:
    code = getattr(type(error), "CODE", None) or getattr(error, "code", "APP_ERROR")
    payload = _error_payload(
        str(code).lower(),
        getattr(error, "message", str(error)),
        getattr(error, "details", {}) or {},
    )
    return enrich_error_payload(payload), _app_error_status_code(error)


def _map_api_exception(error: APIException) -> tuple[dict[str, object], int]:
    """Map legacy APIException to the standard error envelope."""
    code = error.code.value if hasattr(error.code, "value") else str(error.code)
    return _error_payload(code.lower(), error.message, error.details or {}), error.status_code


def register_api_error_handlers(app: Flask) -> None:
    """Register consistent API error mapping for application exceptions."""

    @app.errorhandler(APIException)
    def handle_api_exception(error: APIException):
        payload, status = _map_api_exception(error)
        return jsonify(enrich_error_payload(payload)), status

    @app.errorhandler(ApplicationError)
    def handle_application_error(error: ApplicationError):
        if isinstance(error, ValidationError):
            payload = enrich_error_payload(error.to_payload())
            return jsonify(payload), error.status_code
        if isinstance(error, NotFoundError):
            return jsonify(error.to_payload()), error.status_code
        if isinstance(error, AuthorizationError):
            return jsonify(error.to_payload()), error.status_code
        return jsonify(error.to_payload()), error.status_code

    @app.errorhandler(CoreError)
    def handle_core_error(error: CoreError):
        payload, status = _map_core_error(error)
        return jsonify(payload), status

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        payload, status = _map_app_error(error)
        return jsonify(payload), status

    @app.errorhandler(NotFound)
    def handle_not_found(error: NotFound):
        if is_static_asset_request():
            return _static_http_response(error)
        payload, status_code = map_http_error(error)
        return jsonify(payload), status_code

    @app.errorhandler(Forbidden)
    def handle_forbidden(error: Forbidden):
        payload, status_code = map_http_error(error)
        return jsonify(payload), status_code

    @app.errorhandler(Unauthorized)
    def handle_unauthorized(error: Unauthorized):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify(enrich_error_payload(_error_payload(
                "unauthorized",
                "Authentication required",
                {"path": request.path},
            ))), 401
        return _fallback_unauthorized_response()

    @app.errorhandler(BadRequest)
    def handle_bad_request(error: BadRequest):
        payload, status_code = map_http_error(error)
        return jsonify(payload), status_code

    @app.errorhandler(UnprocessableEntity)
    def handle_unprocessable(error: UnprocessableEntity):
        payload, status_code = map_http_error(error)
        return jsonify(payload), status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        if is_static_asset_request():
            return _static_http_response(error)
        if error.code and error.code >= 500:
            app.logger.exception("HTTP exception %s for %s %s", error.code, request.method, request.path)
        payload, status_code = map_http_error(error)
        return jsonify(payload), status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        if is_static_asset_request() and isinstance(error, HTTPException):
            return _static_http_response(error)
        app.logger.exception("Unexpected error handling %s %s", request.method, request.path)
        payload, status_code = map_unexpected_error(error)
        return jsonify(payload), status_code


def _safe_next_url(url: str) -> str:
    """Only allow internal redirects — block open redirect vulnerabilities."""
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != request.host:
        return url_for("pages.daily_workbench")
    return url


def _fallback_unauthorized_response():
    """Redirect to auth.login when available, otherwise return 401 JSON."""
    try:
        return redirect(url_for("auth.login", next=_safe_next_url(request.url)))
    except Exception:
        return jsonify(enrich_error_payload(_error_payload(
            "unauthorized",
            "Authentication required",
            {},
        ))), 401


def setup_flask_login_errors(app: Flask, login_manager: LoginManager) -> None:
    """Setup Flask-Login error handlers."""

    def _web_unauthorized():
        return _fallback_unauthorized_response()

    def _api_unauthorized():
        return jsonify(enrich_error_payload(_error_payload(
            "unauthorized",
            "Authentication required",
            {},
        ))), 401

    login_manager.unauthorized_callback = _web_unauthorized

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/") or request.is_json:
            return _api_unauthorized()
        return _web_unauthorized()

    if hasattr(login_manager, "invalid_session"):
        @login_manager.invalid_session
        def invalid_session():
            if request.path.startswith("/api/") or request.is_json:
                return jsonify(enrich_error_payload(_error_payload(
                    "invalid_session",
                    "Session invalid or expired",
                    {},
                ))), 401
            return _fallback_unauthorized_response()
