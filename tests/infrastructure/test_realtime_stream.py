"""Realtime Stream 集成测试."""

import asyncio
import pytest

from app.infrastructure.realtime.market_stream import Quote, MarketStreamProcessor
from app.infrastructure.realtime.stream_processor import QuoteStreamProcessor, create_pipeline
from app.infrastructure.realtime.quote_aggregator import QuoteAggregator


class TestQuote:
    """行情数据测试"""

    def test_create_quote(self):
        """测试创建行情"""
        quote = Quote(
            symbol="BTCUSDT",
            price=50000.0,
            volume=1000.0,
            amount=50000000.0,
            change_pct=2.5,
        )

        assert quote.symbol == "BTCUSDT"
        assert quote.price == 50000.0

    def test_serialize(self):
        """测试序列化"""
        quote = Quote(
            symbol="ETHUSDT",
            price=3000.0,
            volume=500.0,
            amount=1500000.0,
            change_pct=-1.2,
        )

        data = quote.to_dict()

        assert data["symbol"] == "ETHUSDT"
        assert data["change_pct"] == -1.2

    def test_deserialize(self):
        """测试反序列化"""
        data = {
            "symbol": "BNBUSDT",
            "price": 400.0,
            "volume": 200.0,
            "amount": 80000.0,
            "change_pct": 0.5,
            "timestamp": 1234567890.0,
        }

        quote = Quote.from_dict(data)

        assert quote.symbol == "BNBUSDT"
        assert quote.timestamp == 1234567890.0


class TestMarketStreamProcessor:
    """市场流处理器测试"""

    @pytest.mark.asyncio
    async def test_subscribe(self):
        """测试订阅"""
        processor = MarketStreamProcessor(redis_url="redis://localhost:6379/0")

        await processor.subscribe_symbols(["BTCUSDT", "ETHUSDT"])

        assert "BTCUSDT" in processor._subscriptions
        assert "ETHUSDT" in processor._subscriptions

    @pytest.mark.asyncio
    async def test_callback(self):
        """测试回调"""
        received = []

        def on_quote(q: Quote):
            received.append(q)

        processor = MarketStreamProcessor()
        processor.add_callback(on_quote)

        await processor.subscribe_symbols(["BTCUSDT"])
        await processor.start()

        # 等待模拟数据
        await asyncio.sleep(2)

        await processor.stop()

        # 应该有模拟数据
        assert len(received) > 0


class TestStreamProcessor:
    """流处理器测试"""

    def test_create_pipeline(self):
        """测试创建管道"""
        results = []

        def on_quote(q: Quote):
            results.append(q)

        processor = create_pipeline(on_quote, indicators=["sma_20", "ema_10"])

        assert processor is not None

    def test_calculate_sma(self):
        """测试 SMA 计算"""
        processor = QuoteStreamProcessor()

        # 模拟数据
        for i in range(30):
            quote = Quote(
                symbol="TEST",
                price=100.0 + i,
                volume=1000.0,
                amount=100000.0,
                change_pct=0.0,
            )
            processor.process(quote)

        sma = processor.calculate_sma("TEST", window=10)

        assert sma is not None
        assert sma.name == "SMA10"


class TestQuoteAggregator:
    """行情聚合器测试"""

    @pytest.mark.asyncio
    async def test_get_quote(self):
        """测试获取行情"""
        aggregator = QuoteAggregator(redis_url="redis://localhost:6379/0")

        quote = await aggregator.get_quote("BTCUSDT")

        # 可能返回 None 如果没有缓存
        assert quote is None or quote.symbol == "BTCUSDT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])