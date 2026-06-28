from __future__ import annotations

"""Application-level exception hierarchy."""


from typing import Any


class ApplicationError(Exception):
    """Base application exception with HTTP mapping metadata."""

    status_code = 400
    error_code = "application_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "success": False,
            "data": None,
            "error": self.message,
            "meta": {
                "code": self.error_code,
                "details": self.details,
            },
            "status": "error",  # backward compat
        }


class ValidationError(ApplicationError):
    status_code = 400
    error_code = "validation_error"


class AuthorizationError(ApplicationError):
    status_code = 403
    error_code = "authorization_error"


class NotFoundError(ApplicationError):
    status_code = 404
    error_code = "not_found"


class ExternalServiceError(ApplicationError):
    status_code = 503
    error_code = "external_service_error"
