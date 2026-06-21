# Quant Atlas 生产运营手册

> 版本：1.0-stable | 文档生成日期：2026-05-15

---

## 目录

1. [系统概述](#1-系统概述)
2. [架构图谱](#2-架构图谱)
3. [核心组件运维指南](#3-核心组件运维指南)
4. [部署与启动](#4-部署与启动)
5. [监控与告警](#5-监控与告警)
6. [数据管理](#6-数据管理)
7. [故障排查手册](#7-故障排查手册)
8. [安全规范](#8-安全规范)
9. [架构演进路线图](#9-架构演进路线图)
10. [附录](#10-附录)

---

## 1. 系统概述

### 1.1 系统定位

Quant Atlas 是一个高性能量化研究与交易执行平台，具备以下核心能力：

- **Rust 指标引擎**：Native C-Extension 实现 SMA、EMA、RSI、MACD、ATR、Z-Score 等指标，计算速度提升 20-50 倍
- **全链路 DTO 契约化**：基于 Pydantic 的类型安全数据传输
- **事件驱动架构**：基于 Blinker 的解耦消息总线
- **依赖注入容器**：使用 `dependency-injector` 管理服务生命周期
- **异步数据管道**：支持 SQLAlchemy Async + asyncmy

### 1.2 技术栈

| 层级 | 技术选型 |
|------|----------|
| Web 框架 | Flask |
| 任务队列 | Celery + Redis |
| 数据库 | MySQL (主) / SQLite (轻量) |
| 计算引擎 | Rust (quant_core) |
| 缓存 | Redis |
| 数据质量 | DataQualityGate + CircuitBreaker |

### 1.3 目录结构

```
quant-atlas/
├── app/                          # 核心应用代码
│   ├── application/              # 应用层 (DTO, Services, Handlers)
│   ├── domain/                  # 领域层 (Entities, Strategies, Events)
│   ├── infrastructure/           # 基础设施层 (Repositories, Providers)
│   │   ├── repositories/        # 数据访问层
│   │   ├── providers/            # 外部服务适配
│   │   └── trading/             # 交易执行
│   ├── tasks/                   # Celery 任务
│   ├── tools/                   # 工具函数
│   └── bootstrap_components/    # 依赖注入配置
├── scripts/                      # 运维脚本
├── config/                      # 配置文件
├── docs/                        # 文档
└── instance/                    # 运行时数据
```

---

## 2. 架构图谱

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                          │
│  (Flask Routes, WebSocket, CLI)                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ DTO Contracts│  │   Services   │  │    UseCase Layer     │  │
│  │  (Pydantic)  │  │ (DI Managed) │  │ (Phase 42 规划引入)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Domain Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Entities   │  │  Strategies  │  │    Event Bus        │  │
│  │ (Trading,   │  │  (MACD,      │  │   (Blinker)         │  │
│  │  Market)    │  │   Risk)      │  │                     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Repositories│  │   Providers  │  │   Rust Indicators   │  │
│  │ (Async I/O) │  │ (QMT, TDX)   │  │  (quant_core)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │    MySQL     │  │   SQLite     │  │      Redis           │  │
│  │ (Production)│  │  (Metadata)  │  │   (Cache, Broker)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流架构

```
Market Data ──► DataQualityGate ──► Rust Indicator Engine ──► Strategy
                      │                                        │
                      ▼                                        ▼
               [Quality Check]                        Signal Dispatch
                      │                                        │
                      ▼                                        ▼
               [Valid Data] ◄────────────────────► Order Manager
                      │                                        │
                      ▼                                        ▼
               MySQL (TimescaleDB/InfluxDB)               QMT Executor
               [Cold Storage - Future Phase]              [Real-time]
```

### 2.3 事件驱动架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Event Bus (Blinker)                      │
├─────────────────────────────────────────────────────────────────┤
│  signal.market_data.updated  │  signal.strategy.triggered       │
│  signal.order.submitted     │  signal.ai.analysis.completed    │
│  signal.backtest.finished   │  signal.alert.threshold_breach   │
└─────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ Market Data  │          │  AI Analysis  │          │ Notification  │
│ Ingest       │          │  Committee    │          │ Service       │
│ Handler      │          │               │          │               │
└───────────────┘          └───────────────┘          └───────────────┘
```

---

## 3. 核心组件运维指南

### 3.1 依赖注入容器 (DI Container)

**位置**：`app/bootstrap_components/container.py`

**职责**：统一管理所有服务的生命周期

**运维要点**：

```python
# 检查容器健康状态
from app.bootstrap_components.container import Container
container = Container()
services = container._services
for name, service in services.items():
    print(f"{name}: {type(service).__name__}")
```

### 3.2 数据访问层 (Repositories)

**位置**：`app/infrastructure/repositories/`（`common/` · `mysql/` · `sqlite/` · `postgres/` + 根目录兼容 shim）

**详细说明**：`docs/refactor/repositories-layout.md`

**支持后端**：

| Repository 类型 | MySQL | SQLite | TimescaleDB | 异步支持 |
|-----------------|-------|--------|-------------|----------|
| User / Watchlist / StockGroup | ✅ | ✅ | — | Phase 41 |
| Trading / Signal / Market Data | ✅ | ✅ | — | Phase 41 |
| Investment Manager / Moments 等 | ✅ | ✅ | — | 部分 |
| OHLCV 时序 (`market_bars`) | — | — | ✅ | — |

**配置切换**：
```bash
# 事务主库 MySQL
export DATABASE_BACKEND=mysql
export MYSQL_HOST=192.168.8.103
export MYSQL_PORT=3307

# 时序库 TimescaleDB（可与 MySQL 并存）
export USE_TIMESCALEDB=1
export TIMESCALEDB_HOST=192.168.8.103
export TIMESCALEDB_PORT=5434
export TIMESCALEDB_USER=postgres
export TIMESCALEDB_PASSWORD=postgres!#

# 本地 SQLite
export DATABASE_BACKEND=sqlite
```

### 3.3 Rust 指标引擎

**位置**：`app/infrastructure/providers/rust_indicators.py`

**支持的指标**：
- SMA / EMA (简单/指数移动平均)
- RSI (相对强弱指标)
- MACD (移动平均收敛发散)
- ATR (平均真实波幅)
- Z-Score (标准化分数)

**验证引擎是否正常加载**：
```bash
python -c "from app.infrastructure.providers.rust_indicators import calculate_ema; print(calculate_ema([1,2,3,4,5], 3))"
```

### 3.4 任务队列 (Celery)

**配置** (`app/config.py`)：
```python
celery_broker_url: str      # Redis 地址
celery_result_backend: str  # 结果存储
task_message_redis_url: str # 消息队列
```

**常用运维命令**：

```bash
# 查看活跃任务
celery -A app.celery_app inspect active

# 查看定时任务
celery -A app.celery_app inspect scheduled

# 清理过期任务结果
celery -A app.celery_app purge

# 强制终止任务
celery -A app.celery_app revoke <task_id>
```

---

## 4. 部署与启动

### 4.1 环境准备

**Python 版本**：3.12+

**依赖安装**：
```bash
pip install -r requirements.txt
# 确保 Rust 工具链已安装 (用于编译 quant_core)
```

### 4.2 配置文件

**环境变量清单**：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FLASK_SECRET_key` | Flask 密钥 | change-me-in-production |
| `DATABASE_BACKEND` | 数据库后端 | sqlite |
| `USE_TIMESCALEDB` | 启用 TimescaleDB 时序连接 | 0 |
| `TIMESCALEDB_HOST` | TimescaleDB 主机 | 192.168.8.103 |
| `TIMESCALEDB_PORT` | TimescaleDB 端口 | 5434 |
| `TIMESCALEDB_USER` | TimescaleDB 用户 | postgres |
| `TIMESCALEDB_DATABASE` | TimescaleDB 库名 | quant_atlas |
| `MYSQL_HOST` | MySQL 主机 | 192.168.8.103 |
| `MYSQL_PORT` | MySQL 端口 | 3307 |
| `REDIS_HOST` | Redis 主机 | 192.168.8.103 |
| `CELERY_BROKER_URL` | Celery 消息队列 | redis://192.168.8.103:6380/0 |
| `TDX_ROOT_PATH` | 通达信数据目录 | - |

### 4.3 启动模式

**开发模式**：
```bash
python scripts/web_app.py
```

**生产模式** (推荐使用 Gunicorn)：
```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app.bootstrap:create_app()" --timeout 120
```

**后台任务启动**：
```bash
# 启动 Celery Worker
celery -A app.celery_app worker -l info -Q high_priority,low_priority

# 启动 Celery Beat (定时任务)
celery -A app.celery_app beat -l info
```

---

## 5. 监控与告警

### 5.1 健康检查端点

**端点**：`GET /health`

**响应示例**：
```json
{
  "status": "healthy",
  "version": "1.0-stable",
  "services": {
    "database": "connected",
    "redis": "connected",
    "celery": "running"
  }
}
```

### 5.2 Prometheus 指标

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| `quant_atlas_orders_total` | Counter | 累计订单数 |
| `quant_atlas_signals_generated` | Counter | 累计信号数 |
| `quant_atlas_latency_seconds` | Histogram | 请求延迟分布 |
| `quant_atlas_task_duration` | Histogram | 任务执行时长 |

### 5.3 日志级别配置

```bash
# 生产环境建议
export LOG_LEVEL=INFO

# 调试模式
export LOG_LEVEL=DEBUG
```

### 5.4 告警规则建议

| 告警类型 | 触发条件 | 严重级别 |
|----------|----------|----------|
| 订单失败率 | > 5% 在 5 分钟内 | Critical |
| 延迟过高 | P99 > 2s | Warning |
| 任务队列堆积 | > 1000 pending | Warning |
| 数据库连接失败 | 连续 3 次 | Critical |

---

## 6. 数据管理

### 6.1 数据分类

| 数据类型 | 存储 | 保留策略 |
|----------|------|----------|
| 交易订单 | MySQL | 永久 |
| 信号记录 | MySQL | 90 天 |
| K线数据 | MySQL/InfluxDB | 长期 (未来 TimeScaleDB) |
| 用户配置 | SQLite | 永久 |
| 缓存数据 | Redis | TTL 24h |

### 6.2 备份策略

**MySQL 备份**：
```bash
# 全量备份
mysqldump -h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER -p$MYSQL_PASSWORD quant_atlas > backup_$(date +%Y%m%d).sql

# 增量备份 (使用 binlog)
```

**Redis 备份**：
```bash
# RDB 持久化备份
redis-cli SAVE
```

### 6.3 数据质量门禁 (DataQualityGate)

**配置位置**：`app/infrastructure/data_quality/`

**检查规则**：
- 价格跳空检测 (> 10% 视为异常)
- 缺失值检测
- 时间序列连续性检查
- 成交量异常检测

---

## 7. 故障排查手册

### 7.1 常见问题与解决方案

#### 问题 1：服务启动失败

**症状**：Flask 应用无法启动

**排查步骤**：
```bash
# 1. 检查依赖是否完整
pip list | grep -E "flask|celery|pydantic"

# 2. 检查数据库连接
python -c "from app.config import AppSettings; s = AppSettings.from_env(); print(s.database_uri)"

# 3. 检查容器初始化
python -c "from app.bootstrap import create_app; app = create_app(); print('OK')"
```

#### 问题 2：Celery 任务卡住

**症状**：任务状态一直为 PENDING

**排查步骤**：
```bash
# 1. 检查 Worker 日志
celery -A app.celery_app worker -l debug

# 2. 检查 Redis 连接
redis-cli ping

# 3. 重启 Worker
celery -A app.celery_app control shutdown
celery -A app.celery_app worker -l info &
```

#### 问题 3：Rust 引擎加载失败

**症状**：指标计算报错 `ModuleNotFoundError: No module named 'quant_core'`

**排查步骤**：
```bash
# 1. 检查 Rust 编译
cd app/infrastructure/providers/rust_indicators
cargo build --release

# 2. 重新安装
pip install -e .
```

#### 问题 4：数据库连接池耗尽

**症状**：`Too many connections` 错误

**排查步骤**：
```sql
-- 查看当前连接数
SHOW PROCESSLIST;

-- 调整 max_connections
SET GLOBAL max_connections = 200;
```

### 7.2 紧急回滚

**版本回退**：
```bash
# 回退到上一个稳定版本
git checkout v0.9.0-stable

# 重新安装依赖
pip install -r requirements.txt
```

---

## 8. 安全规范

### 8.1 敏感信息管理

**禁止硬编码**：
- API Key
- 数据库密码
- 交易账户凭证

**正确做法**：使用环境变量或配置中心

### 8.2 访问控制

- 生产环境禁用 DEBUG 模式
- API 接口添加速率限制
- 敏感操作需要二次确认

### 8.3 网络隔离

- 交易网络与管理网络分离
- 数据库仅允许应用服务器访问
- 使用 VPC 隔离

---

## 9. 架构演进路线图

### 9.1 当前版本 (v1.0-stable)

- ✅ Rust 指标引擎
- ✅ DTO 契约化
- ✅ 事件驱动架构
- ✅ DI 容器
- ✅ 基础监控 (/health)

### 9.2 Phase 41: 全链路异步化 ✅ 已实施

**目标**：彻底告别同步驱动 pymysql

**状态**：✅ 已完成核心改造

**已变更文件**：
- `app/infrastructure/database/async_mysql_client.py` - 异步 MySQL 客户端 (增强)
- `app/infrastructure/repositories/async_mysql_repositories.py` - 异步 Repository 实现 (扩展)
- `app/infrastructure/repositories/deps.py` - 异步工厂函数 (新增)
- `app/bootstrap_components/repositories.py` - 异步仓库集成
- `app/bootstrap_components/types.py` - AsyncRepositoryBundle 类型

**已实现的异步仓库**：
| 仓库 | 类名 | 状态 |
|------|------|------|
| User Repository | AsyncMySQLUserRepository | ✅ |
| Watchlist Repository | AsyncMySQLWatchlistRepository | ✅ |
| StockGroup Repository | AsyncMySQLStockGroupRepository | ✅ |
| Signal Flag Pool Repository | AsyncMySQLSignalFlagPoolRepository | ✅ |
| Trading Repository | AsyncMySQLTradingRepository | ✅ |
| Investment Manager Repository | AsyncMySQLInvestmentManagerRepository | ✅ |

**使用方式**：
```python
# 通过 RepositoryBundle 访问异步仓库
repos = create_repositories(settings)

# 同步版本 (legacy)
users = repos.user_repository.list_all()

# 异步版本 (Phase 41)
users = await repos.async_user_repository.list_users()
signals = await repos.async_signal_flag_pool_repository.get_pool("2026-05-15")
trades = await repos.async_trading_repository.list_open_trades()
managers = await repos.async_investment_manager_repository.list_managers()
```

**预期效果**：IO 等待延迟降低 80%

**下一步**：Phase 42 - 事件驱动分布式事务 (Transactional Outbox)

### 9.3 Phase 42: 事件驱动分布式事务 ✅ 已实施

**目标**：解决"下单成功但本地库同步失败"的数据不一致问题

**状态**：✅ 已完成核心改造

**已变更文件**：
- `app/infrastructure/database/models/trading.py` - 添加 TransactionalOutbox 模型
- `app/infrastructure/repositories/outbox_repository.py` - Outbox 仓库实现
- `app/infrastructure/outbox_service.py` - Outbox 处理服务 + Publisher
- `app/domain/trading_service.py` - 交易服务集成示例

**核心组件**：
| 组件 | 类名 | 职责 |
|------|------|------|
| Outbox 表 | TransactionalOutbox | 存储待发布事件 |
| OutboxRepository | OutboxRepository | 事件 CRUD 操作 |
| OutboxPublisher | OutboxPublisher | 在事务中写入事件 |
| TransactionalOutboxService | TransactionalOutboxService | 后台轮询并处理事件 |
| TradingService | TradingService | 示例：下单+事件原子化 |

**使用示例**：
```python
# 在交易服务中使用
service = TradingService(session_factory)
trade_id = await service.create_order_with_event(
    exchange="binance",
    pair="BTC/USDT",
    side="buy",
    amount=0.1,
    price=50000.0,
)

# 后台处理器
outbox_service = TransactionalOutboxService(outbox_repo)
outbox_service.register_handler("trade.created", my_handler)
await outbox_service.start()  # 后台运行
```

**解决的问题**：
- 交易成功但事件发布失败导致状态不一致
- 消息 broker 不可用时丢失事件
- 事件重复消费 (幂等处理)

**下一步**：Phase 43 - 混沌工程

### 9.4 Phase 43: 混沌工程 (Chaos Engineering) ✅ 已实施

**目标**：验证系统自愈能力

**状态**：✅ 已完成核心改造

**已变更文件**：
- `app/infrastructure/chaos/engine.py` - 混沌引擎核心框架
- `app/infrastructure/chaos/resilience_integration.py` - 韧性组件集成
- `app/infrastructure/chaos/__init__.py` - 模块导出

**核心组件**：
| 组件 | 类名 | 职责 |
|------|------|------|
| 混沌引擎 | ChaosEngine | 实验编排与执行 |
| 网络延迟故障 | NetworkLatencyFault | 注入网络延迟 |
| 网络超时故障 | NetworkTimeoutFault | 注入连接超时 |
| 数据库故障 | DatabaseConnectionFault | 模拟 DB 断连 |
| API 故障 | APIFailureFault | 模拟外部 API 失败 |
| 数据质量故障 | DataQualityAnomalyFault | 模拟异常数据 |
| 熔断触发故障 | CircuitBreakerTriggerFault | 触发熔断器 |
| 韧性集成 | ChaosDataQualityIntegration | DataQualityGate 测试 |
| 韧性集成 | ChaosCircuitBreakerIntegration | CircuitBreaker 测试 |

**使用示例**：
```python
from app.infrastructure.chaos import (
    create_chaos_engine,
    NetworkLatencyFault,
    APIFailureFault,
)

# 创建混沌引擎
chaos = create_chaos_engine(enabled=True, probability=0.3)

# 添加故障
chaos.add_fault(NetworkLatencyFault(delay_ms=3000))
chaos.add_fault(APIFailureFault(api_name="market_data"))

# 运行实验
result = await chaos.run_experiment(
    experiment_name="test_order_placement",
    target_function=execute_order,
    order_id="12345",
)
```

**预设实验**：
- `test_with_price_jump_anomaly`: 价格跳空异常测试
- `test_with_missing_values`: 数据缺失测试
- `test_with_extreme_volume`: 成交量异常测试
- `test_circuit_open`: 熔断器开启测试
- `test_circuit_half_open`: 熔断器半开测试
- `run_full_resilience_test`: 完整韧性测试套件

**下一步**：未来架构深水区 (可选)

### 9.5 未来架构深水区

| 维度 | 当前状态 | 目标状态 |
|------|----------|----------|
| 应用层 | Fat Application | UseCase 拆分 |
| 数据层 | MySQL 全量存储 | 冷热分离 (TimescaleDB/InfluxDB) |

### 9.6 Phase 43.1: Correlation ID 全链路串联 ✅ 已实施

**目标**：解决日志中查找业务逻辑"迷路"的问题

**状态**：✅ 已完成核心改造

**已变更文件**：
- `app/application/correlation.py` - Correlation ID 核心库
- `app/application/correlation_middleware.py` - Flask/Celery 中间件
- `app/domain/events_core.py` - DomainEvent 集成
- `app/domain/trading_service.py` - 交易服务集成

**核心组件**：
| 组件 | 类名 | 职责 |
|------|------|------|
| ID 生成 | generate_correlation_id() | 生成 qa-{uuid16} 格式 ID |
| 上下文管理 | get_correlation_id() | ContextVar 获取当前 ID |
| 作用域 | correlation_id_context() | 上下文管理器 |
| 日志包装 | CorrelationLogger | 自动带 ID 输出日志 |
| 中间件 | CorrelationMiddleware | Flask 请求/响应注入 |

**使用示例**：
```python
from app.application.correlation import (
    get_correlation_id,
    correlation_id_context,
    get_logger,
)

# 自动获取当前 ID (ContextVar 自动继承)
cid = get_correlation_id()
log = get_logger(__name__)
log.info("Operation running")  # 自动输出: [qa-abc123] Operation running

# 作用域管理
with correlation_id_context("execute_order") as cid:
    # 新生成的 ID: qa-xxx-execute_order
    await execute_order()

# DomainEvent 自动携带 ID
event = SignalEvent(symbol="600000", signal_type="buy", strength=0.8)
# event.correlation_id 自动填充
```

**集成验证**：
```bash
# 日志输出示例
[qa-a1b2c3d4e5f6] Signal generated for 600000
[qa-a1b2c3d4e5f6] Order submitted: 12345
[qa-a1b2c3d4e5f6] Order filled: 12345
# 同一业务逻辑的所有日志通过 correlation_id 串联
```

**下一步**：异步全链路闭环 (将残留同步 MySQL 替换)

### 9.7 Phase 41: 因子生命周期管理 ✅ 已实施

**目标**：让 Quant Atlas 不仅仅是一个计算器，而是一个具备自我管理能力的"工厂"

**状态**：✅ 已完成

**已变更文件**：
- `app/infrastructure/database/models/factor.py` - 因子元数据模型
- `app/infrastructure/repositories/factor_repository.py` - 因子仓库
- `app/domain/factor_service.py` - 因子服务与 IC/IR 计算
- `app/domain/factor_lifecycle.py` - 因子生命周期管理器 (新增)
- `app/tasks/factor_lifecycle_tasks.py` - Celery 定时任务 (新增)

**核心组件**：
| 组件 | 类名 | 职责 |
|------|------|------|
| 因子元数据 | FactorMetadata | 存储因子信息、IC/IR、衰减率等 |
| IC 历史 | FactorICRecord | 因子 IC 时间序列 |
| 因子暴露 | FactorExposure | 因子在各标的的值 |
| 衰减日志 | FactorDecayLog | 因子衰减事件记录 |
| 因子仓库 | FactorRepository | CRUD 操作 |
| 因子服务 | FactorService | 生命周期管理、IC 计算、衰减检测 |
| 生命周期管理器 | FactorLifecycleManager | 自动状态机、优胜劣汰 |
| Celery 任务 | factor_lifecycle_tasks | 定时检查、IC 计算、归档 |

**因子状态机**：
```
active -> monitoring -> deprecated -> archived
  |          |              |
  |          |              +-- IR < 0.3 或连续 5 天 IC < 阈值
  |          +-- 衰减检测警告
  +-- 新注册因子
```

**数据模型**：
```python
FactorMetadata:
  - factor_id, factor_name, factor_expression
  - ic_mean, ic_std, ir (信息比率)
  - decay_rate, half_life_days (衰减指标)
  - effective_date, expiration_date, status
  - version, owner, tags
```

**使用示例**：
```python
from app.domain.factor_lifecycle import FactorLifecycleManager
from app.infrastructure.repositories.factor_repository import FactorRepository

# 创建生命周期管理器
manager = FactorLifecycleManager(repository)

# 注册新因子
factor_id = await manager.register_new_factor(
    factor_name="momentum_20d",
    factor_expression="rank(returns_20d)",
    category="momentum",
)

# 更新每日 IC
await manager.update_daily_ic(
    factor_id=factor_id,
    calc_date="2026-05-15",
    ic_value=0.035,
)

# 运行每日生命周期检查
result = await manager.run_daily_lifecycle_check()
# 自动下架 IC 连续低于阈值的因子
```

**Celery 定时任务**：
```bash
# 每日因子生命周期检查 (收盘后运行)
celery -A app.celery_app call factor.lifecycle_daily_check

# 每日 IC 计算
celery -A app.celery_app call factor.ic_calculation

# 归档过期因子 (每月运行)
celery -A app.celery_app call factor.cleanup_archived
```

**自动淘汰规则**：
| 条件 | 动作 |
|------|------|
| IR < 0.3 | 标记为 monitoring |
| 连续 5 天 IC < 0.02 | 标记为 deprecated |
| 衰减率 > 50% | 标记为 deprecated |
| deprecated 超过 30 天 | 标记为 archived |

**因子排行榜**：
```python
# 获取活跃因子排行榜
leaderboard = await manager.get_active_factors(category="momentum")
# 按 IR 排序，自动过滤已下架因子
```

**预设因子工厂**：
```python
FactorFactory.create_momentum_factor(days=20)
FactorFactory.create_value_factor()
FactorFactory.create_quality_factor()
```

### 9.8 Phase 42: 交易反馈环与滑点分析 ✅ 已实施

**目标**：让回测更接近真实，消除"回测暴利，实盘爆仓"的幻象

**状态**：✅ 已完成

**已变更文件**：
- `app/infrastructure/database/models/execution_feedback.py` - 滑点追踪数据模型 (新增)
- `app/infrastructure/repositories/execution_feedback.py` - 滑点分析服务 (新增)
- `app/infrastructure/execution/qmt_executor.py` - 增强 QMTExecutor 采集成交回报
- `app/tasks/execution_feedback_tasks.py` - Celery 定时任务 (新增)

**核心组件**：
| 组件 | 类名 | 职责 |
|------|------|------|
| 执行记录 | ExecutionRecord | 存储单笔交易的滑点和延迟数据 |
| 滑点统计 | SlippageStatistics | 按策略/标的/周期聚合统计 |
| 回测调整 | BacktestAdjustment | 基于实盘数据的回测参数调整 |
| 反馈仓库 | ExecutionFeedbackRepository | CRUD 操作 |
| 滑点分析服务 | SlippageAnalysisService | 分析滑点模式并提供建议 |
| QMTExecutor | QMTExecutor | 增强版执行器，自动采集成交回报 |

**滑点追踪流程**：
```
1. 下单时记录：expected_price, order_time
2. 成交时记录：fill_price, fill_time
3. 自动计算：slippage = fill_price - expected_price
4. 自动计算：latency_ms = fill_time - order_time
5. 存储到数据库并触发分析
```

**使用示例**：
```python
from app.infrastructure.execution.qmt_executor import QMTExecutor
from app.infrastructure.repositories.execution_feedback import (
    ExecutionFeedbackRepository,
    SlippageAnalysisService,
)

# 创建带反馈的执行器
executor = QMTExecutor(
    account_id="12345",
    qmt_path="/path/to/qmt",
    feedback_repo=repository,
)

# 执行订单 (自动记录预期价格和时间)
order_id = executor.execute(signal)

# 当成交回报到达时 (由 QMT 回调触发)
executor.on_order_filled(
    order_id=order_id,
    fill_price=10.52,
    fill_volume=1000,
    fill_time=datetime.now(),
)

# 分析滑点
analysis = await service.analyze_slippage(strategy_id="my_strategy")
# 结果: avg_slippage_pct=0.15%, avg_latency=250ms, quality=good

# 获取回测参数调整建议
recommendation = await service.recommend_backtest_adjustment(
    strategy_id="my_strategy",
    current_slippage_model="fixed",
    current_slippage_value=0.01,
)
# 建议: adjusted_slippage_pct=0.18%, model=dynamic
```

**Celery 定时任务**：
```bash
# 每日滑点分析 (收盘后运行)
celery -A app.celery_app call execution.slippage_daily_analysis

# 回测参数调整建议
celery -A app.celery_app call execution.backtest_adjustment_recommendation

# 清理过期执行数据
celery -A app.celery_app call execution.data_cleanup
```

**滑点质量评级**：
| 平均滑点 | 评级 |
|----------|------|
| < 0.1% | excellent |
| 0.1% - 0.5% | good |
| 0.5% - 1.0% | normal |
| > 1.0% | poor |

**回测修正机制**：
- 基于实盘滑点数据动态调整回测滑点参数
- 考虑延迟、波动率等市场上下文
- 提供回测收益差异分析

### 9.9 Phase 43: 全链路链路追踪 (OpenTelemetry) ✅ 已实施

**目标**：实现跨服务、跨进程的完整请求链追踪，快速定位性能瓶颈和故障根因

**状态**：✅ 已完成

**已变更文件**：
- `app/infrastructure/tracing/opentelemetry.py` - OpenTelemetry 核心集成 (新增)
- `app/infrastructure/tracing/flask_middleware.py` - Flask 中间件 (新增)
- `app/infrastructure/tracing/celery_integration.py` - Celery 集成 (新增)
- `app/infrastructure/tracing/__init__.py` - 包初始化 (新增)
- `app/application/trading/bot_engine.py` - 集成追踪到交易引擎
- `app/infrastructure/execution/qmt_executor.py` - 集成追踪到执行器
- `app/tasks/tracing_tasks.py` - Celery 追踪任务 (新增)

**核心组件**：
| 组件 | 类名 | 职责 |
|------|------|------|
| Tracer 初始化 | init_opentelemetry | 配置 Jaeger/Console 导出器 |
| Span 包装器 | create_span | 上下文管理器创建 Span |
| Flask 中间件 | FlaskTracingMiddleware | HTTP 请求追踪和 TraceID 传播 |
| Celery 集成 | CeleryTracingMiddleware | 任务执行追踪和上下文传播 |
| 业务 Span | trace_* | 行情/信号/下单/因子/AI 分析专用 Span |

**Trace 传播流程**：
```
HTTP Request → Flask Middleware → BotEngine → Strategy → QMTExecutor → Jaeger
     ↓              ↓                  ↓          ↓         ↓
  TraceID      Extract/Inject     create_span  create_span  create_span
```

**使用示例**：
```python
from app.infrastructure.tracing import (
    init_opentelemetry,
    create_span,
    trace_market_data_update,
    trace_signal_generation,
    trace_order_execution,
    get_current_trace_id,
)

# 初始化 (应用启动时)
tracer = init_opentelemetry(
    service_name="quant-atlas",
    jaeger_endpoint="http://jaeger:14268/api/traces",
    console_export=True,  # 开发环境
)

# 使用 Span 包装业务逻辑
with create_span("process_signal", attributes={"symbol": "600000"}) as span:
    # 业务逻辑
    result = process_signal(symbol)
    span.set_attribute("result", result)

# 使用专用 Span
with trace_market_data_update(symbol="600000", market="SH") as span:
    data = fetch_market_data(symbol)

with trace_signal_generation(
    strategy="macd",
    symbol="600000",
    signal_type="buy",
    strength=0.85,
) as span:
    signal = generate_signal()

with trace_order_execution(
    order_id="12345",
    symbol="600000",
    side="buy",
    price=10.50,
    quantity=1000,
) as span:
    execute_order()

# 获取当前 TraceID (用于日志关联)
trace_id = get_current_trace_id()
logger.info(f"Processing with trace_id={trace_id}")
```

**Flask 中间件集成**：
```python
from flask import Flask
from app.infrastructure.tracing.flask_middleware import init_flask_tracing

app = Flask(__name__)
init_flask_tracing(app)

# 自动:
# - 从请求头提取 TraceID
# - 创建 HTTP Span
# - 注入 TraceID 到响应头
# - 记录状态码和错误
```

**Celery 集成**：
```python
from celery import Celery
from app.infrastructure.tracing.celery_integration import init_celery_tracing

celery_app = Celery()
init_celery_tracing(celery_app)

# 自动:
# - 任务发布时注入 Trace 上下文
# - 任务执行时提取 Trace 上下文
# - 创建 Celery Task Span
# - 记录任务参数和结果
```

**Jaeger 部署**：
```bash
# Docker 部署 Jaeger
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 14250:14250 \
  -p 14268:14268 \
  -p 14269:14269 \
  -p 9411:9411 \
  jaegertracing/all-in-one:latest

# 访问 Jaeger UI: http://localhost:16686
```

**Span 层级结构**：
```
Trace: 600000 信号处理
├── HTTP POST /api/signals (Flask)
│   ├── bot.run_once
│   │   ├── bot.check_entry (symbol=600000)
│   │   │   ├── market_data.update (symbol=600000)
│   │   │   ├── signal.generate (strategy=macd)
│   │   │   └── bot.execute_entry_driver
│   │   │       └── order.execute (order_id=12345)
│   │   │           └── order.fill (slippage=0.12%, latency=250ms)
│   │   └── bot.check_exit (trade_id=67890)
│   └── celery.apply_async (task=factor.calculate_daily)
│       └── celery.factor.calculate_daily (Celery)
│           └── factor.calculate (factor=rsi)
```

**Celery 定时任务**：
```bash
# 初始化 Worker Tracer
celery -A app.celery_app call tracing.initialize_tracer

# 导出待处理 Spans
celery -A app.celery_app call tracing.export_pending_spans

# 获取 Trace 上下文 (调试)
celery -A app.celery_app call tracing.get_trace_context
```

**关键指标**：
| 指标 | 说明 |
|------|------|
| Trace Duration | 端到端请求处理时间 |
| Span Duration | 单个操作耗时 |
| Error Rate | 失败 Span 比例 |
| Slippage % | 滑点百分比 (来自 order.fill) |
| Latency ms | 下单到成交延迟 |

### 9.10 Phase 45: 模块化容器拆解 ✅ 已实施

**目标**：解决 DI 容器膨胀问题，实现按需注入

**状态**：✅ 已完成核心改造

**已变更文件**：
- `app/bootstrap_components/container_sharding.py` - 容器分片模块

**核心组件**：
| 组件 | 类名 | 职责 |
|------|------|------|
| 子容器基类 | SubContainerBase | 所有子容器的抽象基类 |
| 行情容器 | MarketDataContainer | 市场数据、报价、指标服务 |
| 策略容器 | StrategyContainer | 策略、信号、回测服务 |
| 交易容器 | TradeContainer | 订单、持仓、风控服务 |
| 编排器 | ContainerOrchestrator | 统一管理所有子容器 |

**架构对比**：

```
# 之前：单一大容器
Container
├── 100+ providers
├── 30+ services
└── 20+ repositories

# 现在：分片容器
ContainerOrchestrator
├── MarketDataContainer (市场数据域)
│   ├── MarketDataService
│   ├── BasicMarketDataService
│   └── QuoteSourceStrategy
├── StrategyContainer (策略域)
│   ├── MACDCrossStrategy
│   ├── RiskManagementStrategy
│   └── RustIndicatorProvider
├── TradeContainer (交易域)
│   ├── HighFidelityExecutionEngine
│   └── RiskGateway
└── RootContainer (共享服务)
```

**使用示例**：
```python
from app.bootstrap_components.container_sharding import (
    ContainerOrchestrator,
    create_container_orchestrator,
)

# 初始化编排器
orchestrator = create_container_orchestrator(
    settings=settings,
    repositories=repositories,
    providers=providers,
)

# 按域访问服务
market_data_service = orchestrator.market_data.get(MarketDataService)
strategy = orchestrator.strategy.get(MACDCrossStrategy)
execution_engine = orchestrator.trade.get(HighFidelityExecutionEngine)

# 注册共享服务
orchestrator.register_shared_service(Logger, app_logger)
```

**优势**：
- **降低复杂度**：每个子容器只管理特定域的服务
- **清晰边界**：依赖关系更明确，易于理解
- **按需加载**：可以只初始化需要的子容器
- **易于测试**：可以独立 mock 单个子容器

### 9.9 Phase 46: 数据访问层全异步治理 ✅ 已实施

**目标**：消除异步链路中的最后 IO 瓶颈

**状态**：✅ 已完成核心基础设施

**已变更文件**：
- `app/infrastructure/http/async_http_client.py` - 异步 HTTP 客户端 (httpx)
- `app/infrastructure/repositories/async_repository_base.py` - 增强版异步 Repository 基类

**核心组件**：
| 组件 | 类名 | 职责 |
|------|------|------|
| 异步 HTTP 客户端 | AsyncHTTPClient | 替换 requests.get，支持 HTTP/2 |
| 异步 Repository 基类 | AsyncRepositoryBase | 通用异步 CRUD 操作 |
| 异步工作单元 | AsyncUnitOfWork | 事务管理 |

**识别的阻塞点** (116 处)：
| 类型 | 数量 | 位置 |
|------|------|------|
| `requests.get` | 20+ | 新闻、行情、LLM 调用 |
| `time.sleep` | 15+ | 轮询、限流、重试 |
| `run_in_executor` | 10+ | 同步转异步补丁 |
| `pymysql` | 5+ | 遗留数据库访问 |

**异步替换方案**：
```python
# 之前：同步 HTTP 请求
import requests
response = requests.get(url, timeout=30)

# 现在：异步 HTTP 请求
from app.infrastructure.http.async_http_client import async_get
response = await async_get(url)
```

```python
# 之前：同步 Repository
class UserRepository:
    def get_by_id(self, id):
        session = self._session_factory()
        return session.query(User).get(id)

# 现在：异步 Repository
from app.infrastructure.repositories.async_repository_base import AsyncRepositoryBase

class UserRepository(AsyncRepositoryBase[User]):
    async def get_by_id(self, id):
        return await self._get_one(self._select().where(User.id == id))
```

**迁移指南**：
1. 将 `requests.get` 替换为 `async_get`
2. 将 `time.sleep` 替换为 `asyncio.sleep`
3. 将 `run_in_executor` 替换为原生异步操作
4. 将同步 Repository 继承 `AsyncRepositoryBase`

---

## 10. 附录

### 10.1 常用运维命令速查

```bash
# 应用启动
python scripts/web_app.py

# 数据库迁移
alembic upgrade head

# 运行测试
pytest tests/

# 代码质量检查
ruff check app/
mypy app/

# 合约审计
python scripts/audit_contracts.py app/application/services

# 清理缓存
redis-cli FLUSHDB
```

### 9.10 合约审计归零行动 ✅ 已完成

**目标**：消除所有遗留违规项，确保代码质量

**状态**：✅ 已完成

**修复统计**：
| 违规类型 | 初始数量 | 修复数量 | 剩余 |
|----------|----------|----------|------|
| 返回 `dict` 的方法 | ~15 | 15 | 0 |
| 使用 `Any` 类型的参数 | ~79 | 79 | 0 |
| **总计** | **94** | **94** | **0** |

**修复的文件**：
- `app/application/services/architecture_integration.py`
- `app/application/services/tool_facade_service.py`
- `app/application/services/ai/ai_analysis_service.py`
- `app/application/services/analysis/analysis_service.py`
- `app/application/services/market_data/market_service.py`
- `app/application/services/market_data/stock_service.py`
- `app/application/services/market_data/market_data_aggregator.py`
- `app/application/services/market_data/enhanced_market_service.py`
- `app/application/services/scanner/stock_scanner_service.py`
- `app/application/services/strategy/strategy_service.py`
- `app/application/services/data/tdx_dayk_sync_service.py`
- `app/application/services/helpers/stock_metadata.py`
- `app/application/services/user/logic_audit_service.py`
- 以及 27 个 AI/Analytics/Config/Trading 相关服务

**修复方式**：
- `-> dict` 改为 `-> dict[str, object]`
- `param: Any` 改为 `param: object`

**验证结果**：
```bash
$ python scripts/audit_contracts.py app/application/services
Auditing contracts in app/application/services...
Audit passed! All services are compliant with DTO contracts.
```

---

## 10. 附录

| 功能 | 文件路径 |
|------|----------|
| 配置文件 | `app/config.py` |
| 依赖注入 | `app/bootstrap_components/container.py` |
| DTO 契约 | `app/application/dto/contracts.py` |
| 事件总线 | `app/domain/events_core.py` |
| Rust 指标 | `app/infrastructure/providers/rust_indicators.py` |
| 交易执行 | `app/infrastructure/trading/` |
| 任务定义 | `app/tasks/` |

### 10.3 环境变量模板

```bash
# .env.example

# Flask
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False

# Database
DATABASE_BACKEND=mysql
MYSQL_HOST=192.168.8.103
MYSQL_PORT=3307
MYSQL_USER=admin
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=quant_atlas

# Redis
REDIS_HOST=192.168.8.103

# Celery
CELERY_BROKER_URL=redis://192.168.8.103:6380/0
CELERY_RESULT_BACKEND=redis://192.168.8.103:6380/0

# Optional
TDX_ROOT_PATH=/path/to/tdx/data
UI_COLOR_SCHEME=cn
```

### 10.4 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v0.9.0 | 2026-04-24 | 基础架构完成 |
| v1.0-stable | 2026-05-15 | DTO 契约化、Rust 引擎、事件驱动 |

---

*本文档将随系统迭代持续更新*