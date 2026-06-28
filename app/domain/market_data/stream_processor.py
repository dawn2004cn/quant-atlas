from __future__ import annotations
"""Market Stream Processor - 流式行情处理器。

提供:
- 窗口计算
- 指标聚合
- 信号检测
"""


import time
from collections import deque
from dataclasses import dataclass

from app.core.logger import get_logger
from .data_bus import Subscriber, Tick

logger = get_logger(__name__)


@dataclass
class WindowedStats:
    """窗口统计"""
    symbol: str
    avg_price: float
    max_price: float
    min_price: float
    total_volume: float
    tick_count: int
    window_seconds: float


class MarketStreamProcessor(Subscriber):
    """流式行情处理器

    处理实时行情流:
    - 维护滑动窗口
    - 计算实时指标
    - 触发信号
    """

    def __init__(
        self,
        symbol: str,
        window_size: int = 100,
        window_seconds: float = 60.0,
    ):
        self.symbol = symbol
        self._window_size = window_size
        self._window_seconds = window_seconds
        self._ticks: deque[Tick] = deque(maxlen=window_size)
        self._signal_callbacks: list[callable] = []
        self._received_count = 0

    def on_tick(self, tick: Tick) -> None:
        """处理接收到的 Tick"""
        self._received_count += 1
        self._ticks.append(tick)

        # 清理过期数据
        self._cleanup_old_ticks()

        # 计算并检查信号
        self._check_signals(tick)

    def on_error(self, error: Exception) -> None:
        logger.error(f"Stream processor error: {error}")

    def _cleanup_old_ticks(self) -> None:
        """清理窗口外的数据"""
        now = time.time()
        cutoff = now - self._window_seconds

        while self._ticks and self._ticks[0].timestamp < cutoff:
            self._ticks.popleft()

    def _check_signals(self, tick: Tick) -> None:
        """检查信号"""
        if len(self._ticks) < 2:
            return

        # 价格突破信号
        prev = self._ticks[-2]
        if tick.price > prev.price * 1.02:  # 上涨 2%
            self._emit_signal("price_breakout_up", tick)
        elif tick.price < prev.price * 0.98:  # 下跌 2%
            self._emit_signal("price_breakout_down", tick)

    def _emit_signal(self, signal_type: str, tick: Tick) -> None:
        """触发信号"""
        for callback in self._signal_callbacks:
            try:
                callback(signal_type, tick)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")

    def on_signal(self, callback: callable) -> None:
        """注册信号回调"""
        self._signal_callbacks.append(callback)

    def get_stats(self) -> WindowedStats:
        """获取窗口统计"""
        if not self._ticks:
            return WindowedStats(
                symbol=self.symbol,
                avg_price=0,
                max_price=0,
                min_price=0,
                total_volume=0,
                tick_count=0,
                window_seconds=self._window_seconds,
            )

        prices = [t.price for t in self._ticks]
        volumes = [t.volume for t in self._ticks]

        return WindowedStats(
            symbol=self.symbol,
            avg_price=sum(prices) / len(prices),
            max_price=max(prices),
            min_price=min(prices),
            total_volume=sum(volumes),
            tick_count=len(self._ticks),
            window_seconds=self._window_seconds,
        )

    def get_vwap(self) -> float:
        """计算成交量加权平均价 (VWAP)"""
        if not self._ticks:
            return 0.0

        total_value = sum(t.price * t.volume for t in self._ticks)
        total_volume = sum(t.volume for t in self._ticks)

        return total_value / total_volume if total_volume > 0 else 0.0


class TickHandler:
    """Tick 处理器 - 简化 Tick 创建与处理"""

    @staticmethod
    def from_dict(data: dict) -> Tick:
        """从字典创建 Tick"""
        return Tick(
            symbol=data.get("symbol", ""),
            price=float(data.get("price", 0)),
            volume=float(data.get("volume", 0)),
            amount=float(data.get("amount", 0)),
            bid=float(data.get("bid", 0)),
            ask=float(data.get("ask", 0)),
            timestamp=float(data.get("timestamp", time.time())),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def to_dict(tick: Tick) -> dict:
        """Tick 转字典"""
        return {
            "symbol": tick.symbol,
            "price": tick.price,
            "volume": tick.volume,
            "amount": tick.amount,
            "bid": tick.bid,
            "ask": tick.ask,
            "timestamp": tick.timestamp,
            "metadata": tick.metadata,
        }
