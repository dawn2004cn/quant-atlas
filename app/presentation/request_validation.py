from __future__ import annotations

"""Request Validation.

Schema validation for API requests.
"""


import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.presentation.api_errors import ValidationException

logger = get_logger(__name__)


@dataclass
class FieldValidator:
    """Validator for a single field."""
    name: str
    field_type: type
    required: bool = False
    pattern: str = None
    min_value: Any = None
    max_value: Any = None
    allowed_values: list = None


class RequestValidator:
    """Validates API requests."""

    def __init__(self):
        self._validators: dict[str, list[FieldValidator]] = {}
        self._register_default_validators()
        logger.info("RequestValidator initialized")

    def _register_default_validators(self) -> None:
        """Register default validators."""
        self.register("screening", [
            FieldValidator("filters", dict, required=True),
            FieldValidator("limit", int, required=False, min_value=1, max_value=1000),
        ])
        self.register("stock_code", [
            FieldValidator("code", str, required=True, pattern=r"^\d{6}$"),
        ])
        self.register("order", [
            FieldValidator("stock_code", str, required=True, pattern=r"^\d{6}$"),
            FieldValidator("quantity", int, required=True, min_value=1),
            FieldValidator("price", float, required=True, min_value=0.01),
        ])
        self.register("signal", [
            FieldValidator("stock_code", str, required=True, pattern=r"^\d{6}$"),
            FieldValidator("signal_type", str, required=True, allowed_values=["buy", "sell"]),
        ])

    def register(self, schema: str, validators: list[FieldValidator]) -> None:
        """Register validator for schema."""
        self._validators[schema] = validators

    def validate(self, schema: str, data: dict) -> dict:
        """Validate request data."""
        if schema not in self._validators:
            logger.warning(f"No validator for schema: {schema}")
            return data

        validators = self._validators[schema]
        errors = []

        for field in validators:
            value = data.get(field.name)

            # Check required
            if field.required and value is None:
                errors.append(f"Missing required field: {field.name}")
                continue

            if value is None:
                continue

            # Check type
            if not isinstance(value, field.field_type):
                errors.append(
                    f"Invalid type for {field.name}: expected {field.field_type.__name__}"
                )
                continue

            # Check pattern
            if field.pattern and isinstance(value, str):
                if not re.match(field.pattern, value):
                    errors.append(f"Invalid format for {field.name}")

            # Check range
            if field.min_value is not None and value < field.min_value:
                errors.append(f"{field.name} must be >= {field.min_value}")

            if field.max_value is not None and value > field.max_value:
                errors.append(f"{field.name} must be <= {field.max_value}")

            # Check allowed values
            if field.allowed_values and value not in field.allowed_values:
                errors.append(f"{field.name} must be one of: {field.allowed_values}")

        if errors:
            raise ValidationException("Validation failed", details={"errors": errors})

        return data

    def validate_required(self, data: dict, required_fields: list[str]) -> None:
        """Validate required fields."""
        missing = [f for f in required_fields if f not in data or data[f] is None]
        if missing:
            raise ValidationException(
                "Missing required fields",
                details={"missing": missing}
            )


class StockCodeValidator:
    """Validates stock codes."""

    @staticmethod
    def validate(code: str) -> str:
        """Validate stock code format."""
        if not code:
            raise ValidationException("Stock code is required")

        if not re.match(r"^\d{6}$", code):
            raise ValidationException(
                "Invalid stock code format",
                details={"expected": "6 digits", "got": code}
            )

        return code

    @staticmethod
    def normalize(code: str) -> str:
        """Normalize stock code."""
        code = code.strip().upper()
        return code


class DateRangeValidator:
    """Validates date ranges."""

    @staticmethod
    def validate(start_date: str, end_date: str) -> tuple[datetime, datetime]:
        """Validate date range."""
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise ValidationException("Invalid date format (use ISO 8601)") from None

        if start > end:
            raise ValidationException("start_date must be before end_date")

        return start, end

    @staticmethod
    def validate_days(start_date: str, end_date: str, max_days: int = 365) -> None:
        """Validate date range is within max days."""
        start, end = DateRangeValidator.validate(start_date, end_date)
        days = (end - start).days

        if days > max_days:
            raise ValidationException(
                f"Date range exceeds maximum {max_days} days",
                details={"days": days, "max": max_days}
            )


# Global instance
_request_validator: RequestValidator | None = None


def get_request_validator() -> RequestValidator:
    """Get global request validator."""
    global _request_validator
    if _request_validator is None:
        _request_validator = RequestValidator()
    return _request_validator


__all__ = [
    "FieldValidator",
    "RequestValidator",
    "StockCodeValidator",
    "DateRangeValidator",
    "get_request_validator",
]
