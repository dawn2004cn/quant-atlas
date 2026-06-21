from __future__ import annotations
"""API Error Handling.

Unified error responses and exception handlers.
"""


import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from flask import jsonify



from app.core.logger import get_logger

logger = get_logger(__name__)


class ErrorCode(Enum):
    """API error codes."""
    UNKNOWN = "UNKNOWN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


@dataclass
class APIError:
    """API error response."""
    code: ErrorCode
    message: str
    details: Optional[dict] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "timestamp": datetime.now().isoformat(),
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        if self.request_id:
            result["error"]["request_id"] = self.request_id
        return result
    
    def to_response(self, status_code: int):
        """Convert to Flask response."""
        return jsonify(self.to_dict()), status_code


class APIException(Exception):
    """Base API exception."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        status_code: int = 500,
        details: dict = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)
    
    def to_response(self):
        """Convert to Flask response."""
        error = APIError(
            code=self.code,
            message=self.message,
            details=self.details
        )
        return error.to_response(self.status_code)


class NotFoundException(APIException):
    """Resource not found."""
    
    def __init__(self, resource: str, identifier: str = None):
        msg = f"{resource} not found"
        if identifier:
            msg = f"{resource} '{identifier}' not found"
        super().__init__(
            msg,
            code=ErrorCode.NOT_FOUND,
            status_code=404
        )


class ValidationException(APIException):
    """Validation error."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details
        )


class UnauthorizedException(APIException):
    """Unauthorized access."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message,
            code=ErrorCode.UNAUTHORIZED,
            status_code=401
        )


class ForbiddenException(APIException):
    """Forbidden access."""
    
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message,
            code=ErrorCode.FORBIDDEN,
            status_code=403
        )


class ConflictException(APIException):
    """Resource conflict."""
    
    def __init__(self, message: str):
        super().__init__(
            message,
            code=ErrorCode.CONFLICT,
            status_code=409
        )


class RateLimitedException(APIException):
    """Rate limited."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Rate limited. Retry after {retry_after} seconds",
            code=ErrorCode.RATE_LIMITED,
            status_code=429,
            details={"retry_after": retry_after}
        )


class ServiceUnavailableException(APIException):
    """Service unavailable."""
    
    def __init__(self, message: str = "Service unavailable"):
        super().__init__(
            message,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503
        )


def handle_exception(exc: Exception) -> tuple:
    """Handle any exception."""
    if isinstance(exc, APIException):
        return exc.to_response(exc.status_code)
    
    logger.exception(f"Unhandled exception: {exc}")
    
    error = APIError(
        code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error"
    )
    return error.to_response(500)


def register_error_handlers(app):
    """Deprecated: use ``register_api_error_handlers`` from error_handlers module."""
    import warnings

    warnings.warn(
        "register_error_handlers is deprecated; use register_api_error_handlers",
        DeprecationWarning,
        stacklevel=2,
    )
    from app.presentation.api.error_handlers import register_api_error_handlers

    register_api_error_handlers(app)


__all__ = [
    "ErrorCode",
    "APIError",
    "APIException",
    "NotFoundException",
    "ValidationException",
    "UnauthorizedException",
    "ForbiddenException",
    "ConflictException",
    "RateLimitedException",
    "ServiceUnavailableException",
    "handle_exception",
    "register_error_handlers",
]