from __future__ import annotations

"""Execution driver protocol and request/response types (domain layer)."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class TradeRequest:
    request_id: str = field(default_factory=lambda: f"req_{int(time.time() * 1000)}")
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    amount: float = 0.0
    price: float = 0.0
    stop_price: float = 0.0
    time_in_force: str = "GTC"
    exchange: str = "binance"
    client_order_id: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "amount": self.amount,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
            "exchange": self.exchange,
            "client_order_id": self.client_order_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TradeRequest:
        return cls(
            request_id=data.get("request_id", ""),
            symbol=data.get("symbol", ""),
            side=OrderSide(data.get("side", "buy")),
            order_type=OrderType(data.get("order_type", "market")),
            amount=float(data.get("amount", 0)),
            price=float(data.get("price", 0)),
            stop_price=float(data.get("stop_price", 0)),
            time_in_force=data.get("time_in_force", "GTC"),
            exchange=data.get("exchange", "binance"),
            client_order_id=data.get("client_order_id", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TradeResponse:
    request_id: str = ""
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    filled_amount: float = 0.0
    filled_price: float = 0.0
    remaining_amount: float = 0.0
    commission: float = 0.0
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    raw_response: dict = field(default_factory=dict)

    def is_success(self) -> bool:
        return self.status in (OrderStatus.SUBMITTED, OrderStatus.FILLED, OrderStatus.PARTIAL_FILLED)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "order_id": self.order_id,
            "status": self.status.value,
            "filled_amount": self.filled_amount,
            "filled_price": self.filled_price,
            "remaining_amount": self.remaining_amount,
            "commission": self.commission,
            "message": self.message,
            "timestamp": self.timestamp,
            "raw_response": self.raw_response,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TradeResponse:
        status_str = data.get("status", "pending")
        if isinstance(status_str, str):
            try:
                status = OrderStatus(status_str)
            except ValueError:
                status = OrderStatus.PENDING
        else:
            status = OrderStatus.PENDING

        return cls(
            request_id=data.get("request_id", ""),
            order_id=data.get("order_id", ""),
            status=status,
            filled_amount=float(data.get("filled_amount", 0)),
            filled_price=float(data.get("filled_price", 0)),
            remaining_amount=float(data.get("remaining_amount", 0)),
            commission=float(data.get("commission", 0)),
            message=data.get("message", ""),
            timestamp=float(data.get("timestamp", time.time())),
            raw_response=data.get("raw_response", {}),
        )


@runtime_checkable
class ExecutionGateway(Protocol):
    async def submit_order(self, request: TradeRequest) -> TradeResponse:
        ...

    async def cancel_order(self, order_id: str, symbol: str) -> TradeResponse:
        ...

    async def get_order_status(self, order_id: str, symbol: str) -> TradeResponse:
        ...

    async def get_positions(self, symbol: str | None = None) -> list[dict]:
        ...

    async def get_balance(self, asset: str | None = None) -> dict:
        ...

    async def health_check(self) -> bool:
        ...
