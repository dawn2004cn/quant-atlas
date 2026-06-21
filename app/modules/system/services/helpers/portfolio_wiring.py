from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.portfolio_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.portfolio_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound portfolio optimization infrastructure for application services."""

from collections.abc import Callable
from app.domain.ports.portfolio_ports import AttributionAnalysisPort, PortfolioOptimizerPort


_create_markowitz: Callable[[], PortfolioOptimizerPort] | None = None
_create_black_litterman: Callable[[], PortfolioOptimizerPort] | None = None
_create_attribution: Callable[[], AttributionAnalysisPort] | None = None
def bind_portfolio_infrastructure(
    *,
    markowitz_factory: Callable[[], PortfolioOptimizerPort],
    black_litterman_factory: Callable[[], PortfolioOptimizerPort],
    attribution_factory: Callable[[], AttributionAnalysisPort],
) -> None:
    global _create_markowitz, _create_black_litterman, _create_attribution
    _create_markowitz = markowitz_factory
    _create_black_litterman = black_litterman_factory
    _create_attribution = attribution_factory
def create_markowitz_optimizer() -> PortfolioOptimizerPort:
    if _create_markowitz is None:
        raise RuntimeError("Portfolio infrastructure not configured; bootstrap must bind it")
    return _create_markowitz()
def create_black_litterman_optimizer() -> PortfolioOptimizerPort:
    if _create_black_litterman is None:
        raise RuntimeError("Portfolio infrastructure not configured; bootstrap must bind it")
    return _create_black_litterman()
def create_default_attribution_analysis() -> AttributionAnalysisPort:
    if _create_attribution is None:
        raise RuntimeError("Portfolio infrastructure not configured; bootstrap must bind it")
    return _create_attribution()
