from __future__ import annotations
"""Request parameter parsing helpers for API routes."""


from typing import Any, Type
from pydantic import BaseModel, ValidationError as PydanticValidationError

from ...application.errors import ValidationError


def parse_int_param(
    raw_value,
    *,
    name: str,
    default: int | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """Parse integer-like request value with consistent validation errors."""
    value = raw_value
    if value is None or value == "":
        if default is None:
            raise ValidationError(f"{name} is required")
        value = default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer") from exc

    if min_value is not None and parsed < min_value:
        raise ValidationError(f"{name} must be >= {min_value}")
    if max_value is not None and parsed > max_value:
        raise ValidationError(f"{name} must be <= {max_value}")
    return parsed


def parse_bool_param(raw_value, *, name: str, default: bool = False) -> bool:
    """Parse JSON/body boolean (bool, 0/1, true/false 字符串)。"""
    if raw_value is None or raw_value == "":
        return default
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, (int, float)):
        return bool(raw_value)
    s = str(raw_value).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    raise ValidationError(f"{name} must be a boolean")


def parse_optional_bool_param(raw_value, *, name: str) -> bool | None:
    """``None`` 表示请求体未传该字段（与 ``false`` 区分）。"""
    if raw_value is None:
        return None
    if raw_value == "":
        return None
    return parse_bool_param(raw_value, name=name, default=False)


def parse_float_param(
    raw_value,
    *,
    name: str,
    default: float | None = None,
    min_value: float | None = None,
) -> float:
    """Parse float-like request value with consistent validation errors."""
    value = raw_value
    if value is None or value == "":
        if default is None:
            raise ValidationError(f"{name} is required")
        value = default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be a number") from exc

    if min_value is not None and parsed < min_value:
        raise ValidationError(f"{name} must be >= {min_value}")
    return parsed


def parse_dto(
    raw_data: dict[str, Any] | None,
    dto_class: Type[BaseModel],
    *,
    partial: bool = False,
) -> BaseModel:
    """Parse request JSON into a Pydantic DTO with consistent validation errors."""
    if raw_data is None:
        raw_data = {}
    try:
        if partial:
            return dto_class.model_construct(**raw_data)
        return dto_class(**raw_data)
    except PydanticValidationError as exc:
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(l) for l in first.get("loc", []))
        msg = first.get("msg", "validation failed")
        raise ValidationError(f"{loc}: {msg}" if loc else msg) from exc


def parse_json_body(raw_json: dict[str, Any] | None) -> dict[str, Any]:
    """Parse JSON request body, returning empty dict if None."""
    return raw_json or {}
