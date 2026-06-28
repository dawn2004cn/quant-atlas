from __future__ import annotations

"""Stream Processor - 流式数据处理管道。

提供类似 RxPY 的流式处理能力:
- map/filter/reduce 操作
- 窗口计算
- 指标计算
"""


import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from app.core.logger import get_logger

from .market_stream import Quote

logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class StreamProcessor(Generic[T]):
    """流处理器基类"""

    def __init__(self):
        self._callbacks: list[Callable[[T], None]] = []

    def subscribe(self, callback: Callable[[T], None]) -> None:
        self._callbacks.append(callback)

    def _emit(self, value: T) -> None:
        for cb in self._callbacks:
            try:
                cb(value)
            except Exception as e:
                logger.error(f"Stream callback error: {e}")


@dataclass
class TechnicalIndicator:
    """技术指标"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class WindowedData:
    """窗口化数据"""
    symbol: str
    data: list[Any]
    window_type: str  # time, count
    size: int
    timestamp: float = field(default_factory=time.time)


class QuoteStreamProcessor(StreamProcessor[Quote]):
    """行情流处理器

    支持的操作:
    - map: 转换数据
    - filter: 过滤数据
    - window: 窗口化
    - indicators: 计算指标
    """

    def __init__(self, source: Callable[[], list[Quote]] | None = None):
        super().__init__()
        self._source = source
        self._transforms: list[Callable[[Quote], Quote | None]] = []
        self._filters: list[Callable[[Quote], bool]] = []
        self._buffers: dict[str, list[Quote]] = {}
        self._indicators: dict[str, list[TechnicalIndicator]] = {}

    def map(self, transform: Callable[[Quote], R]) -> QuoteStreamProcessor:
        """数据转换"""
        def wrapped(q: Quote) -> Quote | None:
            result = transform(q)
            return Quote(
                symbol=q.symbol,
                price=result.price if hasattr(result, 'price') else q.price,
                volume=result.volume if hasattr(result, 'volume') else q.volume,
                amount=result.amount if hasattr(result, 'amount') else q.amount,
                change_pct=result.change_pct if hasattr(result, 'change_pct') else q.change_pct,
                timestamp=result.timestamp if hasattr(result, 'timestamp') else q.timestamp,
            ) if result else None
        self._transforms.append(wrapped)
        return self

    def filter(self, predicate: Callable[[Quote], bool]) -> QuoteStreamProcessor:
        """数据过滤"""
        self._filters.append(predicate)
        return self

    def process(self, quote: Quote) -> None:
        """处理单个行情"""
        # 应用过滤
        for f in self._filters:
            if not f(quote):
                return

        # 应用转换
        result = quote
        for t in self._transforms:
            result = t(quote)
            if result is None:
                return

        self._emit(result)

        # 更新缓存 (用于窗口计算)
        self._update_buffer(quote)

    def _update_buffer(self, quote: Quote) -> None:
        """更新缓存"""
        if quote.symbol not in self._buffers:
            self._buffers[quote.symbol] = []

        buffer = self._buffers[quote.symbol]
        buffer.append(quote)

        # 保留最近 500 条
        if len(buffer) > 500:
            buffer.pop(0)

    # ========== 窗口计算 ==========

    def get_window(self, symbol: str, window_type: str = "count", size: int = 100) -> WindowedData:
        """获取窗口数据"""
        buffer = self._buffers.get(symbol, [])

        if window_type == "count":
            data = buffer[-size:]
        else:  # time window
            now = time.time()
            cutoff = now - size  # size seconds
            data = [q for q in buffer if q.timestamp >= cutoff]

        return WindowedData(
            symbol=symbol,
            data=data,
            window_type=window_type,
            size=size,
        )

    # ========== 技术指标计算 ==========

    def calculate_sma(self, symbol: str, window: int = 20) -> TechnicalIndicator | None:
        """计算简单移动平均"""
        buffer = self._buffers.get(symbol, [])
        if len(buffer) < window:
            return None

        prices = [q.price for q in buffer[-window:]]
        sma = sum(prices) / window

        return TechnicalIndicator(name=f"SMA{window}", value=sma)

    def calculate_ema(self, symbol: str, window: int = 20) -> TechnicalIndicator | None:
        """计算指数移动平均"""
        buffer = self._buffers.get(symbol, [])
        if len(buffer) < window:
            return None

        prices = [q.price for q in buffer[-window:]]
        alpha = 2 / (window + 1)

        ema = prices[0]
        for p in prices[1:]:
            ema = p * alpha + ema * (1 - alpha)

        return TechnicalIndicator(name=f"EMA{window}", value=ema)

    def calculate_atr(self, symbol: str, window: int = 14) -> TechnicalIndicator | None:
        """计算平均真实波幅"""
        buffer = self._buffers.get(symbol, [])
        if len(buffer) < window + 1:
            return None

        trs = []
        for i in range(1, len(buffer)):
            high = buffer[i].high
            low = buffer[i].low
            prev_close = buffer[i - 1].price

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)

        atr = sum(trs[-window:]) / window
        return TechnicalIndicator(name=f"ATR{window}", value=atr)

    def calculate_rsi(self, symbol: str, window: int = 14) -> TechnicalIndicator | None:
        """计算相对强弱指标"""
        buffer = self._buffers.get(symbol, [])
        if len(buffer) < window + 1:
            return None

        gains = []
        losses = []
        for i in range(1, len(buffer)):
            change = buffer[i].price - buffer[i - 1].price
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if len(gains) < window:
            return None

        avg_gain = sum(gains[-window:]) / window
        avg_loss = sum(losses[-window:]) / window

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        return TechnicalIndicator(name=f"RSI{window}", value=rsi)


def create_pipeline(
    on_quote: Callable[[Quote], None],
    indicators: list[str] | None = None,
) -> QuoteStreamProcessor:
    """创建行情处理管道

    Args:
        on_quote: 行情回调
        indicators: 需要计算的指标列表

    Returns:
        配置好的流处理器
    """
    processor = QuoteStreamProcessor()

    if indicators:
        for ind in indicators:
            logger.info(f"Pipeline will calculate: {ind}")

    processor.subscribe(on_quote)
    return processor


class BacktestStreamProcessor:
    """回测流处理器 - 支持历史数据回放"""

    def __init__(self, processor: QuoteStreamProcessor):
        self._processor = processor
        self._replaying = False
        self._replay_speed = 1.0

    async def replay(self, symbol: str, from_ts: float, to_ts: float, speed: float = 1.0) -> None:
        """回放历史数据

        Args:
            symbol: 股票代码
            from_ts: 开始时间戳
            to_ts: 结束时间戳
            speed: 回放速度 (1.0 = 真实时间)
        """
        self._replaying = True
        self._replay_speed = speed

        # TODO: 从数据源获取历史数据并按时间回放

        self._replaying = False
        logger.info(f"Replay finished for {symbol}")

    def pause(self) -> None:
        self._replaying = False

    def resume(self) -> None:
        self._replaying = True
