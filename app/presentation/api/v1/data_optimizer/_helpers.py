"""Shared helpers for data-optimizer HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.application.errors import ExternalServiceError, ValidationError
from app.modules.system.services.helpers.data_optimizer_access import (
    build_scenario_service,
    resolve_configured_tdx_root,
)


def parse_symbols_param(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def require_symbols(symbols: list[str]) -> None:
    if not symbols:
        raise ValidationError("symbols_required")


def resolve_tdx_root() -> Path:
    tdx_root = resolve_configured_tdx_root()
    if not tdx_root:
        raise ExternalServiceError("tdx_not_configured")
    return tdx_root


def scenario_service(tdx_root: Path) -> Any:
    return build_scenario_service(tdx_root)
