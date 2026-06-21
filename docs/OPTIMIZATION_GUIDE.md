# Quant Atlas 架构优化指南

本文档说明如何使用三个优化方向的实现。

---

## 方向1: 执行器驱动模式

### 快速开始

```python
from app.infrastructure.execution.driver import (
    RedisStreamExecutor,
    TradeRequest,
    OrderSide,
    OrderType,
)

# 1. 创建执行器
executor = RedisStreamExecutor(
    redis_url="redis://192.168.8.103:6380/0",
    timeout=30.0,
)

# 2. 连接
await executor.connect()

# 3. 提交订单
request = TradeRequest(
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    amount=0.001,
    price=50000.0,
)

response = await executor.submit_order(request)
print(f"Order status: {response.status}")
```

### 在 TradingBotService 中使用

```python
from app.infrastructure.execution.driver import RedisStreamExecutor
from app.application.services.trading import TradingBotService

# 创建执行器
executor = RedisStreamExecutor()
await executor.connect()

# 创建服务 (使用执行器驱动)
service = TradingBotService(
    repository=repo,
    exchange_factory=legacy_exchange_factory,
    strategy_factory=strategy_factory,
    execution_gateway=executor,  # 新增参数
)
```

---

## 方向2: 时序数据流式架构

### 快速开始

```python
import asyncio
from app.infrastructure.realtime import (
    MarketStreamProcessor,
    QuoteStreamProcessor,
    QuoteAggregator,
)

# 1. 创建流处理器
processor = MarketStreamProcessor(
    redis_url="redis://192.168.8.103:6380/0",
)

# 2. 定义回调
def on_quote(quote):
    print(f"Price update: {quote.symbol} = {quote.price}")

processor.add_callback(on_quote)

# 3. 订阅并启动
await processor.subscribe_symbols(["BTCUSDT", "ETHUSDT"])
await processor.start()

# 保持运行
await asyncio.sleep(60)

# 4. 停止
await processor.stop()
```

### 使用流处理管道

```python
from app.infrastructure.realtime import create_pipeline

# 创建管道
processor = create_pipeline(
    on_quote=lambda q: print(f"Processed: {q}"),
    indicators=["sma_20", "ema_10", "rsi_14"],
)

# 处理行情
from app.infrastructure.realtime.market_stream import Quote
quote = Quote(symbol="BTCUSDT", price=50000, volume=100, amount=5000000, change_pct=2.0)
processor.process(quote)

# 计算指标
sma = processor.calculate_sma("BTCUSDT", window=20)
rsi = processor.calculate_rsi("BTCUSDT", window=14)
```

### 使用聚合器

```python
from app.infrastructure.realtime import QuoteAggregator

aggregator = QuoteAggregator(redis_url="redis://192.168.8.103:6380/0")
await aggregator.start()

# 订阅
await aggregator.subscribe(
    symbols=["600519", "000001"],
    callback=lambda q: print(f"Aggregated: {q}"),
)

# 获取当前行情
quote = await aggregator.get_quote("600519")
```

---

## 方向3: Apache Arrow 零拷贝计算

### 快速开始

```python
import numpy as np
from app.infrastructure.compute.arrow_client import ArrowComputeClient, get_arrow_client

# 获取客户端 (自动选择最优路径)
client = get_arrow_client(use_flight=False)

# 准备数据
data = np.random.randn(10000).astype(np.float64)

# 计算 SMA (零拷贝)
result = client.calculate_sma(data, window=20)

# 批量计算
results = client.batch_calculate(
    data,
    indicators=["sma_5", "sma_10", "sma_20", "ema_10", "zscore_20"],
)

for indicator, values in results.items():
    print(f"{indicator}: {values[:5]}")
```

### 使用内存池

```python
from app.infrastructure.compute.arrow_client import ArrowMemoryPool

pool = ArrowMemoryPool(max_size_mb=100)

# 分配
arr = pool.allocate((1000, 1000))

# 使用
arr[:] = np.random.randn(1000, 1000)

# 回收
pool.release(arr)

# 统计
print(pool.stats())
```

---

## 运行测试

```bash
# 执行器驱动测试
pytest tests/test_execution_driver.py -v

# 实时流测试
pytest tests/test_realtime_stream.py -v

# Arrow 计算测试
pytest tests/test_arrow_compute.py -v
```

---

## 配置说明

### Redis 配置

默认 Redis 地址: `redis://192.168.8.103:6380/0`

可通过环境变量覆盖:
```bash
export REDIS_URL="redis://localhost:6379/0"
```

### 执行器配置

```python
executor = RedisStreamExecutor(
    redis_url="redis://192.168.8.103:6380/0",
    queue_name="execution_queue",      # 订单队列
    result_prefix="execution_result:", # 结果前缀
    timeout=30.0,                       # 超时时间
)
```

---

## 注意事项

1. **执行器驱动**: 需要 Redis 支持，生产环境建议使用 Redis Cluster
2. **流式架构**: 目前使用模拟数据源，需要接入真实行情 API
3. **零拷贝**: 需要先编译 Rust 核心 (`cd rust_core && cargo build --release`)