"""Shared helpers for signal-flag HTTP routes."""

from __future__ import annotations

from app.application.errors import ValidationError


def parse_signal_flag_max_stocks(body: dict) -> int:
    """Default 800 (same as fund manager); max_stocks=0 means unlimited."""
    raw = body.get("max_stocks")
    if raw is None or raw == "":
        return 800
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError("max_stocks must be an integer") from exc
    if value < 0:
        raise ValidationError("max_stocks must be >= 0")
    if value == 0:
        return 0
    return min(value, 8000)
