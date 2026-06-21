"""Alias module for data optimizer route factory functions.

Re-exports are preferred; this module provides concrete factory functions
for TDX-based scenario optimization routes.
"""

from pathlib import Path

from app.config import get_settings
from app.domain.shared.tdx_paths import resolve_tdx_root
from app.infrastructure.providers.tdx_file_adapter import (
    TDXFileHistoryAdapter,
    TDXFileHistoryWithOptimization,
)
from app.modules.strategy.services.strategy.scenario_optimizer_service import (
    ScenarioBasedDataService,
)


def resolve_configured_tdx_root() -> Path | None:
    """Resolve configured TDX root path from application settings.

    Returns:
        Resolved Path if TDX_ROOT_PATH is set and directory exists, else None.
    """
    settings = get_settings()
    raw = (getattr(settings, "tdx_root_path", None) or "").strip()
    return resolve_tdx_root(raw) if raw else None


def build_tdx_history_adapter(tdx_root: Path) -> TDXFileHistoryAdapter:
    """Build a TDX history adapter for symbol listing and data access.

    Args:
        tdx_root: Path to TDX installation root (vipdoc parent).

    Returns:
        Configured TDXFileHistoryAdapter instance.
    """
    return TDXFileHistoryAdapter(str(tdx_root))


def build_tdx_optimized_adapter(tdx_root: Path) -> TDXFileHistoryWithOptimization:
    """Build a TDX optimized adapter with preload and cache support.

    Args:
        tdx_root: Path to TDX installation root.

    Returns:
        Configured TDXFileHistoryWithOptimization instance.
    """
    return TDXFileHistoryWithOptimization(str(tdx_root))


def build_scenario_service(tdx_root: Path) -> ScenarioBasedDataService:
    """Build a scenario-based data service backed by an optimized TDX adapter.

    Args:
        tdx_root: Path to TDX installation root.

    Returns:
        ScenarioBasedDataService instance ready for scan/backtest operations.
    """
    adapter = build_tdx_optimized_adapter(tdx_root)
    return ScenarioBasedDataService(tdx_adapter=adapter)
