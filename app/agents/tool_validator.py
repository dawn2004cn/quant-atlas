from __future__ import annotations
"""Input sanitization and validation for Agent tools.

This implements tool contract validation from quant_plan.md:
- Strict Pydantic validation for all tool inputs
- Prevents LLM hallucination from breaking system
- Provides clear error messages
"""


import re
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class ValidationResult:
    """Result of input validation."""

    def __init__(self, is_valid: bool, errors: list[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []


class InputSanitizer:
    """Input sanitizer for agent tool calls."""

    @staticmethod
    def sanitize_symbol(symbol: str) -> ValidationResult:
        """Validate and sanitize stock symbol."""
        if not symbol:
            return ValidationResult(False, ["Symbol cannot be empty"])

        symbol = symbol.strip().upper()

        patterns = [
            r"^(SH|SZ|BJ|HK|US)?[0-9]{6}$",
            r"^(BTC|ETH|SOL)[0-9A-Z]{,20}$",
        ]

        if not any(re.match(p, symbol) for p in patterns):
            return ValidationResult(False, [f"Invalid symbol format: {symbol}"])

        return ValidationResult(True)

    @staticmethod
    def sanitize_date(date_str: str) -> ValidationResult:
        """Validate date string format."""
        if not date_str:
            return ValidationResult(False, ["Date cannot be empty"])

        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(date_pattern, date_str):
            return ValidationResult(False, [f"Invalid date format: {date_str}. Expected YYYY-MM-DD"])

        return ValidationResult(True)

    @staticmethod
    def sanitize_date_range(start: str, end: str) -> ValidationResult:
        """Validate date range."""
        errors = []

        start_result = InputSanitizer.sanitize_date(start)
        if not start_result.is_valid:
            errors.extend(start_result.errors)

        end_result = InputSanitizer.sanitize_date(end)
        if not end_result.is_valid:
            errors.extend(end_result.errors)

        if start > end:
            errors.append(f"Start date {start} is after end date {end}")

        return ValidationResult(len(errors) == 0, errors)

    @staticmethod
    def sanitize_numeric(value: Any, field_name: str, min_val: float = None, max_val: float = None) -> ValidationResult:
        """Validate numeric value."""
        errors = []

        try:
            num = float(value)
        except (TypeError, ValueError):
            return ValidationResult(False, [f"{field_name} must be numeric"])

        if min_val is not None and num < min_val:
            errors.append(f"{field_name} {num} is below minimum {min_val}")

        if max_val is not None and num > max_val:
            errors.append(f"{field_name} {num} exceeds maximum {max_val}")

        return ValidationResult(len(errors) == 0, errors)

    @staticmethod
    def sanitize_list(value: Any, field_name: str, max_length: int = 100) -> ValidationResult:
        """Validate list input."""
        errors = []

        if not isinstance(value, (list, tuple)):
            return ValidationResult(False, [f"{field_name} must be a list"])

        if len(value) > max_length:
            errors.append(f"{field_name} has {len(value)} items, exceeds maximum {max_length}")

        return ValidationResult(len(errors) == 0, errors)

    @staticmethod
    def sanitize_dict(value: Any, field_name: str, allowed_keys: list[str] = None) -> ValidationResult:
        """Validate dict input."""
        errors = []

        if not isinstance(value, dict):
            return ValidationResult(False, [f"{field_name} must be a dictionary"])

        if allowed_keys:
            extra = set(value.keys()) - set(allowed_keys)
            if extra:
                errors.append(f"{field_name} contains unknown keys: {extra}")

        return ValidationResult(len(errors) == 0, errors)


class ToolInputValidator:
    """Validator for specific tool inputs."""

    @staticmethod
    def validate_get_market_data(symbol: str, start_date: str = None, end_date: str = None) -> ValidationResult:
        """Validate get_market_data tool input."""
        errors = []

        symbol_result = InputSanitizer.sanitize_symbol(symbol)
        if not symbol_result.is_valid:
            errors.extend(symbol_result.errors)

        if start_date and end_date:
            range_result = InputSanitizer.sanitize_date_range(start_date, end_date)
            if not range_result.is_valid:
                errors.extend(range_result.errors)
        elif start_date:
            date_result = InputSanitizer.sanitize_date(start_date)
            if not date_result.is_valid:
                errors.extend(date_result.errors)
        elif end_date:
            date_result = InputSanitizer.sanitize_date(end_date)
            if not date_result.is_valid:
                errors.extend(date_result.errors)

        return ValidationResult(len(errors) == 0, errors)

    @staticmethod
    def validate_get_stock_news(symbol: str, limit: int = None) -> ValidationResult:
        """Validate get_stock_news tool input."""
        errors = []

        symbol_result = InputSanitizer.sanitize_symbol(symbol)
        if not symbol_result.is_valid:
            errors.extend(symbol_result.errors)

        if limit is not None:
            num_result = InputSanitizer.sanitize_numeric(limit, "limit", min_val=1, max_val=100)
            if not num_result.is_valid:
                errors.extend(num_result.errors)

        return ValidationResult(len(errors) == 0, errors)

    @staticmethod
    def validate_run_backtest(
        strategy: str,
        start_date: str,
        end_date: str,
        initial_cash: float = None,
    ) -> ValidationResult:
        """Validate run_backtest tool input."""
        errors = []

        if not strategy:
            errors.append("Strategy cannot be empty")

        date_result = InputSanitizer.sanitize_date_range(start_date, end_date)
        if not date_result.is_valid:
            errors.extend(date_result.errors)

        if initial_cash is not None:
            cash_result = InputSanitizer.sanitize_numeric(initial_cash, "initial_cash", min_val=0)
            if not cash_result.is_valid:
                errors.extend(cash_result.errors)

        return ValidationResult(len(errors) == 0, errors)

    @staticmethod
    def validate_alpha_formula(formula: str) -> ValidationResult:
        """Validate alpha formula."""
        errors = []

        if not formula:
            errors.append("Formula cannot be empty")
            return ValidationResult(False, errors)

        if len(formula) > 2000:
            errors.append(f"Formula too long: {len(formula)} chars, max 2000")

        forbidden = ["import", "exec", "eval", "open(", "os.", "sys."]
        for f in forbidden:
            if f in formula.lower():
                errors.append(f"Formula contains forbidden keyword: {f}")

        return ValidationResult(len(errors) == 0, errors)


_validator: ToolInputValidator | None = None
_sanitizer: InputSanitizer | None = None


def get_tool_validator() -> ToolInputValidator:
    """Get the global tool validator."""
    global _validator
    if _validator is None:
        _validator = ToolInputValidator()
    return _validator


def get_input_sanitizer() -> InputSanitizer:
    """Get the global input sanitizer."""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = InputSanitizer()
    return _sanitizer
