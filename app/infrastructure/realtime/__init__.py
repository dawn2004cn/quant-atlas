"""Realtime Market Data Stream Processing.

提供实时行情数据的流式处理能力:
- Redis Stream 订阅器
- RxPY 流式处理
- 背压处理
"""

from .market_stream import MarketStreamProcessor, QuoteStream
from .stream_processor import StreamProcessor, create_pipeline

try:
    from .quote_aggregator import QuoteAggregator
except Exception:  # noqa: BLE001
    QuoteAggregator = None  # type: ignore[misc,assignment]

__all__ = [
    "MarketStreamProcessor",
    "QuoteStream",
    "StreamProcessor",
    "create_pipeline",
    "QuoteAggregator",
]
