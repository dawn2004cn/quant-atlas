# 新架构说明 (New Architecture Documentation)

## 概述

本项目已根据 `docs/option_plan.md` 中的 Phase 6-8 计划完成架构重构，引入响应式编程、领域模型纯净化和事件驱动架构。

## 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                    │
│         (Flask Blueprints, REST API, Web UI)            │
├─────────────────────────────────────────────────────────┤
│                   Application Layer                     │
│    (Application Services, DTOs, Event Handlers)         │
├─────────────────────────────────────────────────────────┤
│                     Domain Layer                        │
│      (Domain Models, Business Logic, Entities)          │
├─────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                   │
│   (Market Providers, Database, Cache, Async Tasks)      │
└─────────────────────────────────────────────────────────┘
```

## Phase 6: 响应式架构 (Async/Reactive)

### 新增文件
- `app/infrastructure/providers/async_market_provider.py` - 异步市场数据提供者
- `app/infrastructure/task_queue.py` - 异步任务队列
- `app/application/services/async_mixin.py` - 异步混入类
- `app/infrastructure/repositories/async_repository.py` - 异步数据库仓库

### 特性
- 支持异步数据获取
- 任务优先级队列
- 非阻塞 I/O 操作

## Phase 7: 领域模型纯净化 (Domain Model Purity)

### 领域模型 (`app/domain/models/`)

| 模型 | 用途 |
|------|------|
| `risk_models.py` | 风险管理: RiskCalculator, RiskMetrics |
| `signal_models.py` | 交易信号: SignalGenerator, TradingSignal |
| `portfolio_models.py` | 组合管理: Portfolio, Position, PortfolioAnalyzer |
| `analysis_models.py` | 技术分析: TechnicalIndicators, Analyzer, AnalysisService |
| `market_models.py` | 市场数据: Quote, MarketSentiment, MarketAnalyzer |

### DTOs (`app/application/dto/complete_dto.py`)

- `QuoteDTO` - 行情数据
- `SignalDTO` - 交易信号
- `PositionDTO` - 持仓
- `PortfolioDTO` - 组合
- `RiskAssessmentDTO` - 风评
- `AnalysisResultDTO` - 分析结果

### 使用示例

```python
from app.domain.models import SignalGenerator, RiskCalculator, Portfolio

# 生成交易信号
signal = SignalGenerator.generate_breakout_signal(
    code="600519",
    name="贵州茅台",
    price=1800.0,
    volume=1000000,
    high=1820.0,
    low=1780.0,
    open_price=1790.0,
    prev_close=1795.0,
    avg_volume_20d=800000,
)

# 计算风险
risk = RiskCalculator.calculate_position_risk(
    position_value=50000,
    portfolio_value=100000,
    weight=0.5,
    volatility=0.25,
)

# 管理组合
portfolio = Portfolio(name="My Portfolio", initial_capital=100000)
```

## Phase 8: 事件驱动架构 (Event-Driven)

### 事件总线 (`app/application/events/`)

| 文件 | 说明 |
|------|------|
| `event_bus.py` | 事件总线核心 |
| `handlers.py` | 事件处理器注册 |
| `middleware.py` | 事件中间件 |
| `workflows.py` | 业务工作流 |
| `trading_workflows.py` | 交易工作流 |
| `event_handlers.py` | 事件处理器实现 |

### 事件类型

```python
from app.application.events import EventType, publish_event

# 发布事件
await publish_event(
    EventType.SIGNAL_GENERATED,
    {"code": "600519", "signal_type": "breakout"},
    source="MyService"
)

# 订阅事件
@event_bus.subscribe(EventType.SIGNAL_GENERATED)
def handle_signal(event):
    print(f"Signal: {event.payload}")
```

### 事件处理器

- `RiskEventHandler` - 风控事件处理
- `DataEventHandler` - 数据事件处理
- `MarketEventHandler` - 市场事件处理
- `TaskEventHandler` - 任务事件处理

## API 端点

### 新架构 API (`/api/v1/arch/`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/signals/generate` | POST | 生成信号 |
| `/signals/stock/<code>` | GET | 获取股票信号 |
| `/portfolio` | GET | 获取组合 |
| `/portfolio/position` | POST | 添加持仓 |
| `/risk/assess/position` | POST | 持仓风评 |
| `/risk/assess/portfolio` | POST | 组合风评 |
| `/scanner/breakout` | POST | 突破扫描 |
| `/scanner/momentum` | POST | 动量扫描 |
| `/analysis/stock/<code>` | GET | 股票分析 |
| `/market/sentiment` | POST | 市场情绪 |
| `/market/regime` | POST | 市场状态 |
| `/events` | GET | 事件历史 |

