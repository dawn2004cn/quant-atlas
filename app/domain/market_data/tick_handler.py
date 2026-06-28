from __future__ import annotations

"""Tick Handler - Tick 数据处理。

提供:
- Tick 解析与验证
- 数据标准化
- 异常检测
"""


import time
from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Tick:
    """行情 Tick"""
    symbol: str
    price: float
    volume: float
    amount: float
    bid: float = 0.0
    ask: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class TickValidator:
    """Tick 验证器"""

    @staticmethod
    def validate(tick: Tick) -> tuple[bool, str]:
        """验证 Tick 数据合法性

        Returns:
            (是否合法, 错误信息)
        """
        if not tick.symbol:
            return False, "Empty symbol"

        if tick.price <= 0:
            return False, "Invalid price"

        if tick.volume < 0:
            return False, "Negative volume"

        if tick.amount < 0:
            return False, "Negative amount"

        if tick.bid > 0 and tick.ask > 0 and tick.bid >= tick.ask:
            return False, "Bid >= Ask"

        return True, ""


class TickNormalizer:
    """Tick 标准化处理器"""

    @staticmethod
    def normalize(tick: Tick) -> Tick:
        """标准化 Tick 数据"""
        # 确保价格精度
        tick.price = round(tick.price, 2)
        tick.bid = round(tick.bid, 2)
        tick.ask = round(tick.ask, 2)

        # 确保数量精度
        tick.volume = round(tick.volume, 2)
        tick.amount = round(tick.amount, 2)

        return tick


class TickAnomalyDetector:
    """Tick 异常检测器"""

    def __init__(self, threshold_pct: float = 10.0):
        self._threshold = threshold_pct
        self._last_prices: dict[str, float] = {}

    def detect(self, tick: Tick) -> bool:
        """检测异常 Tick

        Returns:
            True 表示检测到异常
        """
        last_price = self._last_prices.get(tick.symbol)

        if last_price and last_price > 0:
            change_pct = abs(tick.price - last_price) / last_price * 100
            if change_pct > self._threshold:
                logger.warning(
                    f"Anomaly detected for {tick.symbol}: "
                    f"price changed {change_pct:.2f}% "
                    f"({last_price} -> {tick.price})"
                )
                return True

        self._last_prices[tick.symbol] = tick.price
        return False
