from __future__ import annotations

"""Order State Machine - 订单状态机核心实现。

定义订单状态及转换规则:
- Pending -> Accepted -> PartialFilled -> Filled
- 任意状态 -> Cancelled/Rejected/Expired
"""


import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class OrderState(str, Enum):
    """订单状态"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


# 合法状态转换
VALID_TRANSITIONS = {
    OrderState.PENDING: [OrderState.ACCEPTED, OrderState.REJECTED, OrderState.CANCELLED, OrderState.FAILED, OrderState.EXPIRED],
    OrderState.ACCEPTED: [OrderState.PARTIAL_FILLED, OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED],
    OrderState.PARTIAL_FILLED: [OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED],
    OrderState.FILLED: [],  # 终态
    OrderState.CANCELLED: [],  # 终态
    OrderState.REJECTED: [],  # 终态
    OrderState.EXPIRED: [],  # 终态
    OrderState.FAILED: [],  # 终态
}


@dataclass
class OrderEvent:
    """订单事件"""
    order_id: str
    from_state: OrderState
    to_state: OrderState
    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderRecord:
    """订单记录"""
    order_id: str
    symbol: str
    side: str  # buy/sell
    amount: float
    price: float
    filled_amount: float = 0.0
    filled_price: float = 0.0
    state: OrderState = OrderState.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    filled_at: float | None = None
    events: list[OrderEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class OrderStateMachine:
    """订单状态机

    严格管理订单状态转换，确保:
    - 只允许合法的状态转换
    - 记录所有状态变更事件
    - 支持状态恢复
    """

    def __init__(self, order_id: str):
        self.order_id = order_id
        self._state = OrderState.PENDING
        self._events: list[OrderEvent] = []
        self._created_at = time.time()
        self._updated_at = time.time()

    @property
    def state(self) -> OrderState:
        return self._state

    @property
    def events(self) -> list[OrderEvent]:
        return self._events.copy()

    def transition(self, to_state: OrderState, reason: str = "", metadata: dict | None = None) -> bool:
        """执行状态转换

        Args:
            to_state: 目标状态
            reason: 转换原因
            metadata: 附加元数据

        Returns:
            是否转换成功
        """
        # 验证转换合法性
        if not self._is_valid_transition(to_state):
            logger.error(
                f"Invalid transition: {self._state} -> {to_state} for order {self.order_id}"
            )
            return False

        # 创建事件
        event = OrderEvent(
            order_id=self.order_id,
            from_state=self._state,
            to_state=to_state,
            reason=reason,
            metadata=metadata or {},
        )

        # 执行转换
        self._state = to_state
        self._updated_at = time.time()
        self._events.append(event)

        logger.info(f"Order {self.order_id}: {event.from_state.value} -> {to_state.value} ({reason})")
        return True

    def _is_valid_transition(self, to_state: OrderState) -> bool:
        """验证状态转换是否合法"""
        allowed = VALID_TRANSITIONS.get(self._state, [])
        return to_state in allowed

    def can_transition_to(self, state: OrderState) -> bool:
        """检查是否可以转换到指定状态"""
        return self._is_valid_transition(state)

    def get_history(self) -> list[dict]:
        """获取状态变更历史"""
        return [
            {
                "from": e.from_state.value,
                "to": e.to_state.value,
                "reason": e.reason,
                "timestamp": e.timestamp,
            }
            for e in self._events
        ]

    def is_terminal(self) -> bool:
        """是否处于终态"""
        return self._state in (
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
            OrderState.EXPIRED,
            OrderState.FAILED,
        )

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "order_id": self.order_id,
            "state": self._state.value,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "events": self.get_history(),
            "is_terminal": self.is_terminal(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> OrderStateMachine:
        """从字典恢复状态机"""
        machine = cls(data["order_id"])
        machine._state = OrderState(data.get("state", OrderState.PENDING))
        machine._created_at = data.get("created_at", time.time())
        machine._updated_at = data.get("updated_at", time.time())

        # 恢复事件历史
        for e in data.get("events", []):
            machine._events.append(OrderEvent(
                order_id=data["order_id"],
                from_state=OrderState(e["from"]),
                to_state=OrderState(e["to"]),
                reason=e.get("reason", ""),
                timestamp=e.get("timestamp", time.time()),
            ))

        return machine


class OrderTracker:
    """订单追踪器 - 管理所有订单的状态机

    提供:
    - 订单创建与追踪
    - 状态转换
    - 查询与统计
    """

    def __init__(self):
        self._orders: dict[str, OrderStateMachine] = {}
        self._pending_orders: set[str] = set()
        self._terminal_orders: set[str] = set()

    def create_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        metadata: dict | None = None,
    ) -> OrderStateMachine:
        """创建订单

        Args:
            order_id: 订单 ID
            symbol: 交易对
            side: 买卖方向
            amount: 数量
            price: 价格
            metadata: 元数据

        Returns:
            订单状态机
        """
        if order_id in self._orders:
            raise ValueError(f"Order {order_id} already exists")

        machine = OrderStateMachine(order_id)
        self._orders[order_id] = machine
        self._pending_orders.add(order_id)

        logger.info(f"Order created: {order_id} {symbol} {side} {amount}@{price}")
        return machine

    def transition(self, order_id: str, to_state: OrderState, reason: str = "") -> bool:
        """转换订单状态

        Args:
            order_id: 订单 ID
            to_state: 目标状态
            reason: 转换原因

        Returns:
            是否转换成功
        """
        machine = self._orders.get(order_id)
        if not machine:
            logger.error(f"Order not found: {order_id}")
            return False

        result = machine.transition(to_state, reason)

        if result and machine.is_terminal():
            self._pending_orders.discard(order_id)
            self._terminal_orders.add(order_id)

        return result

    def get_order(self, order_id: str) -> OrderStateMachine | None:
        """获取订单状态机"""
        return self._orders.get(order_id)

    def get_pending_orders(self) -> list[str]:
        """获取待处理订单 ID"""
        return list(self._pending_orders)

    def get_terminal_orders(self) -> list[str]:
        """获取终态订单 ID"""
        return list(self._terminal_orders)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total": len(self._orders),
            "pending": len(self._pending_orders),
            "terminal": len(self._terminal_orders),
        }

    def export_state(self) -> dict:
        """导出所有订单状态 (用于持久化)"""
        return {
            oid: machine.to_dict()
            for oid, machine in self._orders.items()
        }

    def import_state(self, state: dict) -> int:
        """导入订单状态 (用于恢复)

        Returns:
            恢复的订单数量
        """
        count = 0
        for order_id, data in state.items():
            try:
                machine = OrderStateMachine.from_dict(data)
                self._orders[order_id] = machine

                if machine.is_terminal():
                    self._terminal_orders.add(order_id)
                else:
                    self._pending_orders.add(order_id)

                count += 1
            except Exception as e:
                logger.error(f"Failed to restore order {order_id}: {e}")

        logger.info(f"Restored {count} orders from state")
        return count