## 应用服务

| 服务 | 文件 | 说明 |
|------|------|------|
| `SignalApplicationService` | `strategy/signal_application_service.py` | 信号生成 |
| `PortfolioApplicationService` | `portfolio/portfolio_application_service.py` | 组合管理 |
| `RiskApplicationService` | `trading/risk_application_service.py` | 风险管理 |
| `StockScannerService` | `scanner/stock_scanner_service.py` | 股票扫描 |
| `MarketDataAggregator` | `market_data/market_data_aggregator.py` | 数据聚合 |
| `AnalysisApplicationService` | `analysis/analysis_application_service.py` | 技术分析 |

## 测试

```bash
# 运行单元测试
python -m pytest tests/test_domain_models.py -v

# 运行综合测试
python -m pytest tests/test_comprehensive.py -v
```

## 迁移指南

### 从 Dict 到 DTO

**之前:**
```python
def get_quote(code):
    return {"code": code, "price": 1800}
```

**现在:**
```python
from app.application.dto.complete_dto import QuoteDTO

def get_quote(code):
    return QuoteDTO(code=code, price=1800)
```

### 从同步到异步

**之前:**
```python
def get_data(code):
    return provider.get_quote(code)
```

**现在:**
```python
async def get_data(code):
    return await provider.get_quote_async(code)
```

### 从直接调用到事件

**之前:**
```python
def on_signal(signal):
    analysis_service.analyze(signal)
```

**现在:**
```python
# 发布事件
await publish_event(EventType.SIGNAL_GENERATED, {"signal": signal})

# 订阅处理
@event_bus.subscribe(EventType.SIGNAL_GENERATED)
async def handle_signal(event):
    await analysis_service.analyze(event.payload)
```

## 文件结构

```
app/
├── domain/
│   └── models/
│       ├── risk_models.py
│       ├── signal_models.py
│       ├── portfolio_models.py
│       ├── analysis_models.py
│       └── market_models.py
├── application/
│   ├── dto/
│   │   └── complete_dto.py
│   ├── events/
│   │   ├── event_bus.py
│   │   ├── handlers.py
│   │   ├── workflows.py
│   │   └── event_handlers.py
│   ├── middleware/
│   │   ├── request_middleware.py
│   │   ├── degradation.py
│   │   └── validation.py
│   └── services/
│       ├── architecture_integration.py
│       └── ...
├── infrastructure/
│   ├── providers/
│   │   └── async_market_provider.py
│   └── task_queue.py
└── presentation/
    └── api/
        ├── routes_v1_health.py
        └── routes_v1_arch.py
```

## 完整 API 端点列表

### 健康检查
- `GET /api/v1/arch/health` - 新架构健康状态

### 信号与持仓
- `POST /api/v1/arch/signals/generate` - 生成交易信号
- `GET /api/v1/arch/signals/stock/<code>` - 获取股票信号

### 组合管理
- `GET /api/v1/arch/portfolio` - 获取组合
- `GET /api/v1/arch/portfolio/summary` - 组合摘要
- `GET /api/v1/arch/portfolio/metrics` - 组合指标
- `POST /api/v1/arch/portfolio/position` - 添加持仓
- `DELETE /api/v1/arch/portfolio/position/<code>` - 平仓

### 风险管理
- `POST /api/v1/arch/risk/assess/position` - 持仓风评
- `POST /api/v1/arch/risk/assess/portfolio` - 组合风评
- `POST /api/v1/arch/risk/check-trade` - 交易风控检查
- `GET /api/v1/arch/risk/limits` - 风控限额
- `GET /api/v1/arch/risk/alerts` - 风控警报

### 股票扫描
- `POST /api/v1/arch/scanner/breakout` - 突破信号扫描
- `POST /api/v1/arch/scanner/volume` - 量能信号扫描
- `POST /api/v1/arch/scanner/momentum` - 动量信号扫描
- `POST /api/v1/arch/scanner/low-risk` - 低风险股票扫描

### 技术分析
- `GET /api/v1/arch/analysis/stock/<code>` - 股票分析
- `POST /api/v1/arch/analysis/batch` - 批量分析
- `POST /api/v1/arch/analysis/trend` - 快速趋势计算
- `POST /api/v1/arch/analysis/support-resistance` - 支撑阻力位
- `POST /api/v1/arch/analysis/fibonacci` - 斐波那契回撤

