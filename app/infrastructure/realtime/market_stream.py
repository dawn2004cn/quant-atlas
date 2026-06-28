from __future__ import annotations





from app.core.runtime_config import get_runtime





"""Market Stream Processor - 实时行情流处理器。


基于 Redis Stream 实现实时行情推送，支持:


- symbol 订阅


- 背压处理


- 断线重连


"""








import asyncio


import json




import time


from dataclasses import dataclass, field


from collections.abc import Callable





import redis


from app.infrastructure.redis_client import RedisClientPool





from app.core.logger import get_logger





logger = get_logger(__name__)








@dataclass


class Quote:


    """行情数据"""


    symbol: str


    price: float


    volume: float


    amount: float


    change_pct: float


    timestamp: float = field(default_factory=time.time)


    bid: float = 0


    ask: float = 0


    high: float = 0


    low: float = 0


    open: float = 0


    pre_close: float = 0





    def to_dict(self) -> dict:


        return {


            "symbol": self.symbol,


            "price": self.price,


            "volume": self.volume,


            "amount": self.amount,


            "change_pct": self.change_pct,


            "timestamp": self.timestamp,


            "bid": self.bid,


            "ask": self.ask,


            "high": self.high,


            "low": self.low,


            "open": self.open,


            "pre_close": self.pre_close,


        }





    @classmethod


    def from_dict(cls, data: dict) -> Quote:


        return cls(


            symbol=data.get("symbol", ""),


            price=float(data.get("price", 0)),


            volume=float(data.get("volume", 0)),


            amount=float(data.get("amount", 0)),


            change_pct=float(data.get("change_pct", 0)),


            timestamp=float(data.get("timestamp", time.time())),


            bid=float(data.get("bid", 0)),


            ask=float(data.get("ask", 0)),


            high=float(data.get("high", 0)),


            low=float(data.get("low", 0)),


            open=float(data.get("open", 0)),


            pre_close=float(data.get("pre_close", 0)),


        )








class QuoteStream:


    """行情(适配器模"""





    def __init__(self, callback: Callable[[Quote], None]):


        self._callback = callback





    def send(self, quote: Quote) -> None:


        self._callback(quote)








