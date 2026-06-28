from __future__ import annotations
"""Trading Session Aggregate Root.

Aggregate root for trading session with orders and executions.
"""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.domain.base import AggregateRoot


import logging
logger = logging.getLogger(__name__)
class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TradingSessionError(Exception):
    """Trading session error."""
    pass


class InvalidOrderError(TradingSessionError):
    """Invalid order error."""
    pass


class OrderNotFoundError(TradingSessionError):
    """Order not found."""
    pass


class InvalidTransitionError(TradingSessionError):
    """Invalid state transition."""
    pass


@dataclass
class OrderEntity:
    """Order entity."""
    stock_code: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float | None = None
    stop_price: float | None = None
    filled_quantity: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: datetime | None = None
    filled_at: datetime | None = None

    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    @property
    def is_cancelled(self) -> bool:
        return self.status == OrderStatus.CANCELLED

    @property
    def is_active(self) -> bool:
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        )


@dataclass
class ExecutionEntity:
    """Execution entity."""
    order_id: str
    quantity: float
    price: float
    executed_at: datetime = field(default_factory=datetime.now)


_VALID_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.SUBMITTED, OrderStatus.CANCELLED],
    OrderStatus.SUBMITTED: [OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED],
    OrderStatus.PARTIALLY_FILLED: [OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED],
}


@dataclass
class TradingSessionAggregate(AggregateRoot):
    """Trading session aggregate root.

    Encapsulates:
    - Orders
    - Executions
    - Invariants: orders valid before execution
    """

    _orders: list[OrderEntity] = field(default_factory=list)
    _executions: list[ExecutionEntity] = field(default_factory=list)

    @staticmethod
    def create() -> TradingSessionAggregate:
        """Create a new trading session."""
        return TradingSessionAggregate()

    @property
    def order_count(self) -> int:
        return len(self._orders)

    @property
    def active_order_count(self) -> int:
        return sum(1 for o in self._orders if o.is_active)

    @property
    def execution_count(self) -> int:
        return len(self._executions)

    def create_order(
        self,
        stock_code: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None
    ) -> OrderEntity:
        """Create a new order."""
        if quantity <= 0:
            raise InvalidOrderError(f"Invalid quantity: {quantity}")

        if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and price is None:
            raise InvalidOrderError("Limit order requires price")

        if order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and stop_price is None:
            raise InvalidOrderError("Stop order requires stop_price")

        order = OrderEntity(
            stock_code=stock_code,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )

        self._orders.append(order)
        self.touch()

        return order

    def submit_order(self, order_id: str) -> None:
        """Submit an order."""
        order = self._get_order(order_id)
        self._transition_order(order, OrderStatus.SUBMITTED)
        order.submitted_at = datetime.now()
        self.touch()

    def fill_order(
        self,
        order_id: str,
        quantity: float,
        price: float
    ) -> ExecutionEntity:
        """Fill an order (fully or partially)."""
        order = self._get_order(order_id)

        if not order.is_active:
            raise InvalidTransitionError(f"Order {order_id} is not active")

        fill_qty = min(quantity, order.remaining_quantity)

        order.filled_quantity += fill_qty

        if order.filled_quantity >= order.quantity:
            self._transition_order(order, OrderStatus.FILLED)
            order.filled_at = datetime.now()
        else:
            self._transition_order(order, OrderStatus.PARTIALLY_FILLED)

        execution = ExecutionEntity(
            order_id=order_id,
            quantity=fill_qty,
            price=price,
        )

        self._executions.append(execution)
        self.touch()

        return execution

    def cancel_order(self, order_id: str) -> None:
        """Cancel an order."""
        order = self._get_order(order_id)
        self._transition_order(order, OrderStatus.CANCELLED)
        self.touch()

    def reject_order(self, order_id: str, reason: str) -> None:
        """Reject an order."""
        order = self._get_order(order_id)
        self._transition_order(order, OrderStatus.REJECTED)
        self.touch()

    def _get_order(self, order_id: str) -> OrderEntity:
        """Get order by index."""
        try:
            idx = int(order_id) - 1
            if 0 <= idx < len(self._orders):
                return self._orders[idx]
        except (ValueError, IndexError) as e:
            logger.warning("trading_session_aggregate.py._get_order: %s", e)

        for order in self._orders:
            if order.stock_code == order_id:
                return order

        raise OrderNotFoundError(f"Order not found: {order_id}")

    def _transition_order(self, order: OrderEntity, new_status: OrderStatus) -> None:
        """Transition order to new status."""
        valid = _VALID_TRANSITIONS.get(order.status, [])

        if new_status not in valid:
            raise InvalidTransitionError(
                f"Cannot transition from {order.status} to {new_status}"
            )

        order.status = new_status

    def get_order(self, order_id: str) -> OrderEntity:
        """Get order by ID."""
        return self._get_order(order_id)

    def get_orders(
        self,
        status: OrderStatus | None = None,
        stock_code: str | None = None
    ) -> list[OrderEntity]:
        """Get orders with optional filtering."""
        result = self._orders

        if status:
            result = [o for o in result if o.status == status]

        if stock_code:
            result = [o for o in result if o.stock_code == stock_code]

        return sorted(result, key=lambda o: o.created_at, reverse=True)

    def get_active_orders(self) -> list[OrderEntity]:
        """Get all active orders."""
        return [o for o in self._orders if o.is_active]

    def get_executions(
        self,
        stock_code: str | None = None
    ) -> list[ExecutionEntity]:
        """Get executions."""
        result = self._executions

        if stock_code:
            result = [e for e in result if e.order_id == stock_code]

        return sorted(result, key=lambda e: e.executed_at, reverse=True)

    def get_total_filled_value(self) -> float:
        """Get total filled value."""
        return sum(e.quantity * e.price for e in self._executions)

    def clear_filled_orders(self) -> int:
        """Clear filled/cancelled orders."""
        before = len(self._orders)
        self._orders = [o for o in self._orders if o.is_active]
        return before - len(self._orders)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "order_count": self.order_count,
            "active_order_count": self.active_order_count,
            "execution_count": self.execution_count,
            "total_filled_value": self.get_total_filled_value(),
            "orders": [
                {
                    "stock_code": o.stock_code,
                    "side": o.side.value,
                    "quantity": o.quantity,
                    "filled": o.filled_quantity,
                    "status": o.status.value,
                }
                for o in self._orders
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TradingSessionFactory:
    """Factory for creating trading sessions."""

    @staticmethod
    def create_market_order(
        stock_code: str,
        side: OrderSide,
        quantity: float
    ) -> tuple[str, OrderSide, OrderType, float]:
        """Create market order tuple."""
        return (stock_code, side, OrderType.MARKET, quantity)

    @staticmethod
    def create_limit_order(
        stock_code: str,
        side: OrderSide,
        quantity: float,
        price: float
    ) -> tuple[str, OrderSide, OrderType, float, float]:
        """Create limit order tuple."""
        return (stock_code, side, OrderType.LIMIT, quantity, price)

    @staticmethod
    def create_stop_order(
        stock_code: str,
        side: OrderSide,
        quantity: float,
        stop_price: float
    ) -> tuple[str, OrderSide, OrderType, float, float]:
        """Create stop order tuple."""
        return (stock_code, side, OrderType.STOP, quantity, stop_price)


__all__ = [
    "OrderStatus",
    "OrderSide",
    "OrderType",
    "OrderEntity",
    "ExecutionEntity",
    "TradingSessionError",
    "InvalidOrderError",
    "OrderNotFoundError",
    "InvalidTransitionError",
    "TradingSessionAggregate",
    "TradingSessionFactory",
]