### 市场数据
- `POST /api/v1/arch/aggregator/quote/<code>` - 聚合行情
- `POST /api/v1/arch/aggregator/quote` - 批量聚合行情
- `GET /api/v1/arch/aggregator/sources` - 数据源状态
- `POST /api/v1/arch/market/sentiment` - 市场情绪
- `POST /api/v1/arch/market/regime` - 市场状态检测
- `POST /api/v1/arch/market/turning-points` - 转折点检测

### 日历
- `GET /api/v1/arch/market/calendar/is-trading-day` - 交易日判断
- `GET /api/v1/arch/market/calendar/next-trading-day` - 下一交易日

### 通知
- `GET /api/v1/arch/notifications` - 获取通知
- `POST /api/v1/arch/notifications/<id>/read` - 标记已读
- `POST /api/v1/arch/notifications/send` - 发送通知

### 回测
- `POST /api/v1/arch/backtest/run` - 运行回测
- `POST /api/v1/arch/backtest/analyze` - 分析交易
- `POST /api/v1/arch/backtest/compare` - 比较回测结果

### 缓存
- `GET /api/v1/arch/cache/stats` - 缓存统计
- `POST /api/v1/arch/cache/clear` - 清除缓存
- `POST /api/v1/arch/cache/invalidate` - 失效缓存

### 批处理
- `POST /api/v1/arch/batch/quotes` - 批量获取行情
- `POST /api/v1/arch/batch/analyze` - 批量分析

### 事件
- `GET /api/v1/arch/events` - 事件历史

## 完整领域模型列表

| 模块 | 文件 | 主要类 |
|------|------|--------|
| 风险 | risk_models.py | RiskCalculator, RiskMetrics, RiskLevel |
| 信号 | signal_models.py | SignalGenerator, TradingSignal, SignalType |
| 组合 | portfolio_models.py | Portfolio, Position, PortfolioAnalyzer |
| 分析 | analysis_models.py | TechnicalIndicators, Analyzer, AnalysisService |
| 市场 | market_models.py | Quote, MarketAnalyzer, CalendarService |
| 回测 | backtest_models.py | BacktestEngine, BacktestResult, Trade |

## 完整领域服务列表

| 服务 | 文件 | 用途 |
|------|------|------|
| 通知服务 | notification_service.py | 事件驱动的通知系统 |
| 缓存服务 | cache_service.py | 内存缓存 |
| 批处理服务 | batch_service.py | 并行批处理 |

## Phase 9: DTO 与类型契约标准化 ✅

### DTO 文件
- `app/application/dto/complete_dto.py` - 完整 DTO 集合 (30+)
- `app/application/dto/validators.py` - DTO 验证器

### 验证器
- `StockCodeValidator` - 股票代码验证
- `PriceValidator` - 价格验证
- `QuantityValidator` - 数量验证
- `DateValidator` - 日期验证

### 验证 DTO
- `StockRequestDTO` - 股票请求
- `QuoteRequestDTO` - 行情请求
- `TradeRequestDTO` - 交易请求
- `AnalysisRequestDTO` - 分析请求
- `BacktestRequestDTO` - 回测请求
- `RiskAssessmentRequestDTO` - 风控请求

## Phase 10: 领域驱动的逻辑封装 ✅

### 领域模型 (已覆盖)
- 风险模型: `RiskCalculator`, `RiskMetrics`, `RiskLevel`
- 信号模型: `SignalGenerator`, `TradingSignal`
- 组合模型: `Portfolio`, `Position`
- 分析模型: `Analyzer`, `AnalysisService`
- 市场模型: `MarketAnalyzer`, `CalendarService`
- 回测模型: `BacktestEngine`, `BacktestResult`

### 领域服务
- `notification_service.py` - 通知系统
- `cache_service.py` - 缓存服务
- `batch_service.py` - 批处理服务

## Phase 11: 基础设施适配器重构 ✅

### 持久化映射器 (`app/infrastructure/persistence/`)
- `mappers.py` - Entity 到 DBModel 映射层

### 映射器实现
- `StockMapper` - 股票映射
- `QuoteMapper` - 行情映射
- `UserMapper` - 用户映射
- `WatchlistMapper` - 自选股映射
- `PositionMapper` - 持仓映射
- `SignalMapper` - 信号映射
- `MapperRegistry` - 映射器注册表

