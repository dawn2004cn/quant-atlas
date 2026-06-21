from __future__ import annotations
"""Order Recovery - 订单故障恢复机制。

在进程重启或网络中断后:
- 检测未完成的订单
- 同步柜台状态
- 自动恢复或告警
"""


import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from app.core.logger import get_logger
from .order_tracker import OrderStateMachine, OrderState, OrderTracker
from .order_persistence import OrderPersistence

logger = get_logger(__name__)


@dataclass
class RecoveryResult:
    """恢复结果"""
    total_orders: int = 0
    recovered_orders: int = 0
    failed_orders: int = 0
    orphaned_orders: int = 0
    details: list[dict] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class OrderRecovery:
    """订单恢复管理器

    处理:
    - 进程重启后的状态恢复
    - 孤儿订单检测 (本地有但柜台无)
    - 状态不一致修复
    """

    def __init__(
        self,
        tracker: OrderTracker,
        persistence: OrderPersistence,
        exchange_sync: Callable[[str], dict] | None = None,
    ):
        self._tracker = tracker
        self._persistence = persistence
        self._exchange_sync = exchange_sync  # 同步柜台状态的回调

    def recover(self) -> RecoveryResult:
        """执行恢复流程

        Returns:
            恢复结果
        """
        result = RecoveryResult()

        logger.info("Starting order recovery...")

        # 1. 加载持久化状态
        saved_state = self._persistence.load_state()
        result.total_orders = len(saved_state)

        if not saved_state:
            logger.info("No saved state found")
            return result

        # 2. 恢复本地状态机
        recovered = self._tracker.import_state(saved_state)
        result.recovered_orders = recovered

        # 3. 检查待处理订单
        pending = self._tracker.get_pending_orders()
        if pending:
            logger.warning(f"Found {len(pending)} pending orders after recovery")

            for order_id in pending:
                try:
                    self._recover_single_order(order_id, result)
                except Exception as e:
                    logger.error(f"Failed to recover order {order_id}: {e}")
                    result.failed_orders += 1
                    result.details.append({
                        "order_id": order_id,
                        "status": "failed",
                        "error": str(e),
                    })

        # 4. 保存恢复后的状态
        self._persistence.save_state(self._tracker.export_state())

        logger.info(
            f"Recovery complete: {result.recovered_orders} recovered, "
            f"{result.failed_orders} failed, {result.orphaned_orders} orphaned"
        )

        return result

    def _recover_single_order(
        self,
        order_id: str,
        result: RecoveryResult,
    ) -> None:
        """恢复单个订单"""
        machine = self._tracker.get_order(order_id)
        if not machine:
            return

        # 如果有交易所同步回调，尝试同步状态
        if self._exchange_sync:
            try:
                exchange_state = self._exchange_sync(order_id)
                if exchange_state:
                    self._sync_order_state(machine, exchange_state, result)
                else:
                    # 柜台无此订单 - 标记为孤儿
                    result.orphaned_orders += 1
                    result.details.append({
                        "order_id": order_id,
                        "status": "orphaned",
                        "local_state": machine.state.value,
                    })
                    logger.warning(f"Orphaned order detected: {order_id}")
            except Exception as e:
                logger.error(f"Failed to sync order {order_id}: {e}")
                result.failed_orders += 1
        else:
            # 无同步能力，保持原状态
            result.details.append({
                "order_id": order_id,
                "status": "pending_sync",
                "local_state": machine.state.value,
            })

    def _sync_order_state(
        self,
        machine: OrderStateMachine,
        exchange_state: dict,
        result: RecoveryResult,
    ) -> None:
        """同步订单状态"""
        exchange_status = exchange_state.get("status", "").lower()

        # 映射交易所状态到本地状态
        state_map = {
            "filled": OrderState.FILLED,
            "partially_filled": OrderState.PARTIAL_FILLED,
            "cancelled": OrderState.CANCELLED,
            "rejected": OrderState.REJECTED,
            "expired": OrderState.EXPIRED,
        }

        target_state = state_map.get(exchange_status)
        if target_state and machine.can_transition_to(target_state):
            machine.transition(
                target_state,
                reason=f"Recovered from exchange state: {exchange_status}",
            )
            result.details.append({
                "order_id": machine.order_id,
                "status": "synced",
                "from": machine.state.value,
                "to": target_state.value,
            })
        elif target_state:
            result.details.append({
                "order_id": machine.order_id,
                "status": "state_conflict",
                "local": machine.state.value,
                "exchange": exchange_status,
            })

    def detect_orphans(self) -> list[str]:
        """检测孤儿订单 (本地有但可能已过期)"""
        orphans = []
        now = time.time()

        for order_id in self._tracker.get_pending_orders():
            machine = self._tracker.get_order(order_id)
            if machine:
                # 超过 24 小时未更新的待处理订单视为孤儿
                if now - machine._updated_at > 86400:
                    orphans.append(order_id)

        return orphans

    def cleanup_orphans(self, order_ids: list[str]) -> int:
        """清理孤儿订单

        Returns:
            清理数量
        """
        count = 0
        for order_id in order_ids:
            machine = self._tracker.get_order(order_id)
            if machine and not machine.is_terminal():
                machine.transition(
                    OrderState.EXPIRED,
                    reason="Auto-expired as orphan",
                )
                count += 1

        if count > 0:
            self._persistence.save_state(self._tracker.export_state())

        return count


class AutoRecoveryScheduler:
    """自动恢复调度器

    定期执行订单恢复检查。
    """

    def __init__(
        self,
        recovery: OrderRecovery,
        interval_seconds: int = 3600,  # 每小时检查一次
        on_recovery: Callable[[RecoveryResult], None] | None = None,
    ):
        self._recovery = recovery
        self._interval = interval_seconds
        self._on_recovery = on_recovery
        self._running = False

    def start(self) -> None:
        """启动调度器"""
        self._running = True
        logger.info(f"Auto recovery scheduler started (interval={self._interval}s)")

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        logger.info("Auto recovery scheduler stopped")

    def run_once(self) -> RecoveryResult:
        """执行一次恢复检查"""
        result = self._recovery.recover()

        if self._on_recovery:
            self._on_recovery(result)

        return result