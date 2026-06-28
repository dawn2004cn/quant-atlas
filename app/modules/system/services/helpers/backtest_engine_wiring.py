from __future__ import annotations

# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.backtest_engine_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.backtest_engine_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound backtest engine factory for application services."""

from collections.abc import Callable

from app.domain.ports.quant_ports import IBacktestEngine

_factory: Callable[[], IBacktestEngine] | None = None
def bind_backtest_engine_factory(factory: Callable[[], IBacktestEngine]) -> None:
    global _factory
    _factory = factory
def create_backtest_engine() -> IBacktestEngine:
    if _factory is None:
        raise RuntimeError(
            "Backtest engine factory not configured; bootstrap must call bind_backtest_engine_factory()"
        )
    return _factory()
