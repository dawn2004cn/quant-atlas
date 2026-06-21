from __future__ import annotations
# -*- coding: utf-8 -*-
"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.trading_risk_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

import warnings

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.trading_risk_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


"""Bound trading/risk infrastructure defaults for application services."""

from collections.abc import Callable
from app.domain.ports.pre_trade_validation_port import PreTradeValidationPort
from app.domain.ports.risk_ports import PositionSizingPort, RiskPreFlightPort


_create_pre_trade_validator: Callable[[], PreTradeValidationPort] | None = None
_create_risk_preflight: Callable[[], RiskPreFlightPort] | None = None
_create_position_sizing: Callable[[], PositionSizingPort] | None = None
def bind_trading_risk_defaults(
    *,
    pre_trade_validator_factory: Callable[[], PreTradeValidationPort],
    risk_preflight_factory: Callable[[], RiskPreFlightPort],
    position_sizing_factory: Callable[[], PositionSizingPort],
) -> None:
    global _create_pre_trade_validator, _create_risk_preflight, _create_position_sizing
    _create_pre_trade_validator = pre_trade_validator_factory
    _create_risk_preflight = risk_preflight_factory
    _create_position_sizing = position_sizing_factory
def create_pre_trade_validator() -> PreTradeValidationPort:
    if _create_pre_trade_validator is None:
        raise RuntimeError("Trading risk defaults not configured; bootstrap must bind them")
    return _create_pre_trade_validator()
def create_default_risk_preflight() -> RiskPreFlightPort:
    if _create_risk_preflight is None:
        raise RuntimeError("Trading risk defaults not configured; bootstrap must bind them")
    return _create_risk_preflight()
def create_default_position_sizing() -> PositionSizingPort:
    if _create_position_sizing is None:
        raise RuntimeError("Trading risk defaults not configured; bootstrap must bind them")
    return _create_position_sizing()
