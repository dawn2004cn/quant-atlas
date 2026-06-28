from __future__ import annotations

"""Borderless execution router — multi-market ExecutionGateway facade."""

import logging
from typing import Any

from app.domain.execution.driver_protocol import ExecutionGateway, TradeRequest, TradeResponse
from app.domain.execution.execution_schema import ExecutionRouteDescriptor
from app.domain.execution.market_router import resolve_execution_route

logger = logging.getLogger(__name__)


class BorderlessExecutionRouter:
    """Routes orders to market-specific gateways by symbol inference."""

    def __init__(self, *, default_mode: str = "paper") -> None:
        self._default_mode = default_mode
        self._drivers: dict[str, ExecutionGateway] = {}

    def register_driver(self, driver_id: str, gateway: ExecutionGateway) -> None:
        self._drivers[driver_id] = gateway
        logger.debug("borderless driver registered: %s", driver_id)

    def list_drivers(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for driver_id in sorted(self._drivers.keys()):
            gateway = self._drivers[driver_id]
            row: dict[str, Any] = {"driver_id": driver_id, "registered": True}
            describe = getattr(gateway, "describe", None)
            if callable(describe):
                row.update(describe())
            rows.append(row)
        return rows

    def preview_route(
        self,
        symbol: str,
        *,
        market_hint: str | None = None,
        mode: str | None = None,
        exchange_hint: str = "",
    ) -> ExecutionRouteDescriptor:
        route = resolve_execution_route(
            symbol,
            market_hint=market_hint,
            mode=mode or self._default_mode,
            exchange_hint=exchange_hint,
        )
        if route.driver_id not in self._drivers:
            route.evidence = f"{route.evidence}; driver_missing:{route.driver_id}"
            route.confidence = min(route.confidence, 0.5)
        return route

    def gateway_for_symbol(
        self,
        symbol: str,
        *,
        market_hint: str | None = None,
        mode: str | None = None,
        exchange_hint: str = "",
    ) -> ExecutionGateway:
        route = resolve_execution_route(
            symbol,
            market_hint=market_hint,
            mode=mode or self._default_mode,
            exchange_hint=exchange_hint,
        )
        return self._pick_gateway(route)

    def _pick_gateway(self, route: ExecutionRouteDescriptor) -> ExecutionGateway:
        gateway = self._drivers.get(route.driver_id)
        if gateway is None and route.driver_id.startswith("redis_"):
            gateway = self._drivers.get(f"paper_{route.market.value.lower()}")
        if gateway is None:
            prefix = f"paper_{route.market.value.lower()}"
            gateway = self._drivers.get(prefix)
        if gateway is None:
            raise KeyError(f"execution_driver_unavailable:{route.driver_id}")
        return gateway

    async def submit_order(self, request: TradeRequest) -> TradeResponse:
        market_hint = str(request.metadata.get("market") or "")
        route = resolve_execution_route(
            request.symbol,
            market_hint=market_hint or None,
            mode=str(request.metadata.get("mode") or self._default_mode),
            exchange_hint=request.exchange,
        )
        gateway = self._pick_gateway(route)
        enriched = TradeRequest.from_dict(request.to_dict())
        enriched.symbol = route.symbol
        enriched.exchange = route.exchange
        enriched.metadata = {
            **enriched.metadata,
            "route": route.model_dump(mode="json"),
        }
        return await gateway.submit_order(enriched)

    async def cancel_order(self, order_id: str, symbol: str) -> TradeResponse:
        route = resolve_execution_route(symbol, mode=self._default_mode)
        gateway = self._pick_gateway(route)
        return await gateway.cancel_order(order_id, symbol)

    async def get_order_status(self, order_id: str, symbol: str) -> TradeResponse:
        route = resolve_execution_route(symbol, mode=self._default_mode)
        gateway = self._pick_gateway(route)
        return await gateway.get_order_status(order_id, symbol)

    async def get_positions(self, symbol: str | None = None) -> list[dict]:
        results: list[dict] = []
        for gateway in self._drivers.values():
            try:
                chunk = await gateway.get_positions(symbol)
                results.extend(chunk or [])
            except Exception as exc:
                logger.warning("borderless get_positions: %s", exc)
        return results

    async def get_balance(self, asset: str | None = None) -> dict:
        merged: dict[str, Any] = {}
        for gateway in self._drivers.values():
            try:
                bal = await gateway.get_balance(asset)
                if isinstance(bal, dict):
                    merged.update(bal)
            except Exception as exc:
                logger.warning("borderless get_balance: %s", exc)
        return merged

    async def health_check(self) -> bool:
        if not self._drivers:
            return False
        for gateway in self._drivers.values():
            try:
                if not await gateway.health_check():
                    return False
            except Exception:
                return False
        return True


__all__ = ["BorderlessExecutionRouter"]