class MarketStreamProcessor:


    """市场行情流处理器





    支持两种模式:


    1. Redis Stream 模式: 订阅 Redis Stream 获取实时行情


    2. WebSocket 模式: 订阅 WebSocket 获取实时行情


    """





    def __init__(


        self,


        redis_url: str = get_runtime("REDIS_URL", ""),


        stream_prefix: str = "quotes:",


        consumer_group: str = "market_processor",


    ):


        self._redis_url = redis_url


        self._stream_prefix = stream_prefix


        self._consumer_group = consumer_group


        self._client: redis.Redis | None = None


        self._subscriptions: dict[str, bool] = {}


        self._running = False


        self._tasks: list[asyncio.Task] = []


        self._callbacks: list[Callable[[Quote], None]] = []





    @property


    def client(self) -> redis.Redis:


        if self._client is None:


            self._client = RedisClientPool.get(self._redis_url).client


        return self._client





    def add_callback(self, callback: Callable[[Quote], None]) -> None:


        """添加行情回调"""


        self._callbacks.append(callback)





    def remove_callback(self, callback: Callable[[Quote], None]) -> None:


        """移除行情回调"""


        self._callbacks.remove(callback)





    def _notify(self, quote: Quote) -> None:


        """通知所有订阅"""


        for cb in self._callbacks:


            try:


                cb(quote)


            except Exception as e:


                logger.error(f"Callback error: {e}")





    async def subscribe_symbols(self, symbols: list[str]) -> None:


        """订阅 symbol 行情"""


        for symbol in symbols:


            self._subscriptions[symbol] = True


            logger.info(f"Subscribed to {symbol}")





    async def unsubscribe_symbols(self, symbols: list[str]) -> None:


        """取消订阅"""


        for symbol in symbols:


            self._subscriptions.pop(symbol, None)


            logger.info(f"Unsubscribed from {symbol}")





    async def start(self) -> None:


        """启动流处"""


        self._running = True





        # 创建消费者组


        stream_name = f"{self._stream_prefix}all"


        try:


            self.client.xgroup_create(stream_name, self._consumer_group, id="0", mkstream=True)


        except redis.ResponseError as e:


            if "BUSYGROUP" not in str(e):


                raise





        # 启动轮询任务


        task = asyncio.create_task(self._poll_loop())


        self._tasks.append(task)





        # 启动模拟行情推(测试


        if not self._is_real_data_source():


            test_task = asyncio.create_task(self._simulate_quotes())


            self._tasks.append(test_task)





        logger.info("MarketStreamProcessor started")





    async def stop(self) -> None:


        """停止流处"""


        self._running = False


        for task in self._tasks:


            task.cancel()


        self._tasks.clear()


        logger.info("MarketStreamProcessor stopped")





    async def _poll_loop(self) -> None:


        """轮询 Redis Stream"""


        stream_name = f"{self._stream_prefix}all"





        while self._running:


            try:


                # 读取消息 (阻塞 5


                messages = self.client.xreadgroup(


                    self._consumer_group,


                    "worker_1",


                    {stream_name: ">"},


                    count=10,


                    block=5000,


                )





                if not messages:


                    continue





                for stream, msgs in messages:


                    for msg_id, msg_data in msgs:


                        try:


                            payload = json.loads(msg_data.get("payload", "{}"))


                            quote = Quote.from_dict(payload)





                            if quote.symbol in self._subscriptions:


                                self._notify(quote)





                            # 确认消息


                            self.client.xack(stream_name, self._consumer_group, msg_id)


                        except Exception as e:


                            logger.error(f"Process message error: {e}")





            except asyncio.CancelledError:


                break


            except Exception as e:


                logger.error(f"Poll loop error: {e}")


                await asyncio.sleep(1)





    async def _simulate_quotes(self) -> None:


        """模拟推送行(测试"""


        import random





        base_prices = {


            "BTCUSDT": 50000,


            "ETHUSDT": 3000,


            "BNBUSDT": 400,


            "600519": 1800,


            "000001": 15,


        }





        while self._running:


            for symbol, base_price in base_prices.items():


                if symbol not in self._subscriptions:


                    continue





                # 模拟价格波动


                change = random.uniform(-0.02, 0.02)


                price = base_price * (1 + change)





                quote = Quote(


                    symbol=symbol,


                    price=price,


                    volume=random.uniform(100, 10000),


                    amount=random.uniform(10000, 1000000),


                    change_pct=change * 100,


                    high=price * 1.01,


                    low=price * 0.99,


                    open=base_price,


                    pre_close=base_price,


                    timestamp=time.time(),


                )





                self._notify(quote)





            await asyncio.sleep(1)  # 1秒推送一


    def _is_real_data_source(self) -> bool:
        from app.core.runtime_config import get_runtime_bool
        return get_runtime_bool("ENABLE_QUOTE_BROADCAST", False) or get_runtime_bool("USE_REAL_QUOTE_STREAM", False)





    # ========== 便捷方法 ==========





    def get_latest_quote(self, symbol: str) -> Quote | None:


        """获取最新行"""


        key = f"latest_quote:{symbol}"


        data = self.client.get(key)


        if data:


            return Quote.from_dict(json.loads(data))


        return None





    def get_historical(self, symbol: str, limit: int = 100) -> list[Quote]:


        """获取历史行情"""


        key = f"history:{symbol}"


        data = self.client.lrange(key, 0, limit - 1)


        return [Quote.from_dict(json.loads(d)) for d in data if d]








class AsyncMarketStream:


    """异步行情(返回 generator)"""





    def __init__(self, processor: MarketStreamProcessor):


        self._processor = processor


        self._queue: asyncio.Queue[Quote] = asyncio.Queue(maxsize=1000)





    async def __anext__(self) -> Quote:


        return await self._queue.get()





    def __aiter__(self) -> AsyncMarketStream:


        return self





    def _on_quote(self, quote: Quote) -> None:


        """内部回调"""


        try:


            self._queue.put_nowait(quote)


        except asyncio.QueueFull:


            logger.warning("Quote queue full, dropping message")


