from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.strategy_providers_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.strategy_providers_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound strategy/backtest provider factories for application services."""

from collections.abc import Callable
from typing import Any
from app.domain.ports import BacktestProvider, StrategyProvider


_strategy_factory: Callable[[Any], StrategyProvider] | None = None
_backtest_factory: Callable[[], BacktestProvider] | None = None
def bind_strategy_provider_factories(
    *,
    strategy_factory: Callable[[Any], StrategyProvider],
    backtest_factory: Callable[[], BacktestProvider],
) -> None:
    global _strategy_factory, _backtest_factory
    _strategy_factory = strategy_factory
    _backtest_factory = backtest_factory
def create_strategy_provider(market_provider: Any) -> StrategyProvider:
    if _strategy_factory is None:
        raise RuntimeError(
            "Strategy provider factories not configured; bootstrap must bind them"
        )
    return _strategy_factory(market_provider)
def create_backtest_provider() -> BacktestProvider:
    if _backtest_factory is None:
        raise RuntimeError(
            "Strategy provider factories not configured; bootstrap must bind them"
        )
    return _backtest_factory()
