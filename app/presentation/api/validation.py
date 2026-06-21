"""Common request validation helpers for API routes."""

from __future__ import annotations


def bounded_int(value: object, *, default: int, min_value: int, max_value: int) -> int:
    """Coerce *value* to int and clamp between *min_value* and *max_value*."""
    try:
        n = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        n = default
    return max(min_value, min(n, max_value))


def bounded_float(value: object, *, default: float, min_value: float, max_value: float) -> float:
    """Coerce *value* to float and clamp between *min_value* and *max_value*."""
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        f = default
    return max(min_value, min(f, max_value))


def whitelist_str(value: object, *, default: str, allowed: set[str]) -> str:
    """Return *value* if it is in *allowed*, otherwise *default*."""
    s = str(value) if value is not None else default
    return s if s in allowed else default
