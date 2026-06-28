from __future__ import annotations
"""Market Data Bus - 行情数据总线。

实现 Observer 模式，提供:
- 行情推送订阅
- 多播分发
- 过滤与转换
"""


import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from collections.abc import Callable

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Tick:
    """行情 Tick 数据"""
    symbol: str
    price: float
    volume: float
    amount: float
    bid: float = 0.0
    ask: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class Subscriber(ABC):
    """订阅者抽象基类"""

    @abstractmethod
    def on_tick(self, tick: Tick) -> None:
        """接收行情数据"""
        pass

    @abstractmethod
    def on_error(self, error: Exception) -> None:
        """接收错误通知"""
        pass


class SimpleSubscriber(Subscriber):
    """简单订阅者实现"""

    def __init__(
        self,
        name: str,
        on_tick_callback: Callable[[Tick], None] | None = None,
    ):
        self.name = name
        self._on_tick = on_tick_callback
        self._received_count = 0

    def on_tick(self, tick: Tick) -> None:
        self._received_count += 1
        if self._on_tick:
            try:
                self._on_tick(tick)
            except Exception as e:
                self.on_error(e)

    def on_error(self, error: Exception) -> None:
        logger.error(f"Subscriber {self.name} error: {error}")


class Observable:
    """可观察的数据流

    支持:
    - 订阅/取消订阅
    - 数据推送
    - 过滤与转换
    """

    def __init__(self, name: str = ""):
        self.name = name
        self._subscribers: list[Subscriber] = []
        self._lock = threading.RLock()
        self._filters: list[Callable[[Tick], bool]] = []
        self._transforms: list[Callable[[Tick], Tick | None]] = []

    def subscribe(self, subscriber: Subscriber) -> None:
        """订阅数据流"""
        with self._lock:
            if subscriber not in self._subscribers:
                self._subscribers.append(subscriber)
                logger.info(f"Subscriber added to {self.name}: {subscriber}")

    def unsubscribe(self, subscriber: Subscriber) -> None:
        """取消订阅"""
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)
                logger.info(f"Subscriber removed from {self.name}")

    def add_filter(self, predicate: Callable[[Tick], bool]) -> None:
        """添加过滤器"""
        self._filters.append(predicate)

    def add_transform(self, transform: Callable[[Tick], Tick | None]) -> None:
        """添加转换器"""
        self._transforms.append(transform)

    def push(self, tick: Tick) -> int:
        """推送行情数据

        Returns:
            成功接收的订阅者数量
        """
        # 应用过滤
        for f in self._filters:
            if not f(tick):
                return 0

        # 应用转换
        processed_tick = tick
        for t in self._transforms:
            processed_tick = t(processed_tick)
            if processed_tick is None:
                return 0

        # 分发给所有订阅者
        count = 0
        with self._lock:
            for subscriber in self._subscribers:
                try:
                    subscriber.on_tick(processed_tick)
                    count += 1
                except Exception as e:
                    logger.error(f"Subscriber error: {e}")
                    try:
                        subscriber.on_error(e)
                    except Exception as e:
                        logger.warning("data_bus.py.push: %s", e)

        return count

    def subscriber_count(self) -> int:
        """获取订阅者数量"""
        with self._lock:
            return len(self._subscribers)


class MarketDataBus:
    """行情数据总线

    管理多个 Observable 数据流:
    - 按 symbol 分发
    - 全局广播
    - 统计与监控
    """

    def __init__(self):
        self._streams: dict[str, Observable] = {}
        self._global_stream = Observable("global")
        self._lock = threading.RLock()
        self._stats = {
            "total_ticks": 0,
            "total_symbols": 0,
            "last_tick_time": None,
        }

    def get_stream(self, symbol: str) -> Observable:
        """获取或创建 symbol 数据流"""
        with self._lock:
            if symbol not in self._streams:
                self._streams[symbol] = Observable(symbol)
                self._stats["total_symbols"] += 1
            return self._streams[symbol]

    def subscribe(self, symbol: str, subscriber: Subscriber) -> None:
        """订阅指定 symbol 的行情"""
        stream = self.get_stream(symbol)
        stream.subscribe(subscriber)
        logger.info(f"Subscribed to {symbol}")

    def subscribe_global(self, subscriber: Subscriber) -> None:
        """订阅全局行情 (所有 symbol)"""
        self._global_stream.subscribe(subscriber)

    def unsubscribe(self, symbol: str, subscriber: Subscriber) -> None:
        """取消订阅"""
        stream = self._streams.get(symbol)
        if stream:
            stream.unsubscribe(subscriber)

    def publish(self, tick: Tick) -> int:
        """发布行情数据

        Returns:
            接收的订阅者总数
        """
        count = 0

        # 推送到 symbol 专属流
        symbol_stream = self.get_stream(tick.symbol)
        count += symbol_stream.push(tick)

        # 推送到全局流
        count += self._global_stream.push(tick)

        # 更新统计
        self._stats["total_ticks"] += 1
        self._stats["last_tick_time"] = datetime.now()

        return count

    def publish_batch(self, ticks: list[Tick]) -> int:
        """批量发布行情

        Returns:
            总接收数
        """
        total = 0
        for tick in ticks:
            total += self.publish(tick)
        return total

    def get_stats(self) -> dict:
        """获取总线统计"""
        with self._lock:
            return {
                **self._stats,
                "streams": len(self._streams),
                "global_subscribers": self._global_stream.subscriber_count(),
            }

    def list_symbols(self) -> list[str]:
        """列出所有活跃的 symbol"""
        with self._lock:
            return list(self._streams.keys())

    def create_filtered_stream(
        self,
        symbol: str,
        predicate: Callable[[Tick], bool],
    ) -> Observable:
        """创建带过滤器的数据流

        Args:
            symbol: 股票代码
            predicate: 过滤条件

        Returns:
            过滤后的 Observable
        """
        stream = self.get_stream(symbol)
        filtered = Observable(f"{symbol}_filtered")

        # 创建桥接订阅者
        class BridgeSubscriber(Subscriber):
            def on_tick(self, tick: Tick) -> None:
                if predicate(tick):
                    filtered.push(tick)

            def on_error(self, error: Exception) -> None:
                pass

        stream.subscribe(BridgeSubscriber())
        return filtered
