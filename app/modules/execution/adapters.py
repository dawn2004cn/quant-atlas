"""Execution Service Adapters.

Adapters implement the Execution Ports using the current concrete services.
Each adapter wraps an existing service and adapts its interface to match
the corresponding port contract.

This enables:
1. Clean separation between route handlers and service implementations
2. Easy substitution of service implementations in tests
3. Clear migration path to independent microservice
"""

from __future__ import annotations

from typing import Any

from app.modules.execution.ports import (
    SelfHealingPort,
    SimulationPort,
    TradeExecutionPort,
)


class TradeExecutionAdapter(TradeExecutionPort):
    """Adapts TradeExecutionPipelineService to TradeExecutionPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def execute_trade(self, order: dict[str, Any]) -> dict[str, Any]:
        return self._service.execute_trade(order)

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        return self._service.get_order_status(order_id)

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        return self._service.cancel_order(order_id)

    def get_execution_history(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        return self._service.get_execution_history(user_id, limit=limit)


class SimulationAdapter(SimulationPort):
    """Adapts SimulationGatewayService to SimulationPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def run_simulation(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._service.run_simulation(params)


class SelfHealingAdapter(SelfHealingPort):
    """Adapts SelfHealingExecutionService to SelfHealingPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def heal_execution(self, order_id: str) -> dict[str, Any]:
        return self._service.heal_execution(order_id)

    def get_healing_status(self, order_id: str) -> dict[str, Any]:
        return self._service.get_healing_status(order_id)


def create_execution_ports(ctx: Any) -> dict[str, Any]:
    """Create all execution ports from an ApiV1Context.

    This factory function maps context services to port adapters.
    Returns a dict of port_name -> port_instance.
    """
    ports = {}

    if getattr(ctx, "trade_execution_pipeline_service", None) is not None:
        ports["trade_execution"] = TradeExecutionAdapter(
            ctx.trade_execution_pipeline_service
        )

    if getattr(ctx, "simulation_gateway_service", None) is not None:
        ports["simulation"] = SimulationAdapter(ctx.simulation_gateway_service)

    if getattr(ctx, "self_healing_execution_service", None) is not None:
        ports["self_healing"] = SelfHealingAdapter(
            ctx.self_healing_execution_service
        )

    return ports


__all__ = [
    "TradeExecutionPort",
    "SimulationPort",
    "SelfHealingPort",
    "TradeExecutionAdapter",
    "SimulationAdapter",
    "SelfHealingAdapter",
    "create_execution_ports",
]