### 领域仓储 (`app/infrastructure/repositories/`)
- `domain_repositories.py` - 抽象仓储实现
  - `StockRepository`
  - `QuoteRepository`
  - `WatchlistRepository`
  - `PositionRepository`
  - `SignalRepository`
  - `AlertRepository`

## Phase 10: 流水线管道化 ✅

### Pipeline 设计模式 (`app/application/pipeline/`)
- `data_pipeline.py` - 流水线核心
  - `Reader` - 数据读取阶段
  - `Validator` - 数据验证阶段
  - `Transformer` - 数据转换阶段
  - `Writer` - 数据写入阶段
  - `DataPipeline` - 完整流水线
  - `DataQualityGate` - 数据质量门禁
  - `PipelineBuilder` - 流水线构建器

### 流水线示例 (`pipeline_examples.py`)
- `MarketDataPipeline` - 行情数据处理流水线
- `StockDataPipeline` - 股票数据处理流水线

## Phase 12: 事件驱动的解耦 ✅

### 事件总线 (`app/application/events/`)
- `event_bus.py` - 事件总线核心
- `event_handlers.py` - 事件处理器
- `workflows.py` - 业务工作流
- `trading_workflows.py` - 交易工作流

### 事件类型 (20+)
- `DATA_SYNCED`, `QUOTE_UPDATED`
- `SIGNAL_GENERATED`, `POSITION_OPENED`
- `RISK_ALERT`, `TASK_COMPLETED`
- `MARKET_OPEN`, `MARKET_CLOSE`
- 等等

## Phase 13: 领域实体模型化 ✅

### 领域模型扩展 (`app/domain/models/`)
- 风险模型: RiskPolicy, RiskRules
- 信号模型: SignalGenerator
- 分析模型: Analyzer, TechnicalIndicators

## Phase 14: 数据流水线与契约化 ✅

### 数据契约 DTO (`app/domain/dto/`)
- `market_data.py` - 市场数据 DTO
  - `BarData` - K线数据 (OHLCV)
  - `QuoteData` - 实时行情
  - `TickData` - 逐笔数据
  - `StockProfile` - 股票档案
  - `MarketStats` - 市场统计
  - `SignalData` - 信号数据
  - `PositionData` - 持仓数据
  - `RiskAssessmentData` - 风评数据

### 特性
- Pydantic BaseModel 定义
- 严格字段验证 (Field + validators)
- 属性计算 (price, pnl, is_up 等)

## Phase 15: 装饰器化 AOP ✅

### AOP 装饰器 (`app/core/decorators/`)
- `aop_decorators.py` - 切面处理
  - `@trace` - 函数追踪
  - `@monitor_latency` - 延迟监控
  - `@log_error` - 错误日志
  - `@retry` - 重试机制
  - `@cache_result` - 结果缓存
  - `@deprecated` - 弃用标记
  - `@timing` - 执行计时
  - `@validate_input` - 输入验证
  - `@audit_log` - 审计日志
  - `@handle_errors` - 错误处理
  - `PerformanceMonitor` - 性能监控上下文管理器

## Phase 12: 弹性服务治理 ✅

### 上下文感知 (`app/core/middleware/resilience.py`)
- `RequestContext` - 请求上下文
- `init_context()` - 初始化上下文
- `get_context()` - 获取当前上下文
- `get_request_id()` - 获取请求 ID
- `get_trace_id()` - 获取追踪 ID
- `set_user_id()` / `get_user_id()` - 用户 ID 管理

### 熔断保护
- `CircuitBreaker` - 熔断器实现
- `CircuitBreakerRegistry` - 熔断器注册表
- `with_circuit_breaker()` - 装饰器
- `CircuitBreakerOpenError` - 熔断异常

### 限流保护
- `RateLimiter` - 限流器
- `with_rate_limit()` - 限流装饰器
- `RateLimitExceededError` - 限流异常

## 完整文件清单

```
app/
├── domain/
│   ├── models/
│   │   ├── risk_models.py
│   │   ├── signal_models.py
│   │   ├── portfolio_models.py
│   │   ├── analysis_models.py
│   │   ├── market_models.py
│   │   └── backtest_models.py
│   └── services/
│       ├── notification_service.py
│       ├── cache_service.py
│       └── batch_service.py
├── application/
│   ├── dto/
│   │   ├── complete_dto.py
│   │   └── validators.py
│   ├── events/
│   │   ├── event_bus.py
│   │   ├── event_handlers.py
│   │   ├── workflows.py
│   │   └── trading_workflows.py
│   └── services/
│       ├── architecture_integration.py
│       └── ...
├── infrastructure/
│   ├── persistence/
│   │   ├── __init__.py
│   │   └── mappers.py
│   ├── repositories/
│   │   └── domain_repositories.py
│   └── providers/
│       └── async_market_provider.py
└── presentation/
    └── api/
        ├── routes_v1_health.py
        └── routes_v1_arch.py
```

