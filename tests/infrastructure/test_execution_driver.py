"""Execution Driver 集成测试."""

import asyncio
import pytest

from app.infrastructure.execution.driver import (
    RedisStreamExecutor,
    TradeRequest,
    OrderSide,
    OrderType,
)
from app.infrastructure.execution.driver.protocol import OrderStatus


class TestExecutionDriver:
    """执行器驱动测试"""

    @pytest.mark.asyncio
    async def test_submit_order(self):
        """测试订单提交"""
        executor = RedisStreamExecutor(
            redis_url="redis://localhost:6379/0",
            queue_name="test_execution_queue",
            timeout=5.0,
        )

        connected = await executor.connect()
        if not connected:
            pytest.skip("Redis not available")

        request = TradeRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            amount=0.001,
            price=50000.0,
            exchange="binance",
        )

        response = await executor.submit_order(request)

        assert response.request_id == request.request_id
        assert response.status in (OrderStatus.FILLED, OrderStatus.SUBMITTED, OrderStatus.PENDING)

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        executor = RedisStreamExecutor(redis_url="redis://localhost:6379/0")

        connected = await executor.connect()
        if not connected:
            pytest.skip("Redis not available")

        healthy = await executor.health_check()
        assert isinstance(healthy, bool)


class TestTradeRequest:
    """交易请求测试"""

    def test_create_request(self):
        """测试创建请求"""
        request = TradeRequest(
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            amount=0.1,
            price=3000.0,
        )

        assert request.symbol == "ETHUSDT"
        assert request.side == OrderSide.SELL
        assert request.order_type == OrderType.LIMIT
        assert request.amount == 0.1

    def test_serialize(self):
        """测试序列化"""
        request = TradeRequest(
            symbol="BNBUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.STOP,
            amount=1.0,
            price=400.0,
            stop_price=390.0,
        )

        data = request.to_dict()

        assert data["symbol"] == "BNBUSDT"
        assert data["side"] == "buy"
        assert data["stop_price"] == 390.0

    def test_deserialize(self):
        """测试反序列化"""
        data = {
            "request_id": "test_123",
            "symbol": "600519",
            "side": "sell",
            "order_type": "limit",
            "amount": 100.0,
            "price": 1800.0,
        }

        request = TradeRequest.from_dict(data)

        assert request.request_id == "test_123"
        assert request.symbol == "600519"
        assert request.side == OrderSide.SELL
        assert request.order_type == OrderType.LIMIT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])