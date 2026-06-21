"""Order State Machine Tests."""

import pytest
import tempfile
from pathlib import Path

from app.domain.trading import (
    OrderTracker,
    OrderStateMachine,
    OrderPersistence,
    OrderRecovery,
)
from app.domain.trading.order_tracker import OrderState


class TestOrderStateMachine:
    """订单状态机测试"""

    def test_create_order(self):
        machine = OrderStateMachine("test_order_1")
        assert machine.state == OrderState.PENDING
        assert not machine.is_terminal()

    def test_valid_transition(self):
        machine = OrderStateMachine("test_order_2")

        # Pending -> Accepted
        assert machine.transition(OrderState.ACCEPTED, "Order accepted")
        assert machine.state == OrderState.ACCEPTED

        # Accepted -> PartialFilled
        assert machine.transition(OrderState.PARTIAL_FILLED, "Partial fill")
        assert machine.state == OrderState.PARTIAL_FILLED

        # PartialFilled -> Filled
        assert machine.transition(OrderState.FILLED, "Fully filled")
        assert machine.state == OrderState.FILLED
        assert machine.is_terminal()

    def test_invalid_transition(self):
        machine = OrderStateMachine("test_order_3")

        # Pending -> Filled (跳过中间状态)
        result = machine.transition(OrderState.FILLED, "Direct fill")
        assert result is False
        assert machine.state == OrderState.PENDING

    def test_cancel_from_pending(self):
        machine = OrderStateMachine("test_order_4")
        assert machine.transition(OrderState.CANCELLED, "User cancelled")
        assert machine.state == OrderState.CANCELLED
        assert machine.is_terminal()

    def test_reject_from_accepted(self):
        machine = OrderStateMachine("test_order_5")
        machine.transition(OrderState.ACCEPTED, "Accepted")
        assert machine.transition(OrderState.REJECTED, "Risk check failed")
        assert machine.state == OrderState.REJECTED

    def test_event_history(self):
        machine = OrderStateMachine("test_order_6")
        machine.transition(OrderState.ACCEPTED, "Step 1")
        machine.transition(OrderState.PARTIAL_FILLED, "Step 2")
        machine.transition(OrderState.FILLED, "Step 3")

        history = machine.get_history()
        assert len(history) == 3
        assert history[0]["from"] == "pending"
        assert history[0]["to"] == "accepted"
        assert history[2]["to"] == "filled"

    def test_serialization(self):
        machine = OrderStateMachine("test_order_7")
        machine.transition(OrderState.ACCEPTED, "Test")
        machine.transition(OrderState.FILLED, "Done")

        data = machine.to_dict()
        restored = OrderStateMachine.from_dict(data)

        assert restored.order_id == "test_order_7"
        assert restored.state == OrderState.FILLED
        assert len(restored.events) == 2


class TestOrderTracker:
    """订单追踪器测试"""

    def test_create_and_track(self):
        tracker = OrderTracker()

        machine = tracker.create_order(
            order_id="order_1",
            symbol="BTCUSDT",
            side="buy",
            amount=0.001,
            price=50000.0,
        )

        assert machine is not None
        assert machine.order_id == "order_1"
        assert "order_1" in tracker.get_pending_orders()

    def test_transition(self):
        tracker = OrderTracker()
        tracker.create_order("order_2", "ETHUSDT", "sell", 0.1, 3000.0)

        assert tracker.transition("order_2", OrderState.ACCEPTED)
        assert tracker.transition("order_2", OrderState.FILLED)

        assert "order_2" in tracker.get_terminal_orders()
        assert "order_2" not in tracker.get_pending_orders()

    def test_stats(self):
        tracker = OrderTracker()
        tracker.create_order("o1", "BTC", "buy", 1, 100)
        tracker.create_order("o2", "ETH", "sell", 1, 100)
        tracker.transition("o1", OrderState.ACCEPTED)
        tracker.transition("o1", OrderState.FILLED)

        stats = tracker.get_stats()
        assert stats["total"] == 2
        assert stats["pending"] == 1
        assert stats["terminal"] == 1

    def test_export_import(self):
        tracker = OrderTracker()
        tracker.create_order("o1", "BTC", "buy", 1, 100)
        tracker.transition("o1", OrderState.ACCEPTED)

        exported = tracker.export_state()
        assert "o1" in exported

        tracker2 = OrderTracker()
        count = tracker2.import_state(exported)
        assert count == 1
        assert tracker2.get_order("o1").state == OrderState.ACCEPTED


class TestOrderPersistence:
    """订单持久化测试"""

    def test_file_backend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = OrderPersistence(backend="file", path=tmpdir)

            state = {
                "order_1": {
                    "order_id": "order_1",
                    "state": "accepted",
                    "created_at": 1234567890.0,
                    "updated_at": 1234567890.0,
                    "events": [],
                    "is_terminal": False,
                }
            }

            assert persistence.save_state(state)

            loaded = persistence.load_state()
            assert "order_1" in loaded
            assert loaded["order_1"]["state"] == "accepted"

    def test_event_logging(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = OrderPersistence(backend="file", path=tmpdir)

            event = {
                "order_id": "order_1",
                "from": "pending",
                "to": "accepted",
                "timestamp": 1234567890.0,
            }

            assert persistence.save_event(event)

            events = persistence.load_events("order_1")
            assert len(events) == 1
            assert events[0]["order_id"] == "order_1"


class TestOrderRecovery:
    """订单恢复测试"""

    def test_recovery_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = OrderTracker()
            persistence = OrderPersistence(backend="file", path=tmpdir)

            # 创建并保存状态
            tracker.create_order("order_1", "BTC", "buy", 1, 100)
            tracker.transition("order_1", OrderState.ACCEPTED)
            persistence.save_state(tracker.export_state())

            # 模拟重启 - 创建新的 tracker
            new_tracker = OrderTracker()
            recovery = OrderRecovery(new_tracker, persistence)

            result = recovery.recover()

            assert result.total_orders == 1
            assert result.recovered_orders == 1
            assert new_tracker.get_order("order_1").state == OrderState.ACCEPTED

    def test_detect_orphans(self):
        tracker = OrderTracker()
        persistence = OrderPersistence(backend="file", path=tempfile.mkdtemp())

        tracker.create_order("order_1", "BTC", "buy", 1, 100)
        # 模拟过期 - 直接修改时间
        machine = tracker.get_order("order_1")
        machine._updated_at = 0  # 很久以前

        recovery = OrderRecovery(tracker, persistence)
        orphans = recovery.detect_orphans()

        assert "order_1" in orphans

    def test_cleanup_orphans(self):
        tracker = OrderTracker()
        persistence = OrderPersistence(backend="file", path=tempfile.mkdtemp())

        tracker.create_order("order_1", "BTC", "buy", 1, 100)
        recovery = OrderRecovery(tracker, persistence)

        count = recovery.cleanup_orphans(["order_1"])
        assert count == 1
        assert tracker.get_order("order_1").state == OrderState.EXPIRED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])