## 测试文件

- `tests/test_domain_models.py` - 领域模型测试
- `tests/test_comprehensive.py` - 综合测试
- `tests/test_phase11_adapters.py` - 适配器测试

## Phase 17: 策略模式与逻辑编排 ✅

### 策略系统 (`app/domain/strategies/`)
- `base.py` - 策略基类和实现
  - `BaseStrategy` - 策略抽象基类
  - `MACDStrategy` - MACD策略
  - `RSIStrategy` - RSI策略
  - `BreakoutStrategy` - 突破策略
  - `CompositeStrategy` - 组合策略
  - `StrategyRegistry` - 策略注册表

- `execution.py` - 策略执行引擎
  - `StrategyExecutor` - 策略执行器
  - `SignalDispatcher` - 信号分发器
  - `ExecutionOrder` - 执行订单

## DTO 契约化 (Data Contract Standardization) ✅

### 应用层 DTO (`app/application/dto/`)
- `contracts.py` - 完整 DTO 契约 (30+)
  - 严格字段验证 (Field + validators)
  - 计算属性 (@computed_field)
  - 模型验证器 (@model_validator)
  - 完整类型注解

### 领域层 DTO (`app/domain/dto/`)
- `market_data.py` - 市场数据 DTO
- `trading.py` - 交易执行 DTO

### DTO 工厂 (`app/application/dto/factory.py`)
- `DTOFactory` - DTO 创建工厂
- `register_dtos()` - 自动注册
- `create_dto()` / `validate_dto()` - 便捷函数

### DTO 分类

| 分类 | DTO | 用途 |
|------|-----|------|
| 市场 | BarContract, QuoteContract | K线/行情 |
| 策略 | StrategySignalContract, StrategyResultContract | 策略信号 |
| 组合 | PositionContract, PortfolioContract | 持仓/组合 |
| 风控 | RiskAssessmentContract, RiskLimitContract | 风控评估 |
| 订单 | OrderContract | 订单 |
| 分析 | TechnicalIndicatorContract, AnalysisResultContract | 技术分析 |
| 流水线 | PipelineConfigContract, PipelineResultContract | 数据流水线 |
| 任务 | TaskContract | 任务队列 |
| 事件 | EventContract | 事件 |

## Phase 21: 配置即代码化 ✅

### 配置管理 (`app/core/config.py`)
- `ConfigManager` - 配置管理器
- `AppConfig` - 应用配置 (Pydantic)
- `DatabaseConfig`, `RedisConfig`, `MarketProviderConfig`
- `StrategyConfig`, `RiskConfig`, `LoggingConfig`
- 环境分层: settings.yaml -> settings.{env}.yaml

## Phase 23: 分布式任务队列优先级 ✅

### 优先级任务队列 (`app/infrastructure/task_queue_v2.py`)
- `TaskPriority` - 任务优先级 (HIGH/MEDIUM/LOW)
- `TaskStatus` - 任务状态
- `Task` - 任务定义
- `PriorityTaskQueue` - 优先级队列实现

### 使用场景
- HIGH: 实时交易信号
- MEDIUM: 每日数据更新
- LOW: 因子挖掘实验

## 完整 Phase 总结

| 文档 | Phases | 状态 |
|------|--------|------|
| option_plan.md | 6-8 | ✅ |
| option_plan1.md | 9-12 | ✅ |
| option_plan2.md | 9-12 | ✅ |
| option_plan3.md | 13-16 | ✅ |
| option_plan4.md | 17-24 | ✅ |

## 下一步

1. 继续迁移遗留服务到新架构
2. 添加更多事件处理器
3. 完善测试覆盖
4. 性能优化

## 参考

- [option_plan.md](../docs/option_plan.md)
- [option_plan1.md](../docs/option_plan1.md)
- [option_plan3.md](../docs/option_plan3.md)
- [option_plan4.md](../docs/option_plan4.md)
- [领域驱动设计](https://domainlanguage.com/ddd/)
- [事件驱动架构](https://martinfowler.com/articles/201701-event-driven.html)