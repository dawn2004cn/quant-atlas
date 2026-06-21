"""Backtest engine registry.

The codebase historically shipped five different backtest engines with
inconsistent cost models, slippage handling, and settlement rules. This
registry provides a single entry point for selecting an engine by name so
new callers default to the production-grade ``CompositeEngine`` family and
legacy engines are only used when explicitly requested.

Engine tiers:
- ``production``: ``CompositeEngine`` and per-market sub-engines. Use for any
  result that influences trading decisions.
- ``legacy``: the original ``BacktestEngine`` in ``app/infrastructure/providers``.
  Retained for backward compatibility; emits a ``DeprecationWarning`` on use.
- ``preview``: ``FastBacktestEngine`` used by the strategy wizard. May fall
  back to synthetic data; never use for real decisions.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any, Callable

from app.core.logger import get_logger

logger = get_logger(__name__)


EngineFactory = Callable[..., Any]


class BacktestEngineRegistry:
    """Registry of backtest engine factories keyed by tier name."""

    def __init__(self):
        self._factories: dict[str, EngineFactory] = {}
        self._descriptions: dict[str, str] = {}

    def register(
        self,
        name: str,
        factory: EngineFactory,
        *,
        description: str = "",
    ) -> None:
        self._factories[name] = factory
        self._descriptions[name] = description

    def get(self, name: str = "production") -> Any:
        """Instantiate and return the engine registered under *name*."""
        factory = self._factories.get(name)
        if factory is None:
            raise KeyError(
                f"Unknown backtest engine '{name}'. "
                f"Registered: {sorted(self._factories)}"
            )
        if name in ("legacy", "preview"):
            warnings.warn(
                f"Backtest engine '{name}' is intended for {self._descriptions.get(name, 'non-production use')} only. "
                f"Use 'production' for results that influence trading decisions.",
                DeprecationWarning,
                stacklevel=2,
            )
            logger.warning("Instantiating deprecated backtest engine '%s'", name)
        return factory()

    def is_registered(self, name: str) -> bool:
        return name in self._factories

    def list_engines(self) -> dict[str, str]:
        return dict(self._descriptions)


_registry: BacktestEngineRegistry | None = None


def get_backtest_engine_registry() -> BacktestEngineRegistry:
    """Return the global backtest engine registry, lazily populated."""
    global _registry
    if _registry is not None:
        return _registry

    _registry = BacktestEngineRegistry()

    # Production: CompositeEngine (and its per-market sub-engines).
    def _make_production() -> Any:
        from app.infrastructure.agent.backtest.engines.composite import CompositeEngine

        return CompositeEngine()

    _registry.register(
        "production",
        _make_production,
        description="CompositeEngine with per-market sub-engines (A股 T+1, fees, slippage)",
    )

    # Legacy: original BacktestEngine (event-driven, single/portfolio).
    def _make_legacy() -> Any:
        from app.infrastructure.providers.backtest_engine import BacktestEngine

        return BacktestEngine()

    _registry.register(
        "legacy",
        _make_legacy,
        description="legacy BacktestEngine (deprecated; kept for backward compatibility)",
    )

    # Preview: FastBacktestEngine for the strategy wizard.
    def _make_preview() -> Any:
        from app.modules.strategy.services.strategy.fast_backtest_engine import (
            FastBacktestEngine,
        )
        from app.modules.data.services.data_lake_manager import DataLakeManager

        return FastBacktestEngine(lake_manager=DataLakeManager())

    _registry.register(
        "preview",
        _make_preview,
        description="FastBacktestEngine for wizard previews (may use synthetic data)",
    )

    return _registry


def reset_backtest_engine_registry() -> None:
    """Clear the cached registry (tests only)."""
    global _registry
    _registry = None
