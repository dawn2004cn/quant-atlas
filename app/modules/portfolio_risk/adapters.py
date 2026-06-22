"""Portfolio/Risk Service Adapters.

Adapters implement the Portfolio/Risk Ports using the current concrete services.
Each adapter wraps an existing service and adapts its interface to match
the corresponding port contract.

This enables:
1. Clean separation between route handlers and service implementations
2. Easy substitution of service implementations in tests
3. Clear migration path to independent microservice
"""

from __future__ import annotations

from typing import Any

from app.modules.portfolio_risk.ports import (
    PortfolioPort,
    RiskMetricsPort,
    TradePlanPort,
    SignalObservationPort,
    RiskCompanionPort,
)


class PortfolioAdapter(PortfolioPort):
    """Adapts PortfolioService to PortfolioPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_portfolio(self, user_id: int) -> dict[str, Any]:
        return self._service.get_portfolio(user_id)

    def update_portfolio(self, user_id: int, holdings: list[dict[str, Any]]) -> dict[str, Any]:
        return self._service.update_portfolio(user_id, holdings)


class RiskMetricsAdapter(RiskMetricsPort):
    """Adapts RiskApplicationService to RiskMetricsPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_risk_metrics(self, user_id: int) -> dict[str, Any]:
        return self._service.get_risk_metrics(user_id)

    def run_stress_test(self, user_id: int, scenario: str) -> dict[str, Any]:
        return self._service.run_stress_test(user_id, scenario)


class TradePlanAdapter(TradePlanPort):
    """Adapts TradePlanService to TradePlanPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def submit_trade_plan(self, user_id: int, plan: dict[str, Any]) -> dict[str, Any]:
        return self._service.submit_trade_plan(user_id, plan)

    def get_trade_plan(self, plan_id: str) -> dict[str, Any]:
        return self._service.get_trade_plan(plan_id)


class SignalObservationAdapter(SignalObservationPort):
    """Adapts SignalObservationService to SignalObservationPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def record_observation(self, signal_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        return self._service.record_observation(signal_id, outcome)


class RiskCompanionAdapter(RiskCompanionPort):
    """Adapts RiskCompanionService to RiskCompanionPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_companion(self, user_id: int) -> dict[str, Any]:
        return self._service.get_companion(user_id)


def create_portfolio_risk_ports(ctx: Any) -> dict[str, Any]:
    """Create all portfolio/risk ports from an ApiV1Context.

    This factory function maps context services to port adapters.
    Returns a dict of port_name -> port_instance.
    """
    ports = {}

    if getattr(ctx, "portfolio_service", None) is not None:
        ports["portfolio"] = PortfolioAdapter(ctx.portfolio_service)

    if getattr(ctx, "risk_service", None) is not None:
        ports["risk_metrics"] = RiskMetricsAdapter(ctx.risk_service)

    if getattr(ctx, "trade_plan_service", None) is not None:
        ports["trade_plan"] = TradePlanAdapter(ctx.trade_plan_service)

    if getattr(ctx, "signal_observation_service", None) is not None:
        ports["signal_observation"] = SignalObservationAdapter(
            ctx.signal_observation_service
        )

    if getattr(ctx, "risk_companion_service", None) is not None:
        ports["risk_companion"] = RiskCompanionAdapter(ctx.risk_companion_service)

    return ports


__all__ = [
    "PortfolioPort",
    "RiskMetricsPort",
    "TradePlanPort",
    "SignalObservationPort",
    "RiskCompanionPort",
    "PortfolioAdapter",
    "RiskMetricsAdapter",
    "TradePlanAdapter",
    "SignalObservationAdapter",
    "RiskCompanionAdapter",
    "create_portfolio_risk_ports",
]
