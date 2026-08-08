"""TDX-based scenario optimization factory functions for data optimizer routes."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.domain.shared.tdx_paths import resolve_tdx_root
from app.infrastructure.providers.tdx_file_adapter import (
    TDXFileHistoryAdapter,
    TDXFileHistoryWithOptimization,
)


def resolve_configured_tdx_root() -> Path | None:
    """Resolve configured TDX root path from application settings."""
    settings = get_settings()
    raw = (getattr(settings, "tdx_root_path", None) or "").strip()
    return resolve_tdx_root(raw) if raw else None


def build_tdx_history_adapter(tdx_root: Path) -> TDXFileHistoryAdapter:
    """Build a TDX history adapter for symbol listing and data access."""
    return TDXFileHistoryAdapter(str(tdx_root))


def build_tdx_optimized_adapter(tdx_root: Path) -> TDXFileHistoryWithOptimization:
    """Build a TDX optimized adapter with preload and cache support."""
    return TDXFileHistoryWithOptimization(str(tdx_root))


def build_scenario_service(tdx_root: Path) -> Any:
    """Build a scenario-based data service backed by an optimized TDX adapter."""
    adapter = build_tdx_optimized_adapter(tdx_root)
    scenario_mod = importlib.import_module(
        "app.modules.strategy.services.strategy.scenario_optimizer_service"
    )
    return scenario_mod.ScenarioBasedDataService(tdx_adapter=adapter)
