# 分层边界门禁

## 规则（pytest：`tests/test_layer_boundaries.py`）

| 层级 | 禁止 import |
|------|-------------|
| `app/application/**` | `infrastructure.database.models`（ORM） |
| `app/application/**` | `infrastructure.database.db_manager` |
| `app/application/**` | `infrastructure.database.stock_cache_db` |
| `app/application/**` | `infrastructure.database.mysql_client` |
| `app/application/**` | `infrastructure.database.mappers` |

| `app/application/**` | `infrastructure.repositories.basic_market_data_repository` |
| `app/application/**` | `infrastructure.repositories.news_archive_repository` |
| `app/application/**` | `infrastructure.repositories.analysis_report_repository` |
| `app/application/**` | `infrastructure.repositories.mysql.mysql_signal_observation_repository` |

| `app/application/**` | `infrastructure.repositories.deps` |
| `app/application/**` | `infrastructure.mappers.symbol_normalizer` |
| `app/application/**` | `infrastructure.providers.market_data` |
| `app/application/**` | `infrastructure.tdx_local` |
| `app/application/**` | `infrastructure.pytdx` |
| `app/application/**` | `infrastructure.providers.tdx_file_adapter` |
| `app/application/**` | `infrastructure.providers`（全部子模块） |
| `app/application/**` | `infrastructure.cache.quote_cache` |
| `app/application/**` | `infrastructure.mappers.longhu_mapper` |
| `app/application/**` | `infrastructure.parsers.eastmoney_parser` |
| `app/application/**` | `infrastructure.agent.data.quality_checker` |
| `app/application/**` | `infrastructure.adapters.market_ingestion.longhu_adapter` |
| `app/application/**` | `infrastructure.config_loader.loader` |
| `app/application/**` | `infrastructure.qlib` |
| `app/application/**` | `infrastructure.rdagent` |
| `app/application/**` | `infrastructure.trading.pre_trade_validator` |
| `app/application/**` | `infrastructure.risk.risk_gateway` |
| `app/application/**` | `infrastructure.di.container` |
| `app/application/**` | `infrastructure.external.tdx_finance` |
| `app/application/**` | `infrastructure.execution` |
| `app/application/**` | `infrastructure.tracing` |
| `app/application/**` | `infrastructure.agent` |
| `app/application/**` | `infrastructure.events` |
| `app/application/**` | `infrastructure.messaging` |
| `app/application/**` | `infrastructure.task_pipeline` |
| `app/application/**` | `infrastructure.memory` |
| `app/application/**` | `infrastructure.portfolio` |
| `app/application/**` | `infrastructure.strategy` |
| `app/application/**` | `infrastructure.data_quality` |
| `app/application/**` | `infrastructure.adapters`（除 bootstrap 工厂外） |

应用层应依赖：

