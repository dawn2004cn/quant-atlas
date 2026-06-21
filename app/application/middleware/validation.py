from __future__ import annotations
"""Request validation middleware for API endpoints."""


from functools import wraps
from typing import Any, Callable
from flask import request, jsonify

from app.core.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Validation error exception."""

    def __init__(self, message: str, field: str = ""):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_required_fields(required: list[str]) -> Callable:
    """Decorator to validate required fields in request JSON."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json() or {}
            missing = [f for f in required if f not in data or data[f] is None]

            if missing:
                return jsonify({
                    "error": "Missing required fields",
                    "missing": missing,
                }), 400

            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_code_format(code: str) -> bool:
    """Validate stock code format."""
    if not code:
        return False

    if len(code) == 6 and code.isdigit():
        return True

    if code.startswith(("sh", "sz", "SH", "SZ")):
        return len(code) == 8 and code[2:].isdigit()

    return False


def validate_codes(codes: list[str]) -> tuple[bool, list[str]]:
    """Validate a list of stock codes."""
    invalid = [c for c in codes if not validate_code_format(c)]
    return len(invalid) == 0, invalid


def validate_price(price: float) -> bool:
    """Validate price value."""
    return price > 0 and price < 1000000


def validate_quantity(quantity: int) -> bool:
    """Validate quantity value."""
    return quantity > 0 and quantity < 100000000


class RequestValidator:
    """Request validation helper class."""

    @staticmethod
    def validate_stock_code(code: str) -> None:
        """Validate a single stock code."""
        if not validate_code_format(code):
            raise ValidationError(f"Invalid stock code format: {code}", "code")

    @staticmethod
    def validate_stock_codes(codes: list[str]) -> None:
        """Validate multiple stock codes."""
        valid, invalid = validate_codes(codes)
        if not valid:
            raise ValidationError(f"Invalid stock codes: {invalid}", "codes")

    @staticmethod
    def validate_price(price: float, field: str = "price") -> None:
        """Validate price value."""
        if not validate_price(price):
            raise ValidationError(f"Invalid price value: {price}", field)

    @staticmethod
    def validate_quantity(quantity: int, field: str = "quantity") -> None:
        """Validate quantity value."""
        if not validate_quantity(quantity):
            raise ValidationError(f"Invalid quantity: {quantity}", field)

    @staticmethod
    def validate_price_range(price: float, min_price: float, max_price: float, field: str = "price") -> None:
        """Validate price is within range."""
        if price < min_price or price > max_price:
            raise ValidationError(f"Price {price} not in range [{min_price}, {max_price}]", field)

    @staticmethod
    def validate_percentage(value: float, field: str = "value") -> None:
        """Validate percentage value (0-100)."""
        if value < 0 or value > 100:
            raise ValidationError(f"Percentage {value} not in range [0, 100]", field)


def handle_validation_error(error: ValidationError):
    """Handle validation errors."""
    return jsonify({
        "error": "Validation error",
        "message": error.message,
        "field": error.field,
    }), 400


def register_validators(app):
    """Register validators with Flask app."""
    from flask import Flask

    @app.errorhandler(ValidationError)
    def handle_validation_error_wrapper(error):
        return handle_validation_error(error)


__all__ = [
    "ValidationError",
    "validate_required_fields",
    "validate_code_format",
    "validate_codes",
    "validate_price",
    "validate_quantity",
    "RequestValidator",
    "handle_validation_error",
    "register_validators",
]