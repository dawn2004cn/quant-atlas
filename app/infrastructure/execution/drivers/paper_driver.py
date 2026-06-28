from __future__ import annotations
"""Paper execution driver — immediate simulated fills for all markets."""

import uuid

from app.domain.execution.driver_protocol import (
    ExecutionGateway,
    OrderSide,
    OrderStatus,
    OrderType,
    TradeRequest,
    TradeResponse,
)


class PaperExecutionDriver:
    """Synchronous-friendly paper gateway for borderless routing tests and dev."""

    def __init__(self, *, market: str = "CN", exchange: str = "paper") -> None:
        self._market = market.upper()
        self._exchange = exchange
        self._orders: dict[str, TradeResponse] = {}

    def describe(self) -> dict[str, str]:
        return {
            "market": self._market,
            "exchange": self._exchange,
            "backend": "paper",
        }

    async def submit_order(self, request: TradeRequest) -> TradeResponse:
        fill_price = float(request.price or 0) or float(request.metadata.get("reference_price") or 100.0)
        amount = float(request.amount or 0)
        if amount <= 0 and request.metadata.get("quantity"):
            amount = float(request.metadata["quantity"])
        order_id = f"paper_{self._market}_{uuid.uuid4().hex[:12]}"
        status = OrderStatus.FILLED if request.order_type == OrderType.MARKET else OrderStatus.SUBMITTED
        filled = amount if status == OrderStatus.FILLED else 0.0
        response = TradeResponse(
            request_id=request.request_id,
            order_id=order_id,
            status=status,
            filled_amount=filled,
            filled_price=fill_price,
            remaining_amount=max(0.0, amount - filled),
            message=f"paper fill via {self._exchange}",
            raw_response={
                "driver": "paper",
                "market": self._market,
                "exchange": self._exchange,
                "simulated": True,
            },
        )
        self._orders[order_id] = response
        return response

    async def cancel_order(self, order_id: str, symbol: str) -> TradeResponse:
        del symbol
        existing = self._orders.get(order_id)
        if existing is None:
            return TradeResponse(
                request_id=f"cancel_{order_id}",
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message="order_not_found",
            )
        cancelled = TradeResponse(
            request_id=f"cancel_{order_id}",
            order_id=order_id,
            status=OrderStatus.CANCELLED,
            message="paper order cancelled",
        )
        self._orders[order_id] = cancelled
        return cancelled

    async def get_order_status(self, order_id: str, symbol: str) -> TradeResponse:
        del symbol
        if order_id in self._orders:
            return self._orders[order_id]
        return TradeResponse(
            request_id=f"query_{order_id}",
            order_id=order_id,
            status=OrderStatus.PENDING,
            message="unknown order",
        )

    async def get_positions(self, symbol: str | None = None) -> list[dict]:
        positions = [
            {"symbol": symbol, "market": self._market, "amount": 0.0, "exchange": self._exchange}
        ] if symbol else []
        return positions

    async def get_balance(self, asset: str | None = None) -> dict:
        base = {"free": 1_000_000.0, "locked": 0.0, "market": self._market}
        if asset:
            return {asset: base}
        return {"USDT": base, "CNY": base}

    async def health_check(self) -> bool:
        return True


def build_trade_request_from_borderless(
    *,
    route_market: str,
    route_exchange: str,
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    quantity: float,
    price: float,
    provenance_id: str,
    client_order_id: str,
    metadata: dict,
) -> TradeRequest:
    qty = quantity or amount
    try:
        side_enum = OrderSide(side.lower())
    except ValueError:
        side_enum = OrderSide.BUY
    try:
        type_enum = OrderType(order_type.lower())
    except ValueError:
        type_enum = OrderType.MARKET
    meta = dict(metadata or {})
    meta.setdefault("market", route_market)
    if quantity:
        meta["quantity"] = quantity
    return TradeRequest(
        symbol=symbol,
        side=side_enum,
        order_type=type_enum,
        amount=qty,
        price=price,
        exchange=route_exchange,
        client_order_id=client_order_id,
        metadata={
            **meta,
            "provenance_id": provenance_id,
            "borderless": True,
        },
    )


# Protocol conformance for type checkers
def _assert_gateway(driver: PaperExecutionDriver) -> ExecutionGateway:
    return driver  # type: ignore[return-value]


__all__ = ["PaperExecutionDriver", "build_trade_request_from_borderless"]
