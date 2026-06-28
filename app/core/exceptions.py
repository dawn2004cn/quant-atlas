from __future__ import annotations

"""Core exception hierarchy for quant-atlas.

This module unifies exception handling across all layers:
- CoreError: Base exception for the application
- DomainError: Business logic violations
- ServiceError: Service layer failures
- RepositoryError: Data access failures
- ExternalError: External API failures

Each exception maps to an HTTP status code for API responses.
"""


from typing import Any


class CoreError(Exception):
    """Base exception for all quant-atlas errors.

    Provides standardized error handling with HTTP status code mapping.
    Subclasses should define class-level status_code and error_code.
    """

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "status_code": self.status_code,
        }


class ValidationError(CoreError):
    """Raised when input validation fails."""
    status_code = 400
    error_code = "validation_error"


class AuthorizationError(CoreError):
    """Raised when user lacks permission."""
    status_code = 403
    error_code = "authorization_error"


class NotFoundError(CoreError):
    """Raised when a requested resource is not found."""
    status_code = 404
    error_code = "not_found"

    def __init__(self, resource: str, identifier: str, **kwargs: Any):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, **kwargs)
        self.details = {"resource": resource, "identifier": identifier, **self.details}


class ConflictError(CoreError):
    """Raised when a resource conflict occurs."""
    status_code = 409
    error_code = "conflict_error"


class ServiceUnavailableError(CoreError):
    """Raised when a required service is unavailable."""
    status_code = 503
    error_code = "service_unavailable"


class ExternalServiceError(CoreError):
    """Raised when an external API call fails."""
    status_code = 502
    error_code = "external_service_error"

    def __init__(self, service: str, message: str, **kwargs: Any):
        full_message = f"{service} error: {message}"
        super().__init__(full_message, **kwargs)
        self.details = {"service": service, **self.details}


class ConfigurationError(CoreError):
    """Raised when configuration is invalid or missing."""
    status_code = 500
    error_code = "configuration_error"

    def __init__(self, key: str, reason: str, **kwargs: Any):
        message = f"Invalid configuration '{key}': {reason}"
        super().__init__(message, **kwargs)
        self.details = {"config_key": key, "reason": reason, **self.details}


class RateLimitError(CoreError):
    """Raised when rate limit is exceeded."""
    status_code = 429
    error_code = "rate_limit_error"


class CircuitBreakerError(CoreError):
    """Raised when circuit breaker is open."""
    status_code = 503
    error_code = "circuit_breaker_open"


def handle_exception(exc: Exception) -> tuple[int, dict[str, Any]]:
    """Convert any exception to HTTP response format.

    Returns tuple of (status_code, body).
    """
    if isinstance(exc, CoreError):
        return exc.status_code, exc.to_dict()

    return 500, {
        "error": "internal_error",
        "message": str(exc),
        "details": {},
    }
