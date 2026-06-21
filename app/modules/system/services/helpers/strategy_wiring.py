from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.strategy_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.strategy_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound strategy optimization infrastructure for application services."""

from collections.abc import Callable
from app.domain.ports.strategy_ports import WalkForwardOptimizerPort


_create_walk_forward: Callable[[], WalkForwardOptimizerPort] | None = None
def bind_strategy_infrastructure(*, walk_forward_factory: Callable[[], WalkForwardOptimizerPort]) -> None:
    global _create_walk_forward
    _create_walk_forward = walk_forward_factory
def create_default_walk_forward_optimizer() -> WalkForwardOptimizerPort:
    if _create_walk_forward is None:
        raise RuntimeError("Strategy infrastructure not configured; bootstrap must bind it")
    return _create_walk_forward()
