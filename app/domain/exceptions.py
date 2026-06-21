from __future__ import annotations
"""Domain-level exceptions, agnostic of framework or delivery mechanism.

This module implements the exception standardization from midify_plan8.md:
- AppError: Top-level application exceptions
- DomainError: Business logic exceptions
- RepositoryError: Data access exceptions
"""


from typing import Any


class AppError(Exception):
    """Top-level application exception.

    All application-level exceptions should inherit from this.
    Provides standardized error handling for API layer.
    """

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class DomainError(AppError):
    """Base class for all domain exceptions.

    DomainError is for business logic violations.
    Inherits from AppError for unified API handling.
    """

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, code, details)


class RepositoryError(AppError):
    """Exception for data access layer errors.

    Used for database, cache, and external API failures.
    """
    CODE = "REPOSITORY_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, self.CODE, details)


class ServiceError(AppError):
    """Exception for service layer errors.

    Used when service methods fail.
    """
    CODE = "SERVICE_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, self.CODE, details)


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist."""
    CODE = "ENTITY_NOT_FOUND"

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} not found: {entity_id}",
            details={"entity_type": entity_type, "entity_id": entity_id},
        )


class InsufficientFundsError(DomainError):
    """Raised when an operation fails due to lack of balance."""
    CODE = "INSUFFICIENT_FUNDS"

    def __init__(self, required: float, available: float):
        super().__init__(
            message=f"Insufficient funds: required {required}, available {available}",
            details={"required": required, "available": available},
        )


class InvalidOperationError(DomainError):
    """Raised when a business rule is violated."""
    CODE = "INVALID_OPERATION"

    def __init__(self, message: str, operation: str | None = None):
        details = {"operation": operation} if operation else {}
        super().__init__(message, self.CODE, details)


class StrategyNotEnabledError(DomainError):
    """Raised when attempting to use a disabled or non-existent strategy."""
    CODE = "STRATEGY_NOT_ENABLED"

    def __init__(self, strategy_name: str):
        super().__init__(
            message=f"Strategy not enabled: {strategy_name}",
            details={"strategy_name": strategy_name},
        )


class MarketClosedError(DomainError):
    """Raised when an operation requires an open market."""
    CODE = "MARKET_CLOSED"

    def __init__(self, market: str):
        super().__init__(
            message=f"Market is closed: {market}",
            details={"market": market},
        )


class InvalidConfigurationError(DomainError):
    """Raised when domain configuration is invalid or missing."""
    CODE = "INVALID_CONFIGURATION"

    def __init__(self, config_key: str, reason: str):
        super().__init__(
            message=f"Invalid configuration for {config_key}: {reason}",
            details={"config_key": config_key, "reason": reason},
        )


class MarketAnalysisError(DomainError):
    """Raised when market analysis fails."""
    CODE = "MARKET_ANALYSIS_ERROR"

    def __init__(self, symbol: str, reason: str):
        super().__init__(
            message=f"Analysis failed for {symbol}: {reason}",
            details={"symbol": symbol, "reason": reason},
        )


class CriticalSecurityError(AppError):
    """Critical security error that must halt the system.

    Used for security misconfigurations that could lead
    to data breaches or unauthorized access.
    """
    CODE = "CRITICAL_SECURITY_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, self.CODE, details or {})


# Data-specific exceptions
class DataNotFoundError(DomainError):
    """Raised when requested data is not found."""
    CODE = "DATA_NOT_FOUND"

    def __init__(self, data_type: str, query: str):
        super().__init__(
            message=f"{data_type} not found: {query}",
            details={"data_type": data_type, "query": query},
        )


class DataValidationError(DomainError):
    """Raised when data validation fails."""
    CODE = "DATA_VALIDATION_ERROR"

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation failed for {field}: {reason}",
            details={"field": field, "reason": reason},
        )


# Service-specific exceptions
class ServiceUnavailableError(ServiceError):
    """Raised when a service is temporarily unavailable."""
    CODE = "SERVICE_UNAVAILABLE"

    def __init__(self, service_name: str, reason: str = "temporarily unavailable"):
        super().__init__(
            message=f"Service {service_name} is {reason}",
            details={"service": service_name},
        )


class RateLimitExceededError(ServiceError):
    """Raised when API rate limit is exceeded."""
    CODE = "RATE_LIMIT_EXCEEDED"

    def __init__(self, endpoint: str, limit: int):
        super().__init__(
            message=f"Rate limit exceeded for {endpoint}",
            details={"endpoint": endpoint, "limit": limit},
        )


# ── Market data exceptions ──────────────────────────────────────────────


class MarketDataNotFoundError(DomainError):
    """Raised when market data for a symbol/timeframe is not available."""
    CODE = "MARKET_DATA_NOT_FOUND"

    def __init__(self, symbol: str, timeframe: str = ""):
        super().__init__(
            message=f"Market data not found: {symbol}{f' ({timeframe})' if timeframe else ''}",
            details={"symbol": symbol, "timeframe": timeframe},
        )


class ExecutionError(DomainError):
    """Raised when a trading execution fails."""
    CODE = "EXECUTION_ERROR"

    def __init__(self, reason: str, order_id: str | None = None):
        super().__init__(
            message=f"Execution failed: {reason}",
            details={"order_id": order_id, "reason": reason},
        )


class InsufficientQuotaError(DomainError):
    """Raised when allocation quota is exhausted."""
    CODE = "INSUFFICIENT_QUOTA"

    def __init__(self, allocation_id: str, remaining: float, required: float):
        super().__init__(
            message=f"Insufficient quota: {remaining}/{required}",
            details={"allocation_id": allocation_id, "remaining": remaining, "required": required},
        )


# ── Bootstrap / infrastructure exceptions ──────────────────────────────


class RequiredComponentError(RuntimeError):
    """Raised when a required bootstrap component fails to initialize."""
    pass


# ── Cross-cutting exception aliases (previously in app.application.errors) ──
# These are kept here for infrastructure-layer consumers that need exception
# types shared across layers. The canonical definitions remain in
# app.application.errors; import from here to avoid infra→application imports.


class ValidationError(Exception):
    """Parameter/validation error shared across layers."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthorizationError(Exception):
    """Authentication/authorization failure shared across layers."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
