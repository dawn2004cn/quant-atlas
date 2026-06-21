"""Shared helpers for portfolio HTTP routes."""

from __future__ import annotations

import logging

from app.application.errors import ValidationError

logger = logging.getLogger(__name__)


def parse_symbols_param(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def require_symbols(symbols: list[str]) -> None:
    if not symbols:
        raise ValidationError("symbols_required")
