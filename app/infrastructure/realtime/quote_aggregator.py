from __future__ import annotations

from app.core.runtime_config import get_runtime

"""

Quote Aggregator - 多数据源行情聚合器

聚合多个数据源的行情数据:

- 实时推送 (Redis Stream/WebSocket)

- 定时拉取 (akshare/Tushare)

- 本地缓存



提供统一接口，支持?

优先级配置

- 数据一致性校?- ?转移

"""



import asyncio



from dataclasses import dataclass, field

from enum import Enum

from typing import Any
from collections.abc import Callable



import redis

from app.infrastructure.redis_client import RedisClientPool



from app.core.logger import get_logger

from .market_stream import Quote, MarketStreamProcessor




logger = get_logger(__name__)





class DataSource(str, Enum):

    """数据源"""

    REALTIME = "realtime"  # 实时推送    PUSH = "push"          # WebSocket 推送    POLL = "poll"          # 定时拉取

    CACHE = "cache"        # 本地缓存





@dataclass

class AggregatedQuote:

    """聚合后的行情"""

    symbol: str

    price: float

    volume: float

    amount: float

    change_pct: float

    timestamp: float

    sources: list[str] = field(default_factory=list)

    confidence: float = 1.0  # 数据置信度





class QuoteAggregator:

    """行情聚合器"""



    def __init__(self, redis_url: str = None):

        self._redis_url = redis_url or get_runtime("REDIS_URL","redis://127.0.0.1:6379/0")

        self._redis = None

        self._stream_processor = None

        self._adapters = {}

        self._tasks: list[asyncio.Task] = []

        self._poll_tasks: list[asyncio.Task] = []

        self._running = False

        self._callbacks: list[Callable[[Quote], None]] = []



    @property

    def client(self) -> redis.Redis:

        if self._redis is None:

            self._redis = RedisClientPool.get(self._redis_url).client

        return self._redis



    def register_stream_processor(self, processor: MarketStreamProcessor) -> None:

        """注册实时流处理器"""

        self._stream_processor = processor



    def register_adapter(self, source: DataSource, adapter: Any) -> None:

        """注册数据源适配器"""

        self._adapters[source] = adapter

        logger.info(f"Registered adapter for {source}")



    async def start(self) -> None:

        """启动聚合器"""

        self._running = True

        # 启动流处理

        if self._stream_processor:

            await self._stream_processor.start()

        # 启动轮询任务

        if DataSource.POLL in self._adapters:

            poll_task = asyncio.create_task(self._poll_loop())

            self._poll_tasks.append(poll_task)

        logger.info("QuoteAggregator started")



    async def stop(self) -> None:

        """停止聚合器"""

        self._running = False

        # 停止所有任务

        for task in self._tasks:

            task.cancel()

        for task in self._poll_tasks:

            task.cancel()

        logger.info("QuoteAggregator stopped")



    async def _poll_loop(self) -> None:

        """轮询拉取数据"""

        while self._running:

            try:

                for source, adapter in self._adapters.items():

                    if adapter and hasattr(adapter, 'get_quote'):

                        quote = await adapter.get_quote(source.value)

                        if quote:

                            await self._process_quote(quote, source)

            except Exception as e:

                logger.error(f"Poll loop error: {e}")

            await asyncio.sleep(1)



    async def _process_quote(self, quote: Quote, source: DataSource) -> None:

        """处理单个行情"""

        # 这里可以添加数据聚合逻辑

        pass



    def get(self, symbol: str) -> dict:

        """获取聚合后的行情数据"""

        key = f"quote_cache:{symbol}"

        data = self.client.get(key)

        if data:

            import json

            return json.loads(data)

        return {}





__all__ = ["QuoteAggregator"]
