"""Backward-compat shim — canonical path: ``app.modules.data.services.helpers.data_optimizer_access``."""
from __future__ import annotations

from app.modules.data.services.helpers.data_optimizer_access import (
    build_scenario_service,
    build_tdx_history_adapter,
    build_tdx_optimized_adapter,
    resolve_configured_tdx_root,
)

__all__ = [
    "resolve_configured_tdx_root",
    "build_tdx_history_adapter",
    "build_tdx_optimized_adapter",
    "build_scenario_service",
]