- `app.domain.*` — Port 与领域共享工具（含 `EastmoneyParser`）
- `app.application.services.helpers.quote_cache_access` — Redis 行情缓存 Port
- `app.application.services.helpers.longhu_mapping_access` — 龙虎榜 DataFrame 映射
- `app.application.services.helpers.market_data_ingestor_access` — 龙虎榜 ingestor 工厂
- `app.application.services.helpers.config_loader_access` — 动态配置加载
- `app.application.services.helpers.qlib_access` — Qlib 数据适配 / bin dumper / task service
- `app.application.services.helpers.rdagent_access` — RD-Agent job store / artifact registry / 提交校验
- `app.application.services.helpers.trading_risk_access` — 预交易校验 / 风控 preflight / 仓位 sizing
- `app.application.services.helpers.service_resolver_access` — 可选 DI 服务解析（bootstrap 绑定 infra container）
- `app.application.services.helpers.tdx_finance_access` — TDX 在线财务快照
- `app.application.services.helpers.tracing_access` — OpenTelemetry span 创建
- `app.application.services.helpers.events_access` — 事件存储 / 集成事件 emit
- `app.application.services.helpers.task_message_access` — Celery 任务消息存储
- `app.application.services.helpers.agent_access` — Swarm 编排 / 实验仓储 / runtime 工厂
- `app.application.services.helpers.task_pipeline_access` — DAG 任务管道 tracker / observer
- `app.application.services.helpers.memory_access` — Arrow 共享内存管理器
- `app.application.services.helpers.strategy_access` — Walk-forward 优化器工厂
- `app.application.services.helpers.portfolio_access` — 组合优化 / 归因分析工厂
- `app.application.services.helpers.data_infrastructure_access` — 数据质量监控 / 血缘追踪
- `app.application.services.helpers.ai_adapter_access` — AI 分析 adapter 工厂
- `app.application.services.helpers.research_access` — TradingAgents 研究 Port 工厂
- `app.domain.execution.driver_protocol` — 执行驱动请求/响应类型与 `ExecutionGateway` 协议
- `app.application.services.data.mysql_access` — bootstrap 绑定的 MySQL 连接入口
- `app.application.services.helpers.market_data_provider` — 行情 Provider
- `app.application.services.helpers.tdx_local_access` — TDX 本地文件 Port
- `app.application.services.helpers.pytdx_access` — Pytdx Port
- `app.application.services.helpers.cn_fundamentals_access` — A 股基本面 Port
- `app.application.services.helpers.cn_sector_board_access` — 板块数据 Port
- `app.application.services.helpers.news_provider_access` — 新闻 Provider
- `app.application.services.helpers.async_market_access` — 异步行情包装
- `app.application.services.helpers.strategy_providers_access` — 策略/回测 Provider 工厂
- `app.application.services.helpers.backtest_engine_access` — 回测引擎工厂
- 注入的 Repository / Service — 由 `bootstrap_components` + `infrastructure.repositories.deps` 装配

## 本地检查

```bash
python -m pytest tests/test_layer_boundaries.py -q
```

## 基础设施工厂（`infrastructure/repositories/common/deps.py`，根目录 `deps.py` 为 shim）

- `create_stock_cache()` — 本地行情缓存单例
- `create_stock_metadata_repository(settings)` — `base_stock_reference` 元数据
- `create_mysql_connection_port(settings)` — MySQL 连接 / schema 保障
- `create_postgres_connection_port(settings)` — TimescaleDB 连接（`USE_TIMESCALEDB=1`）
- `create_timescale_bar_repository(settings)` — OHLCV 时序 hypertable `market_bars`
- `create_tdx_gpcw_repository(settings)` — TDX 专业财务（gpcw）只读访问
- `create_basic_market_data_repository(settings)` — 龙虎榜 / 研报 / 财报快照
- `create_news_archive_repository(settings)` — 新闻归档
- `create_signal_flag_pool_repository(settings)` — 信号旗扫描池
- `create_investment_manager_repository(settings)` — 投资经理子系统
- `create_moments_repository(settings)` — 动态圈
- `create_analysis_report_repository(settings)` — AI 分析报告
- `create_signal_observation_repository(session_factory)` — 信号观察单（MySQL）
- `create_default_qlib_pipeline_service()` — Celery/脚本/Bootstrap 用 Qlib 管道（**仅 bootstrap/tasks 调用，application 禁止 import deps**）

## Repositories 目录（阶段 10）

详见 [`repositories-layout.md`](repositories-layout.md)：`common/`（factory、deps、facades）、`mysql/`、`sqlite/`、`postgres/`；根目录 shim 保留旧 import 路径。

## 阶段 8 收尾

application 层 `infrastructure.*` 模块级直连已通过 helper + bootstrap 绑定清零；后续新能力须先定义 Port / helper，禁止在 `app/application/**` 新增 infra import。

## 版本控制

项目使用 **SVN**（非 Git）。变更记录见根目录 `REFACTORING_LOG.md`。
