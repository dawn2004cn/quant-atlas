"""Portfolio and risk bounded context module."""

from __future__ import annotations

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry
from app.modules.health import module_health_check


@register_module(name="portfolio_risk", description="Portfolio construction and trading risk")
class PortfolioRiskContextModule:
    """Portfolio + risk context: holdings, optimization, pre-flight checks.

    Services live under ``app/modules/portfolio_risk/services/``.
    Wired via ``wire_portfolio_service`` / ``wire_trading_risk_services`` in bootstrap.
    """

    services = []
    routes = [
        "portfolio",
        "risk",
        "trade_plan",
        "signal_observation",
    ]
    config_keys = []
    depends_on = ["system", "market_data"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        """Auto-invoked by ``initialize_all_modules`` when this module is enabled."""
        PortfolioRiskContextModule.wire(container)

        _subscribe_portfolio_regime_events(container)
        _init_module_memory(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("portfolio_risk", ['mysql', 'redis'])

    @staticmethod
    def autonomous_adjust(volatility_level: float = 0.0) -> dict[str, Any]:
        """Autonomous risk-threshold tuning based on market volatility.

        volatility_level: 0-1 normalized volatility (0=calm, 1=extreme).
        Returns: proposed config overrides.
        """
        base_stop = -0.08
        base_atr_mult = 3.0
        if volatility_level < 0.35:
            return {"RISK_STOP_LOSS_PCT": base_stop, "RISK_ATR_MULT": base_atr_mult}
        if volatility_level < 0.65:
            return {"RISK_STOP_LOSS_PCT": base_stop * 1.5, "RISK_ATR_MULT": base_atr_mult * 1.25}
        return {"RISK_STOP_LOSS_PCT": base_stop * 2.0, "RISK_ATR_MULT": base_atr_mult * 1.5}
__all__ = ["PortfolioRiskContextModule"]


import logging
from typing import Any

_logger = logging.getLogger(__name__)


def _on_regime_changed_portfolio(event: Any) -> None:
    """Adjust portfolio risk limits when market regime changes."""
    new_regime = getattr(event, "new_regime", "")
    confidence = getattr(event, "confidence", 0.0)
    _logger.info("Portfolio adjusting risk limits for regime: %s (confidence=%.2f)", new_regime, confidence)


def _subscribe_portfolio_regime_events(services: Any) -> None:
    """Subscribe to MarketRegimeChangedEvent if event bus is available."""
    try:
        from app.core.event_bus import MarketRegimeChangedEvent, get_event_bus

        bus = get_event_bus()
        bus.subscribe(MarketRegimeChangedEvent, _on_regime_changed_portfolio, priority=50)
        _logger.debug("PortfolioRiskModule subscribed to MarketRegimeChangedEvent")
    except (ImportError, AttributeError, RuntimeError, TypeError) as exc:
        _logger.debug("PortfolioRiskModule regime event subscribe skipped: %s", exc)


def _init_module_memory(container: Any) -> None:
    """Initialize portfolio module memory and inject into portfolio service."""
    try:
        from app.core.mesh.module_local_memory import ModuleLocalMemory
        from app.core.registry import get_module

        mod = get_module("portfolio_risk")
        if mod is None:
            return
        memory = mod.get_or_create_memory()
        portfolio = getattr(container, "portfolio_service", None)
        if portfolio is not None and hasattr(portfolio, "_local_memory"):
            portfolio._local_memory = memory
            _logger.info("PortfolioLocalMemory injected into portfolio_service")
    except (ImportError, AttributeError, RuntimeError, TypeError, OSError) as exc:
        _logger.debug("Module memory init skipped: %s", exc)
