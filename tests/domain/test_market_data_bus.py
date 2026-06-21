"""Market Data Bus Tests."""

import pytest
import time

from app.domain.market_data import (
    MarketDataBus,
    Observable,
    Subscriber,
    MarketStreamProcessor,
    TickHandler,
)
from app.domain.market_data.data_bus import Tick, SimpleSubscriber
from app.domain.market_data.tick_handler import TickValidator, TickNormalizer, TickAnomalyDetector


class TestTick:
    """Tick 数据测试"""

    def test_create_tick(self):
        tick = Tick(symbol="BTCUSDT", price=50000.0, volume=1.0, amount=50000.0)
        assert tick.symbol == "BTCUSDT"
        assert tick.price == 50000.0


class TestObservable:
    """Observable 测试"""

    def test_subscribe_and_push(self):
        observable = Observable("test")
        received = []

        class TestSubscriber(Subscriber):
            def on_tick(self, tick: Tick) -> None:
                received.append(tick)

            def on_error(self, error: Exception) -> None:
                pass

        subscriber = TestSubscriber()
        observable.subscribe(subscriber)

        tick = Tick(symbol="BTC", price=100.0, volume=1.0, amount=100.0)
        count = observable.push(tick)

        assert count == 1
        assert len(received) == 1
        assert received[0].price == 100.0

    def test_unsubscribe(self):
        observable = Observable("test2")

        class TestSubscriber(Subscriber):
            def on_tick(self, tick: Tick) -> None: pass
            def on_error(self, error: Exception) -> None: pass

        subscriber = TestSubscriber()
        observable.subscribe(subscriber)
        assert observable.subscriber_count() == 1

        observable.unsubscribe(subscriber)
        assert observable.subscriber_count() == 0

    def test_filter(self):
        observable = Observable("filtered")
        received = []

        class TestSubscriber(Subscriber):
            def on_tick(self, tick: Tick) -> None:
                received.append(tick)
            def on_error(self, error: Exception) -> None: pass

        observable.add_filter(lambda t: t.price > 100)
        observable.subscribe(TestSubscriber())

        # 不满足过滤条件
        tick1 = Tick(symbol="BTC", price=50.0, volume=1.0, amount=50.0)
        count = observable.push(tick1)
        assert count == 0

        # 满足过滤条件
        tick2 = Tick(symbol="BTC", price=150.0, volume=1.0, amount=150.0)
        count = observable.push(tick2)
        assert count == 1


class TestMarketDataBus:
    """行情数据总线测试"""

    def test_publish_and_subscribe(self):
        bus = MarketDataBus()
        received = []

        class TestSubscriber(Subscriber):
            def on_tick(self, tick: Tick) -> None:
                received.append(tick)
            def on_error(self, error: Exception) -> None: pass

        subscriber = TestSubscriber()
        bus.subscribe("BTCUSDT", subscriber)

        tick = Tick(symbol="BTCUSDT", price=50000.0, volume=1.0, amount=50000.0)
        count = bus.publish(tick)

        assert count >= 1
        assert len(received) == 1

    def test_global_subscribe(self):
        bus = MarketDataBus()
        received = []

        class TestSubscriber(Subscriber):
            def on_tick(self, tick: Tick) -> None:
                received.append(tick)
            def on_error(self, error: Exception) -> None: pass

        subscriber = TestSubscriber()
        bus.subscribe_global(subscriber)

        tick1 = Tick(symbol="BTC", price=50000.0, volume=1.0, amount=50000.0)
        tick2 = Tick(symbol="ETH", price=3000.0, volume=10.0, amount=30000.0)

        bus.publish(tick1)
        bus.publish(tick2)

        assert len(received) == 2

    def test_stats(self):
        bus = MarketDataBus()

        tick = Tick(symbol="BTC", price=50000.0, volume=1.0, amount=50000.0)
        bus.publish(tick)

        stats = bus.get_stats()
        assert stats["total_ticks"] == 1
        assert stats["total_symbols"] == 1

    def test_list_symbols(self):
        bus = MarketDataBus()

        bus.publish(Tick(symbol="BTC", price=50000.0, volume=1.0, amount=50000.0))
        bus.publish(Tick(symbol="ETH", price=3000.0, volume=10.0, amount=30000.0))

        symbols = bus.list_symbols()
        assert "BTC" in symbols
        assert "ETH" in symbols


class TestMarketStreamProcessor:
    """流式处理器测试"""

    def test_process_ticks(self):
        processor = MarketStreamProcessor("BTC", window_size=10)

        for i in range(5):
            tick = Tick(symbol="BTC", price=100.0 + i, volume=1.0, amount=100.0 + i)
            processor.on_tick(tick)

        stats = processor.get_stats()
        assert stats.tick_count == 5
        assert stats.avg_price == 102.0

    def test_signal_detection(self):
        processor = MarketStreamProcessor("BTC", window_size=10)
        signals = []

        processor.on_signal(lambda sig, tick: signals.append(sig))

        # 正常价格
        processor.on_tick(Tick(symbol="BTC", price=100.0, volume=1.0, amount=100.0))

        # 价格突破 (上涨 > 2%)
        processor.on_tick(Tick(symbol="BTC", price=103.0, volume=1.0, amount=103.0))

        assert "price_breakout_up" in signals

    def test_vwap(self):
        processor = MarketStreamProcessor("BTC", window_size=10)

        processor.on_tick(Tick(symbol="BTC", price=100.0, volume=10.0, amount=1000.0))
        processor.on_tick(Tick(symbol="BTC", price=102.0, volume=20.0, amount=2040.0))

        vwap = processor.get_vwap()
        assert abs(vwap - 101.33) < 0.1  # (100*10 + 102*20) / 30


class TestTickHandler:
    """Tick 处理器测试"""

    def test_from_dict(self):
        data = {
            "symbol": "BTC",
            "price": 50000.0,
            "volume": 1.5,
            "amount": 75000.0,
        }
        tick = TickHandler.from_dict(data)
        assert tick.symbol == "BTC"
        assert tick.price == 50000.0

    def test_to_dict(self):
        tick = Tick(symbol="ETH", price=3000.0, volume=10.0, amount=30000.0)
        data = TickHandler.to_dict(tick)
        assert data["symbol"] == "ETH"


class TestTickValidator:
    """Tick 验证器测试"""

    def test_valid_tick(self):
        tick = Tick(symbol="BTC", price=50000.0, volume=1.0, amount=50000.0)
        valid, msg = TickValidator.validate(tick)
        assert valid is True

    def test_invalid_price(self):
        tick = Tick(symbol="BTC", price=-1.0, volume=1.0, amount=50000.0)
        valid, msg = TickValidator.validate(tick)
        assert valid is False

    def test_invalid_symbol(self):
        tick = Tick(symbol="", price=50000.0, volume=1.0, amount=50000.0)
        valid, msg = TickValidator.validate(tick)
        assert valid is False


class TestTickAnomalyDetector:
    """异常检测器测试"""

    def test_detect_anomaly(self):
        detector = TickAnomalyDetector(threshold_pct=5.0)

        # 正常价格
        tick1 = Tick(symbol="BTC", price=100.0, volume=1.0, amount=100.0)
        assert detector.detect(tick1) is False

        # 异常价格 (上涨 20%)
        tick2 = Tick(symbol="BTC", price=120.0, volume=1.0, amount=120.0)
        assert detector.detect(tick2) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])