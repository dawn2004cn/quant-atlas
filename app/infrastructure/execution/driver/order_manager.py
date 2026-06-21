from __future__ import annotations
"""Order Manager - 订单生命周期管理。

负责:
1. 订单状态跟踪与更新
2. 订单重试逻辑
3. 订单历史记录
"""


import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class OrderState(str, Enum):
    """订单状态机"""
    CREATED = "created"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderRecord:
    """订单记录"""
    order_id: str
    request_id: str
    symbol: str
    side: str
    amount: float
    filled_amount: float = 0
    price: float = 0
    filled_price: float = 0
    state: OrderState = OrderState.CREATED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    filled_at: float | None = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    retry_count: int = 0


class OrderManager:
    """订单管理器 - 线程安全"""

    def __init__(self, max_retries: int = 3, validator=None):
        self._orders: dict[str, OrderRecord] = {}
        self._lock = threading.RLock()
        self._max_retries = max_retries
        self._validator = validator

    def create(self, request_id: str, order_id: str, symbol: str, side: str, amount: float, price: float = 0) -> OrderRecord:
        """创建订单记录。如果配置了 PreTradeValidator 且校验失败，订单状态设为 REJECTED。"""
        with self._lock:
            record = OrderRecord(
                order_id=order_id,
                request_id=request_id,
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                state=OrderState.CREATED,
            )

            if self._validator is not None:
                from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO

                signal = TradeSignalDTO(
                    symbol=symbol,
                    direction=SignalDirection.BUY if side.upper() == "BUY" else SignalDirection.SELL,
                    price=float(price or 0),
                    quantity=int(amount or 0),
                    strategy_id="order_manager",
                )
                result = self._validator.validate(signal)
                if not result:
                    record.state = OrderState.REJECTED
                    record.error = "; ".join(result.reasons)
                    record.updated_at = time.time()

            self._orders[order_id] = record
            return record

    def update_state(self, order_id: str, state: OrderState, filled_amount: float = 0, filled_price: float = 0, error: str | None = None) -> bool:
        """更新订单状态。部分成交时按成交量加权计算均价 (VWAP)。"""
        with self._lock:
            record = self._orders.get(order_id)
            if not record:
                return False

            record.state = state
            record.updated_at = time.time()

            if filled_amount > 0 and filled_price > 0:
                # VWAP update for partial fills.
                total_value = record.filled_amount * record.filled_price + filled_amount * filled_price
                record.filled_amount += filled_amount
                record.filled_price = total_value / record.filled_amount if record.filled_amount > 0 else 0
            elif filled_amount > 0:
                record.filled_amount = filled_amount
            elif filled_price > 0:
                record.filled_price = filled_price

            if error:
                record.error = error

            if state == OrderState.FILLED:
                record.filled_at = time.time()

            return True

    def get(self, order_id: str) -> OrderRecord | None:
        """获取订单"""
        with self._lock:
            return self._orders.get(order_id)

    def get_by_request_id(self, request_id: str) -> OrderRecord | None:
        """通过 request_id 查找订单"""
        with self._lock:
            for record in self._orders.values():
                if record.request_id == request_id:
                    return record
            return None

    def can_retry(self, order_id: str) -> bool:
        """检查是否可重试"""
        with self._lock:
            record = self._orders.get(order_id)
            if not record:
                return False
            return record.retry_count < self._max_retries

    def increment_retry(self, order_id: str) -> int:
        """增加重试次数"""
        with self._lock:
            record = self._orders.get(order_id)
            if record:
                record.retry_count += 1
                return record.retry_count
            return 0

    def get_pending_orders(self) -> list[OrderRecord]:
        """获取待处理订单"""
        with self._lock:
            return [
                r for r in self._orders.values()
                if r.state in (OrderState.SUBMITTED, OrderState.PARTIAL_FILLED)
            ]

    def get_orders_by_symbol(self, symbol: str) -> list[OrderRecord]:
        """获取指定 symbol 的订单"""
        with self._lock:
            return [r for r in self._orders.values() if r.symbol == symbol]

    def get_history(self, limit: int = 100) -> list[dict]:
        """获取订单历史"""
        with self._lock:
            sorted_orders = sorted(
                self._orders.values(),
                key=lambda x: x.updated_at,
                reverse=True
            )
            return [
                {
                    "order_id": o.order_id,
                    "symbol": o.symbol,
                    "side": o.side,
                    "amount": o.amount,
                    "filled_amount": o.filled_amount,
                    "state": o.state.value,
                    "created_at": datetime.fromtimestamp(o.created_at).isoformat(),
                    "updated_at": datetime.fromtimestamp(o.updated_at).isoformat(),
                }
                for o in sorted_orders[:limit]
            ]

    def clear_expired(self, max_age_seconds: int = 3600) -> int:
        """清理过期订单"""
        with self._lock:
            now = time.time()
            expired = [
                oid for oid, o in self._orders.items()
                if now - o.updated_at > max_age_seconds
                and o.state in (OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED)
            ]
            for oid in expired:
                del self._orders[oid]
            return len(expired)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        with self._lock:
            total = len(self._orders)
            filled = sum(1 for o in self._orders.values() if o.state == OrderState.FILLED)
            pending = sum(1 for o in self._orders.values() if o.state in (OrderState.SUBMITTED, OrderState.PARTIAL_FILLED))
            rejected = sum(1 for o in self._orders.values() if o.state == OrderState.REJECTED)

            return {
                "total_orders": total,
                "filled": filled,
                "pending": pending,
                "rejected": rejected,
                "fill_rate": round(filled / max(total, 1), 2),
            }