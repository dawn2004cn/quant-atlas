# Refactoring Log

## 2026-04-25 (Architecture Refactoring - HIGH Priority)

### TODO-004: Complete Dependency Injection in Application Services

**Problem**: Application services use inline imports for infrastructure dependencies, violating dependency inversion principle.

**Changes**:
- Added `IndustryProvider` port interface to `domain/ports/market_ports.py`
- Implemented `CnIndustryProvider` in `infrastructure/providers/cn_industry_provider.py`
- Updated `MarketApplicationService` constructor to accept `IndustryProvider`
- Added `industry_provider` to `ProviderBundle` and `create_providers()`
- Updated `bootstrap_components/services.py` to inject `industry_provider`

**Files Modified**:
- `app/domain/ports/market_ports.py` - added IndustryProvider
- `app/domain/ports/__init__.py` - exported IndustryProvider
- `app/domain/ports.py` - backward compatibility export
- `app/infrastructure/providers/cn_industry_provider.py` - new implementation
- `app/application/services/market_service.py` - uses injected IndustryProvider
- `app/bootstrap_components/providers.py` - creates CnIndustryProvider
- `app/bootstrap_components/types.py` - added industry_provider to ProviderBundle
- `app/bootstrap_components/services.py` - injects industry_provider

**Tests**: 5 passed ✅

### TODO-005: Split Fat MarketDataProvider Interface (ISP)

**Problem**: Single interface with 6 data methods violated Interface Segregation Principle.

**Changes**:
- Split `MarketDataProvider` into focused interfaces:
  - `MarketOverviewPort` - market overview and rankings
  - `QuotePort` - real-time quotes and stock profiles
  - `HistoryPort` - historical OHLCV data
  - `ChipDataPort` - chip distribution data
- Made `MarketDataProvider` inherit from all four interfaces (composite pattern)

**Files Modified**:
- `app/domain/ports/market_ports.py` - split into focused interfaces
- `app/domain/ports/__init__.py` - exported new interfaces
- `app/domain/ports.py` - backward compatibility

**Tests**: 5 passed ✅

## 2026-04-25 (Continued)

- **清理遗留废弃导入**：修复 `infrastructure/qlib/data_adapter.py` 中对 `services.data` 的导入，统一使用 `ToolFacadeService`。
- **标记 services/ 为废弃**：在 `services/__init__.py`、`services/data/__init__.py`、`services/backtest/__init__.py` 添加 `DeprecationWarning`。
- **清理 __pycache__**：删除 app/ 和 tests/ 下的 `__pycache__` 目录。
- **修复端口类型标注**：修复 `domain/ports.py` 中 `list[dict]` 的类型标注语法。
- **更新架构文档**：更新 `app/README.md`，记录统一工具门面的新架构。
- **测试更新**：修复 `test_quant_tools.py` 适配新 `QuantToolRuntime`，11 tests passed。
- **迁移 news_backfill_tasks.py**：将 `tasks/news_backfill_tasks.py` 从使用废弃的 `StockNewsAccess.fetch_bundled` 迁移至 `ToolFacadeService.news_bundle`。
- **DTO 标准化**：
    - 新增 `BacktestRequestDTO`、`SelectionRequestDTO` 到 `application/dto/market_data_dto.py`
    - 新增 `parse_dto()` 到 `presentation/api/request_parsers.py`，统一 Pydantic 解析
    - 完善 `application/dto/__init__.py` 导出所有 DTO
    - 补充 `UserAccountDTO`、`RoleDTO`、`CreateUserCommand`、`ChangePasswordCommand` 到 `user_dto.py`
    - 补充 `InvestmentManagerDTO`、`ManagerProfileDTO`、`LeaderboardItemDTO` 到 `investment_manager_dto.py`
- **API 版本化策略**：
    - 新增 `presentation/api/v2_context.py` - v2 路由上下文
    - 新增 `presentation/api/routes_v2.py` - v2 路由蓝图工厂，支持 DTO 验证和标准化响应格式
- **测试修复**：
    - 修复 `application/dto/scanner_dto.py` 缺少 `ScannerSnapshotDTO`
    - 更新 `tests/test_qlib_pipeline.py` 使用 `ToolFacadeService` 接口 (mock fetch_bars)
    - 移除不存在的 `unified_buy_hold_backtest` 测试
    - 16 tests passed
- **统一异常处理**：
    - 扩展 `presentation/api/error_handlers.py` 支持 HTTPException (400/401/403/404/422)
    - 新增 `setup_flask_login_errors()` 处理认证异常 (unauthorized/invalid_session)
    - 更新 `bootstrap.py` 集成 Flask-Login 错误处理
- **DTO 规范化**：
    - 新增 `watchlist_dto.py` (WatchlistAddSymbolDTO, WatchlistCreateDTO, WatchlistUpdateDTO 等)
    - 新增 `portfolio_dto.py` (RegisterUserDTO, ChangePasswordDTO, UpdateUserDTO)
    - 新增 `signal_dto.py` (SignalFlagQueryDTO, SignalFlagBackfillDTO, SignalFlagUpdateDTO)
    - 新增 `manager_dto.py` (LeaderboardQueryDTO, ManagerProfileUpdateDTO, ManagerDeployDTO)
    - 导出 `ScannerStatusDTO`, `ScanResultDTO` 到 scanner_dto.py
    - 新增 `parse_json_body()` 辅助函数到 request_parsers.py

## 2026-04-25

- **services/ 与 application/services 职责重叠清理**：
    - **统一工具门面**：在 `domain/ports.py` 新增 `ToolFacadePort` 抽象接口，在 `application/services/` 新建 `ToolFacadeService` 统一封装 `MarketDataAccess`、`FundamentalDataAccess`、`StockNewsAccess`、`StrategyToolBridge` 功能，消除了原 `services/` 目录与 `application/services/` 的职责重叠。
    - **模块迁移**：将 `services/data/market_access.py` 等迁移至 `application/services/tool_facade_service.py`。
    - **工具函数迁移**：`NewsRelevanceFilter` 迁移至 `core/utils/news_utils.py`；`TechnicalTrendService` 迁移至 `domain/analysis/technical_trend.py`。
    - **向后兼容**：保留 `services/` 目录为兼容别名，新代码引导使用 `ToolFacadeService`。
    - **更新依赖方**：`bootstrap.py`、`quant_tools.py`、`qlib_pipeline_service.py` 等全面使用新服务。

- **剩余 services/ 清理**：
    - **PredictionValidator** 迁移至 `application/services/analysis_prediction_service.py`。
    - **DailyAnalysisService** 迁移至 `application/services/daily_analysis_application_service.py`。
    - **ImportService** 迁移至 `core/utils/import_utils.py`。

- **domain/ports 扩展**：新增 `ToolFacadePort` 接口定义。

- **domain/analysis 模块**：新建 `domain/analysis/` 存放纯领域分析逻辑。

- **core/utils 扩展**：新增 `import_utils.py`、`news_utils.py`，收口工具函数。

- **测试更新**：`test_quant_tools.py` 适配新 `QuantToolRuntime` 接口，8/8 tests passed。

### TODO-006: Resolve Application Service Circular Imports

**Problem**: Services importing other application services directly.

**Analysis**: 
- `AiAnalysisService`, `AiResearchService`, `IntegrationStackService` all import `FinGPTApplicationService`
- However, they use constructor injection with type hints, not circular imports at module level
- The services receive `FinGPTApplicationService` as optional constructor parameter
- Bootstrap wires them together via `ServiceBundle` composition

**Status**: ✅ Already solved via constructor injection pattern

### TODO-007: Fix Presentation → Infrastructure Layer Violations

**Problem**: API routes directly import infrastructure modules at module level.

**Changes**:
- Removed inline imports from `routes.py`:
  - `TaskMessageStore`, `task_label` from `infrastructure.messaging.task_message_store`
  - `enqueue_task_idempotent` from `infrastructure.messaging.celery_reliability`
- Added `task_label` and `enqueue_task_idempotent` to `ApiV1Context`
- Updated `create_api_blueprint()` to accept these as parameters
- Updated `bootstrap_components/presentation.py` to inject dependencies
- Changed all usages in routes to use `ctx.task_message_store`, `ctx.task_label`, `ctx.enqueue_task_idempotent`

**Files Modified**:
- `app/presentation/api/v1_context.py` - added task_label, enqueue_task_idempotent
- `app/presentation/api/routes.py` - removed inline imports, use ctx
- `app/bootstrap_components/presentation.py` - inject dependencies

**Tests**: 5 passed ✅

### TODO-008: Add Market Configuration Mapping

**Problem**: Hardcoded market benchmark symbols in multiple files.

**Changes**:
- Added `MARKET_BENCHMARKS` and `MARKET_CURRENCIES` mappings to `domain/enums.py`
- Added `benchmark` and `currency` properties to `MarketCode` enum
- Refactored `market_service.py` and `strategy_service.py` to use `market.benchmark`

**Files Modified**:
- `app/domain/enums.py` - added MARKET_BENCHMARKS, MARKET_CURRENCIES, properties
- `app/application/services/market_service.py` - use market.benchmark
- `app/application/services/strategy_service.py` - use market.benchmark

**Tests**: 5 passed ✅

## 2026-04-18

- **数据库架构升级（SQLite → MySQL）**：完成从 SQLite 到 MySQL 的全量迁移，解决了高并发任务（如全市场扫描）下的 `database is locked` 问题。核心数据库 `quant_atlas` 现已托管所有用户、行情、策略、信号及朋友圈数据。
- **MySQL 读写分离架构**：在 `mysql_client` 中引入了 Master（写）与 Slave（只读）双连接池机制。通过环境变量 `MYSQL_READ_HOST` 等可配置独立只读节点。`StockCache` 与核心服务已适配自动路由：`SELECT` 查询优先走从库，`INSERT/UPDATE` 强制走主库，显著提升了系统的并发查询吞吐量。
- **耗时任务全面 Celery 化**：将 Scanner（行情扫描器）、数据回填、基础数据同步（龙虎榜/研报）等高 I/O、高耗时任务从 Web 进程中完全剥离。设置 `SCANNER_FORCE_THREADS=0` 后，Web 进程进入“轻量读取”模式，仅负责响应前端请求，所有写库压力由 Celery Worker 承担。
- **RD-Agent 闭环能力增强**：
    - **本地模型支持**：引入 `app/core/llm_config.py`，支持 DeepSeek-Coder、Ollama 等本地 OpenAI 兼容接口，降低 API 成本并保护策略隐私。
    - **量化专用 Prompt**：为 RD-Agent 注入了针对 Qlib 表达式、向量化计算及避坑指南的专家指令模板，提升了自动挖掘因子的质量。
    - **挖掘-验证闭环**：打通了“LLM 提出假设 -> Qlib 真实数据验证 -> 产物自动注册 -> 因子库导出”的全自动闭环流程。
- **Qlib 真实数据流水线**：
    - **MySQL → Qlib 桥接**：实现了从 MySQL `stock_history` 自动同步数据至 Qlib 二进制环境的逻辑，摆脱了对外部 `dump_bin.py` 脚本的依赖。
    - **全量行情同步**：完成了 A 股全市场 8654 只股票（含退市）自 1990 年至今的全量真实历史行情同步，Qlib 环境现已具备“完美历史记忆”。
    - **基准指数补全**：针对 Qlib 回测报错，全量补全了沪深 300、上证指数、深证成指、创业板指、科创 50 及北证 50 的历史基准数据。
- **系统代码规范化（UID 统一）**：确立了 `{MARKET}:{CODE}`（如 `CN:000001`）为全系统数据库存储与逻辑层处理的统一格式。`SymbolNormalizer` 增加了 `to_db_code` 强制规范化工具，解决了此前代码格式混合导致的重复数据与关联失效问题。
- **配置体系重构**：将配置划分为核心层（`.env`，管理敏感密钥与后端节点）与业务层（`config/config.cfg`，管理回测参数与 UI 偏好），提升了生产环境的安全性和可维护性。
- **首页性能优化**：调整了 `get_all_stocks` 的新鲜度过滤逻辑，增加了“低新鲜度自动回退加载 Top 6000”的防御机制，确保在数据迁移初期或扫描器未完成时首页依然能够展示完整的市场全景。

## 2026-04-22

- **Freqtrade 核心功能集成 (Complete Port)**：
    - **交易生命周期管理**：在 `app/domain/trading_entities.py` 中重构了 `Trade` 与 `Order` 实体，完整移植了 Freqtrade 的持仓状态管理、ROI 盈亏止盈及 Stoploss 硬止损逻辑。
    - **MySQL 持久化适配**：在 `mysql_client.py` 中新增 `ft_trades` 与 `ft_orders` 表 DDL，并实现 `MySQLTradingRepository`，确保所有量化交易流水与持仓数据均存储于 MySQL 主库。
    - **策略引擎接口化**：定义了 `BaseStrategy` 领域接口，兼容 Freqtrade `IStrategy` 标准（indicators/entry/exit），并提供了 `SampleStrategy` 作为集成范例。
    - **Bot 核心循环移植**：在 `app/application/trading/bot_engine.py` 中实现了自主控制的交易机器人引擎，支持 OHLCV 数据获取、多标的信号扫描、持仓风险实时监控及自动执行交易指令。
    - **架构解耦与依赖注入**：通过 `TradingBotProvider` 端口实现了业务逻辑与底层交易所（CCXT）的解耦，并在 `app/bootstrap.py` 中完成了全链路依赖注入。

- **Hyperswitch 核心功能集成 (Payment Orchestration)**：
    - **支付编排引擎**：在 `app/application/services/payment_orchestrator.py` 中实现了支付生命周期管理引擎，支持 PaymentIntent 创建、确认、自动捕获（Capture）及退款（Refund）逻辑。
    - **多网关路由体系**：设计了基于策略的网关路由机制，能够根据优先级动态选择最优支付通道；通过 `PaymentGatewayPort` 接口支持插件式扩展。
    - **支付持久化层**：在 `mysql_client.py` 中新增 `gateway_configs`、`payment_intents` 与 `payment_refunds` 表 DDL，并实现 `MySQLPaymentRepository` 进行金融级审计落库。
    - **抽象与适配器模式**：引入 `MockPaymentGatewayAdapter` 作为首个网关实现，展示了如何通过适配器模式隔离外部支付服务（如 Stripe/Adyen）的差异性。

- **Kronos 基础模型集成 (Financial Foundation Model)**：
    - **K线序列生成式预测**：在 `app/infrastructure/adapters/kronos_adapter.py` 中封装了 Kronos 核心推理引擎，支持基于 Transformer 的 OHLCV 全量行情生成式预测。
    - **大模型资产管理**：建立了 `KronosModel` 领域模型，支持对 mini/small/base 等不同规模预训练模型及本地/远程（Hugging Face）权重的统一版本控制。
    - **预测时序持久化**：在 `mysql_client.py` 中新增 `kronos_models` 与 `kronos_predictions` 表，实现了对高维预测数据（JSON 序列）的结构化存储与历史评估能力。
    - **时序预测流水线**：在 `app/application/services/kronos_service.py` 中打通了“原始行情获取 -> 特征 Token 化 -> 模型推理 -> 逆归一化 -> 结果落库”的全自动预测链路。

    - **OpenBB 核心功能集成 (Global Financial Data)**：
    - **全品种行情适配器**：在 `app/infrastructure/adapters/openbb_adapter.py` 中实现了基于 OpenBB SDK 的多源行情适配器，支持 Equities, FX, Crypto 等全球资产数据的统一获取。
    - **多源数据编排**：引入 `GlobalMarketService`，通过 OpenBB 平台整合了 YFinance, FMP, Tiingo 等数十家主流数据供应商，大幅扩展了平台的海外市场覆盖能力。
    - **高性能行情缓存**：在 `mysql_client.py` 中新增 `openbb_data_cache` 表，配合 `MySQLOpenBBRepository` 实现了基于 TTL 的结构化行情缓存，有效降低了 API 频率限制影响。
    - **供应商资产管理**：建立了 `openbb_provider_configs` 体系，支持对不同数据供应商的 API Key、启用状态及特定参数进行动态化配置与加密存储。

- **QuantML 核心功能集成 (Factor Zoo & Model Benchmarks)**：
    - **大规模因子库同步**：实现了 `QuantMLFactorService` 能够解析 `QuantML/factor_zoo` 中的所有 Markdown 格式因子报告，支持同步 1000+ 个高 IC 因子。
    - **结构化因子持久化**：在 `mysql_client.py` 中新增 `quantml_factors` 表，支持按类别（振幅、标准差、高阶矩等）对因子表达式及其 benchmark 指标（IC, ICIR, T-stat）进行毫秒级检索。
    - **领域驱动架构**：定义了 `QuantMLFactor` 领域实体与 `QuantMLFactorRepository` 端口，通过 `MySQLQuantMLFactorRepository` 实现了业务逻辑与数据库实现的彻底解耦。
    - **全量同步机制**：提供了 `sync_all_factors` 原子化同步链路，确保外部 Factor Zoo 的更新能无缝集成到量化平台的因子目录中。

- **QuantML-Agent 核心功能集成 (AI Agentic Analysis)**：
    - **智能市场洞察引擎**：在 `app/application/services/agentic_analysis_service.py` 中实现了基于 AI Agent 的市场洞察功能，支持自动聚合行情数据并生成结构化情绪分析与趋势预测。
    - **研报深度解读**：引入了 `interpret_report` 链路，利用大语言模型（LLM）对复杂研报进行关键点提取与市场影响评估，实现了从长文本到结构化结论的自动转化。
    - **Agent 知识持久化**：在 `mysql_client.py` 中新增 `agent_market_insights` 与 `agent_report_interpretations` 表，实现了 AI 生成洞察的长期记忆与金融级落库。
    - **解耦的 LLM 适配层**：通过 `AgentLLMAdapter` 统一了不同 Agent 的提示词管理与 JSON 响应解析逻辑，实现了业务 Agent 与具体 LLM 实现（如 Ollama）的彻底解耦。

## 2026-04-23

- **基础设施升级：SQLAlchemy ORM 与 连接池集成**：
    - **核心配置引入**：在 `app/infrastructure/database/orm.py` 中建立了 SQLAlchemy `Base` 基类与带连接池的 `Engine` 工厂，默认配置 `pool_size=10, max_overflow=20` 以支撑高并发异步扫描任务。
    - **全量模型映射**：完成了从 `mysql_client.py` 原生 DDL 到 SQLAlchemy ORM 模型的完整迁移。模型按领域划分（`auth`, `market`, `trading`, `advanced`, `investment`, `moments`），极大提升了代码的可读性与类型安全性。
    - **Alembic 迁移骨架**：初始化了 Alembic 环境并配置 `env.py`，支持基于模型定义的 Schema 自动发现与版本平滑迁移。
    - **Session 生命周期管理**：在 `app/bootstrap.py` 中通过 `teardown_appcontext` 钩子实现了 Scoped Session 的自动清理，确保 Web 请求与 Celery 任务的数据库连接安全回收。
    - **全量 Repository 范式重构**：完成了全站 MySQL 仓库从原生 `DictCursor` 到 SQLAlchemy Session 模式的迁移。包括：
        - **核心业务**：`UserRepository`, `WatchlistRepository`, `StockGroupRepository`。
        - **模拟实盘**：`InvestmentManagerRepository`, `SignalFlagPoolRepository`。
        - **社交与分析**：`MomentsRepository`, `AnalysisReportRepository`。
        - **三方集成**：`AgentRepository`, `KronosRepository`, `OpenBBRepository`, `QuantMLFactorRepository`, `FinGPTRepository`。
    - **混合后端兼容性**：在重构过程中保持了对 SQLite 的兼容性，确保本地开发环境（无 MySQL）依然可以通过文件型数据库正常运行。
    - **依赖注入升级**：重构了 `app/infrastructure/repositories/deps.py`，全链路打通了 `session_factory` 的透明传递。
    - **硬编码 DDL 清理**：彻底移除了 `mysql_client.py` 中 700+ 行的 `_ALL_DDL` 字符串，废弃了手动 `ALTER TABLE` 逻辑。现在 MySQL Schema 完全由 SQLAlchemy Models 定义，并由 Alembic 进行版本化管理。
    - **仓库自初始化重构**：移除了各仓库（`NewsArchive`, `BasicMarketData`, `StockCache`）在 MySQL 模式下的 `CREATE TABLE` 执行逻辑，确保基础设施层职责单一化。

- **数据库稳定性增强：连接泄露修复与连接池调优**：
    - **修复连接泄露**：针对 `StockCache` 等单例引起的连接泄露（1040 Too many connections），在 `mysql_client.py` 中引入了基于 SQLAlchemy 线程本地池化的缓存机制，确保 legacy 代码在不手动关闭连接的情况下仍能安全复用连接。
    - **连接池参数调优**：针对多进程（Web + 多个 Celery Worker）环境，将默认连接池从 `10+20` 下调至更为保守的 `2+3`，有效防止了在分布式环境下撑爆 MySQL `max_connections` 的风险。
    - **生命周期补全**：在 `app/bootstrap.py` 的 `teardown_appcontext` 中强制调用 `mysql_close_thread_local_connection`，打通了 legacy 连接向 SQLAlchemy Pool 回收的最后一步。
    - **BUG 修复**：修正了 `MySQLNewsArchiveRepository` 中 `get_meta` 方法的列名错误（KeyError）。

## 2026-04-24

- **应用服务层深度解耦与模型化 (Service Decomposition & Modelization)**：
    - **引入 Pydantic DTO 体系**：在 `app/application/dto/` 下建立了结构化通信协议，涵盖了 `LonghuEntry`, `YanbaoEntry`, `ManagerProfileDTO`, `UserAccountDTO`, `ScannerStatusDTO` 等模型，彻底消除了 Service 间传递 `dict[str, Any]` 带来的不确定性。
    - **“上帝服务”职责拆解**：
        - **数据解析剥离**：创建了 `EastmoneyParser`，将复杂的 Dataframe 模糊匹配、JSONP 清洗及正则表达式提取逻辑从 `BasicMarketDataService` 中解耦。
        - **随机生成引擎**：创建了 `ManagerGenerator`，将投资经理的画像生成逻辑独立，使 `InvestmentManagerService` 回归业务编排本质。
        - **核心工具收口**：在 `app/core/utils/` 下建立了 `datetime_utils` 与 `pandas_utils`，收口了 A 股交易时段判定、日期规范化及 NumPy 安全序列化等通用逻辑。
    - **Service 接口规范化**：
        - `UserApplicationService` 现在通过 `CreateUserCommand` 与 `ChangePasswordCommand` 进行严谨的入参验证。
        - `ScannerApplicationService` 状态与结果上报已全面迁移至 DTO 模型。
    - **框架依赖清理**：在 `UserService` 等模块中通过动态导入及职责转移，降低了核心业务对 Flask/Werkzeug 的直接耦合度。

## 2026-04-24 (Continued)

- **领域层优化与深度解耦 (Domain Layer Enrichment & Decoupling)**：
    - **建立纯领域异常体系**：在 `app/domain/exceptions.py` 中定义了不依赖 HTTP 状态码的异常基类 (`DomainError`) 及其子类，使核心业务规则的违放更具语义化。
    - **充血模型演进 (Rich Domain Model)**：
        - **交易实体增强**：为 `Trade` 增加了 `duration_minutes` 自动计算和 `is_profitable` 盈利判定；为 `Order` 增加了 `is_fully_filled` 与 `filled_ratio` 属性。
        - **行情实体增强**：为 `StockQuote` 增加了 `is_up` 与 `is_down` 快捷状态判定。
    - **彻底剥离框架语义**：
        - **集成目录抽象化**：重构了 `app/domain/integration_catalog.py`，将原本直接指向 Flask 的 `endpoint` 字段替换为抽象的 `nav_id`。表现层现在通过 ID 映射实现路由跳转，确保了领域层对 Web 路由实现细节的零感知。

## 2026-04-24 (Continued)

- **基础设施层：分布式任务编排与性能优化 (Distributed Tasks & Performance)**：
    - **Celery 任务切片化改造 (Task Chunking)**：
        - **行情扫描分布式化**：重构了 `ScannerApplicationService` 与 `scanner_tasks.py`。原本单机的“全市场轮询”被拆解为多 Worker 协同执行的 `process_quote_batch_task`，通过分片处理 5000+ 标的，大幅提升了扫描吞吐量。
        - **信号旗扫描 Chord 模式**：为 `signal_flag_pool_scan` 引入了 Celery Chord 模式。主任务负责划定扫描 Universe 并分片，多个子 Worker 并行计算多策略信号，最后由 Callback 聚合结果并统一落库。
    - **职责边界清晰化**：Service 层剥离了对特定并发机制（如 ThreadPoolExecutor）的写死依赖，改为提供 `scan_batch` 等原子化接口，使其既支持同步单机执行，也支持 Celery 分布式调度。
    - **时间逻辑集中化**：将 A 股交易时段判定、日期加减等逻辑彻底收口至 `datetime_utils`，消除了各 Service 中的硬编码判断。
 Riverside Riverside

## 2026-04-14

- **信号旗历史回填（2020 起）**：新增 Celery 任务 `signal_flag_pool_backfill` 与 API `POST /api/v1/signal-flag/backfill`（仅异步）；按交易日从 `start_date` 到 `end_date` 逐日调用扫描并落库（默认 max_stocks=800，含买/卖信号）。用于基金经理历史回放“只读库不算信号”的前置数据准备。
- **主页榜单刷新稳定性**：`index.html` 渲染股票卡片/榜单项时对 `name/code/source/type/change` 做 HTML 转义并对跳转链接 `encodeURIComponent`，避免外部数据中包含特殊字符导致 DOM 解析异常从而出现“右侧四榜消失”；`refreshDashboard` 增加 try/catch，单模块异常不阻断其它榜单刷新。
- **涨跌颜色可切换中/美版**：新增配置 `UI_COLOR_SCHEME`（默认 `cn`=红涨绿跌，可设 `us`=绿涨红跌）；`base.html` 用 `data-color-scheme` 切换 `--positive/--negative` CSS 变量，全站 `.positive/.negative` 自动生效。
- **个股页日K默认定位最新**：`stock_detail.html` 的 Lightweight Charts 初次渲染改为默认显示最近约 220 根；加载更早数据时根据上一次 `logicalRange` 做 delta 平移以保持视窗不跳回最早（避免出现默认停在 2020、需要拖很久才能回到现在）。
- **K线红绿涨跌切换**：`stock_detail.html` 的蜡烛图与成交量柱颜色按 `UI_COLOR_SCHEME` 切换：`cn`=红涨绿跌、`us`=绿涨红跌。
- **朋友圈附件在 PC 破图**：`MomentsService.save_upload` 对缺失/异常扩展名的上传文件按 `mimetype` 补齐图片/视频后缀（如 `.jpg/.png/.mp4`），避免 `/uploads/...` 在桌面端因无法识别类型导致缩略图不渲染；不影响已存在附件 URL。
- **MySQL signal_strategies_sell 迁移**：TEXT 列禁止使用 DEFAULT（1101）；改为 `ADD ... TEXT NULL` + `UPDATE ... WHERE IS NULL` 回填 `[]`；`CREATE TABLE` 中该列为 `TEXT NULL`。`get_pool` 对 NULL 转空列表。
- **Beat 收盘链顺序**：`INVESTMENT_MANAGERS_CELERY_BEAT=1` 时由任务 `post_close_signal_then_managers` 先 `run_signal_flag_scan_sync` 再 `run_investment_managers_quick_warmup`，替代原先仅投递 `investment_managers_quick_warmup`；消息中心中文标签已注册。
- **投资经理模拟只读信号旗库**：`InvestmentManagerService` 注入 `SignalFlagPoolRepository`；`simulate_day` 买卖触发改为查当日 `signal_flag_pool` 中该 `strategy_id` 的买/卖集合，不再调用 `generate_signals`；硬止损/ATR 与可成交、流动性过滤不变。返回增加 `signal_flag_codes`（当日池内至少有一条买/卖信号的不同代码数）。`bootstrap` / `investment_manager_tasks` / `moments_tasks` 同步注入信号旗仓库。
- **信号旗 universe 与卖信号入库**：扫描默认 `max_stocks=800`（与基金经理一致），`max_stocks=0` 为缓存全量至 `SIGNAL_FLAG_UNIVERSE_HARD_CAP`（默认 8000）；策略 **卖出**（含 Qlib 死叉）写入 `signal_strategies_sell`，仅卖信号的行也会落库。MySQL/SQLite `signal_flag_pool` 增列；API/页面/Celery 默认参数同步；信号旗页增加「卖点策略」列。
- **研报中心分类 Tab**：`yanbao_hub.html` 将原下拉框改为横向 Tab（全部、个股/行业/宏观/策略研报、晨报），与入库分类名及 `ingest_yanbao_eastmoney_api` 一致；切换 Tab 请求 `GET /api/v1/market/yanbao?category=...`；列表单次 limit 提至 120。
- **投资经理收益榜去按钮 + Beat 自动跑**：`investment_managers.html` 移除初始化/排期/投放/模拟/Celery 快跑等前端按钮，仅保留周期切换；说明改为依赖后台。`celery_app` 在 `INVESTMENT_MANAGERS_CELERY_BEAT=1` 时注册每日 15:35（上海）`investment_managers_quick_warmup`；`config/config.cfg` 增加该项并默认 1。
- **投资经理 Celery 快跑**：新增任务 `investment_managers_quick_warmup`（可选入市排期 + `simulate_day`）、`investment_managers_simulate_day`（仅单日模拟）；API `POST /api/v1/investment-managers/quick-warmup`（默认异步，``?sync=1`` 强制同步）；`POST .../simulate` 支持 body ``"async": true`` 投递单日模拟。收益榜页增加「Celery 快跑」按钮；`task_message_store` 补充任务中文标签。
- **投资经理收益榜展示成交**：`InvestmentManagerRepository.trade_stats_by_manager` 聚合 `manager_trades`；`leaderboard` API 增加每行 `trade_count` / `last_trade_date` 及 `aggregate.total_trades`、`managers_with_trades`；收益榜页增加列与空库时的操作提示；「模拟今日交易」默认 `universe_limit` 改为 800。
- **东财行业映射防拉黑**：`cn_em_industry_map` 修复「缓存过期且拉取失败时仍每次请求都重试」导致的连接风暴；分页请求之间增加随机间隔；单页 `ConnectionError`/`RemoteDisconnected` 等指数退避重试；失败后设置 `_next_retry_at` 指数退避（默认 15 分钟起、上限 4 小时）并继续返回陈旧缓存；可选环境变量 `EM_INDUSTRY_MAP_TTL_SEC`、`EM_INDUSTRY_MAP_FAILURE_BACKOFF_SEC`、`EM_INDUSTRY_MAP_FAILURE_BACKOFF_MAX_SEC`、`EM_INDUSTRY_MAP_PAGE_DELAY_MIN/MAX`。
- **MySQL 连接复用（线程内）**：在 `mysql_client` 增加 `mysql_get_thread_local_connection` / `mysql_close_thread_local_connection`（`threading.local` + `ping(reconnect=True)`，配置变更时重建）。`StockCache`、`mysql_repositories` 及双后端仓库（`moments` / `investment_manager` / `news_archive` / `basic_market_data` / `signal_flag_pool`）在 MySQL 模式下复用同一线程连接，业务路径不再 `close` 共享连接；SQLite 仍按请求开关连接。`signal_flag_pool_repository` 的 MySQL 路径去掉 `with self._conn()`（避免 pymysql 上下文管理器误关共享连接）。
- **市场情绪日度历史回填**：新增 `scripts/backfill_market_sentiment_daily.py`，按 `stock_history` 全表逐日统计相对上一根 K 的涨/跌/平家数并 `save_sentiment_daily`；`StockCache` 增加 `get_stock_history_date_bounds`、`list_distinct_stock_history_dates`、`fetch_stock_history_closes_on_date`，SQLite 为 `date` 建索引 `idx_stock_history_date` 以加速按日扫描。
- **回测情绪门按交易日**：修正「用最新缓存卡死整条历史」问题. 新增 `market_sentiment_daily`（SQLite/MySQL）与 `StockCache.save_sentiment_daily` / `get_sentiment_for_trade_date`；行情轮询在 `save_sentiment` 后按东八区 `today_sh_str()` 写入日度涨跌家数。回测每个交易日 `_cn_sentiment_for_trade_date`：优先日表 → 多标的横截面涨跌占比 → 单标的自身涨跌近似 → 50；`RISK_BACKTEST_SENTIMENT_GATE` 默认 1（关则回测完全不应用情绪门）。投资经理 `simulate_day` 对 `nav_date` 优先日表再回退最新快照。
- **顶栏与链路导航精简**：`base.html` 将「朋友圈」「投资经理」合并为「圈子」下拉；消息中心改为铃铛图标（角标类 `js-nav-bell-badge` 同步桌面与移动抽屉）；右侧为「用户管理」图标（管理员）、头像+用户名·角色链至个人中心、退出为图标按钮；`partials/research_lane.html` 增加朋友圈/投资经理入口，消息改为图标链；移动端抽屉与上述一致。
- **个股新闻 API 500**：`GET /api/v1/stocks/<market>/<symbol>/news` 中 `ok_response` 误传 `enable_legacy_response_fields=`，应为关键字 `enable_legacy_alias=`，已修正 `routes.py` 中 `stock_news`。
- **顶栏与链路重复显示**：`base.html` 中 `.qc-mobile-lane` / `.qc-mobile-user` 位于 `<nav>` 外，桌面端未默认隐藏，与 `main` 内 `research_lane` 叠加出现两条「链路」及重复用户区；已默认 `display:none` 并修正小屏展开选择器为 `nav.app-nav.qc-nav-open ~ .qc-mobile-*`（兄弟选择器）；小屏隐藏主区链路改为 `main.page-wrap .qc-research-lane`，避免抽屉内 `.qc-research-lane` 被误隐藏。
- **朋友圈正文折叠（五行 + 全文）**：`moments.html` 动态正文默认 `-webkit-line-clamp: 5`；渲染后用 `scrollHeight`/`clientHeight` 判断是否溢出，仅溢出时显示「全文」；点击展开 `.expanded` 并显示「收起」，收起后重新测量；无文字纯附件帖不渲染正文块。
- **投资经理人设与头像**：`investment_managers` 增加 `tagline`/`specialty`（SQLite 迁移 + MySQL 可选列）；种子文案含多段「牛逼」介绍、擅长领域与一句话标签；`GET /avatars/pm/<manager_id>` 返回确定性 SVG 头像（渐变+首字）。收益榜与详情展示入市时间、标签与擅长；用户表增加 `avatar_url`，`GET /avatars/user` 默认 SVG，`POST /api/v1/profile/avatar` 上传至 `uploads/avatars/`，顶栏与个人中心展示头像。
- **投资经理「未入市」与初始化互踩**：`upsert_manager` 在重复执行 `ensure_seed_managers`（「初始化 100 经理」）时不再覆盖已有 `deployed_at`/`active`（MySQL 去掉 DUPLICATE KEY 中对这两列的更新；SQLite 改为 `ON CONFLICT DO UPDATE` 仅更新档案字段）。投资经理页增加「入市排期（推荐）」按钮与流程说明，便于一次性按 2020 起每月 10 位激活后再模拟。
- **朋友圈时间统一东八区**：新增 `app/core/shanghai_time.py`（`Asia/Shanghai`），`MomentsRepository` 的 `created_at` 及点赞/评论时间由 UTC 改为上海本地时间字符串；`moments_after_close` 默认 `market_date` 亦按东八区日历日，避免与展示相差 8 小时。
- **朋友圈展示与发布 UX**：动态流置顶；图片/视频以 9 宫格缩略图（`object-fit: cover`）展示，单图单列、双图两列、三图及以上三列；用户发帖最多 9 个附件（前端截断 + `MomentsService` 校验 `too_many_attachments`）；发布区与说明弱化（折叠说明、小标题）；视频格内点击播放再展开控件。
- **朋友圈用户帖编辑/删除**：`DELETE /api/v1/moments/<post_id>`、`PATCH /api/v1/moments/<post_id>`（正文 + 可选整表替换附件），仅 `actor_type=user`且 `actor_id` 为当前登录用户 id/用户名时允许；feed 项增加 `can_edit`；上传接口按扩展名 + MIME 推断 `media_type`，前端对 `file`/未知类型按 URL 后缀与 `mime_type` 回退为图/视频缩略图，避免只显示文件名。

## 2026-04-13

- **存储迁移（SQLite → MySQL）**：新增 `DATABASE_BACKEND=mysql` 配置与 MySQL DDL/连接层，合并原 `instance/*.db` 多库为单库 `quant-atlas`（表：用户/自选/分组、stock_cache、基础数据、新闻归档、信号旗池等）。
- **数据迁移脚本**：新增 `scripts/migrate_sqlite_to_mysql.py`，可将现有 SQLite 数据一次性导入 MySQL（导入前会清空目标表，便于可重复迁移）。
- **基础数据抓取稳健性**：修复 AkShare 龙虎榜列名在 Windows 环境可能乱码导致的“入库 0 行”；研报抓取增加 AkShare 聚合兜底（当东财 HTML `read_html` 反爬失败时，按股票列表拉取研报并写入 `yanbao_items`）。
- **研报中心覆盖扩展**：新增东财研报 API 抓取（宏观/策略/晨报/行业/个股五类），用于补全“研报中心”覆盖面，并将 `yanbao_items.category` 统一为「个股研报/行业研报/宏观研报/策略研报/晨报」。
- **新闻归档批量刷新**：为批量回填提供 `NEWS_BACKFILL_FAST_ONLY=1` 快速模式（跳过行情档案与 AkShare 个股新闻，使用门户快讯过滤 + 归档落库），避免大规模标的刷新时卡住；可用于补齐近 30 天新闻缓存的滚动刷新。
- **定时任务（Celery Beat）**：新增 `NEWS_DAILY_BEAT`、`BASIC_DATA_LONGHU_BEAT`、`BASIC_DATA_YANBAO_BEAT` 开关；Beat 每日定时刷新新闻归档/龙虎榜/研报（研报改用东财 API）。同时 `market_tasks`/`data_backfill_tasks` 注入 MySQL 仓库，确保 MySQL 模式下定时入库生效。
- **Redis 部署地址调整**：将 Celery broker/result 与消息中心的默认 Redis 从 `localhost` 切换为内网 `192.168.8.103`（需保证 Web/Worker/Beat 使用同一 Redis）。如需迁移旧 Redis 数据，建议用 RDB/AOF 或主从复制方式同步（见运行说明）。
- **Redis 回退（192.168.8.103 → localhost）**：由于目标机 Redis 暂不便于完成数据同步与对外服务校验，配置回退为本机 `redis://localhost:6379/0`，以保证 Celery 队列与消息中心稳定可用。
- **Qlib 20 策略移植（轻量版）**：将 `scripts/qlib_strategy.py` 的规则策略迁入 `app/models/qlib_high_win.py`，注册到 `StrategyFactory` 与回测下拉分组；补齐脚本中占位的 12-15 “ML 策略”为可运行的轻量因子/规则版本（不依赖 pyqlib 训练），并加入止损逻辑以适配平台单标的回测。
- **全局风控后处理（全策略生效）**：为所有“内置策略”在回测与信号旗扫描中统一增加成交量过滤 + 波动率过滤（开仓门禁），并在回测执行中加入默认 -8% 单仓止损强制平仓（不改动各策略实现，避免大范围重构）。
- **智能选股扩容 Qlib 策略池**：在 `MarketRegimeManager.get_recommended_categories()` 的推荐类别中追加「Qlib 高胜率（规则/轻量）」以纳入 `DefaultStrategyProvider.select()` 的市场扫描模型池（smart 模式会下发 `category:` 过滤并参与共振投票）。
- **回测实盘化（成本/滑点/ATR 追踪）**：为 `DefaultBacktestProvider` 增加可配置的滑点（bps）、手续费、最小手续费与卖出印花税；止损升级为「-8% 硬止损 + 可选 ATR 追踪止损」，并将风控/成本参数写入 `config/config.cfg` 作为运行时可调项。
- **仓位风控（按手数取整）**：在 `DefaultBacktestProvider` 引入可配置仓位模式（full/max_weight/risk/hybrid），按「最大仓位」与「风险预算（结合硬止损/ATR 初始止损距离）」换算买入股数，并在 A 股场景按 `BT_CN_LOT_SIZE=100` 一手向下取整，尽量避免零散股数与资金不足导致的碎股交易。
- **可成交约束 + 组合回测 + 诊断指标**：回测引擎增加 A 股日频近似的停牌/无量、一字板、涨跌停买卖约束；支持 `symbol` 传入逗号分隔实现多标的组合回测，并用 `BT_MAX_POSITIONS` 限制持仓上限；同时在 `metrics.diagnostics` 输出门禁拦截次数、不可成交拦截次数、止损次数与费税合计，并在回测页面展示。
- **情绪门禁（只卖不买）**：回测引擎新增市场情绪阈值风控：当 `sentiment_score < RISK_SENTIMENT_MIN_SCORE` 时禁止开仓买入，仅允许卖出（含止损）；并在 `metrics.diagnostics` 中输出 `sentiment_score` 与 `blocked_buy_sentiment`，前端回测面板同步展示。
- **策略库扩容（72 → 100）**：新增 `app/models/extended_28.py` 的 28 个扩展策略（趋势突破/均值回归/恐慌抄底/机构资金等轻量指标流派），注册进 `StrategyFactory` 与回测下拉分组 `extended_28`，总策略数达到 100。
- **投资经理模拟与排行榜（v1）**：新增「100 策略=100 投资经理」模拟子系统（`investment_managers.db`）：支持初始化/分批入市（每次 10 个）、按策略信号进行简化交易落库、经理净值与持仓快照回溯，以及日/周/月/年收益榜 API 与页面。
- **投资经理交易生命周期升级**：投资经理模拟从“仅开仓示范”升级为跨日持仓状态机：持仓状态持久化（含 high watermark）、支持卖出信号与「硬止损 + ATR 追踪止损」强制平仓，并加入 A 股可成交约束（停牌/无量、一字板、涨跌停）与情绪门禁（低情绪只卖不买）；交易流水、持仓快照与每日净值可回溯。
- **入市排期 + 历史回放（2020 起每月+10）**：新增 `deploy-schedule` 与 `backfill` 接口：从 2020-01-01 起每月新增 10 位投资经理入市（写入 `deployed_at`，并按 `asof_date` 自动计算 active）；支持按交易日历从历史日期回放执行 `simulate_day()`，用于跑出“最牛逼经理”排行榜。
- **投资经理回放异步化（Celery）**：将投资经理 `backfill` 支持改为默认异步投递 Celery 任务 `app.tasks.investment_manager_tasks.investment_managers_backfill`（可用 `?sync=1` 强制同步），并写入消息中心，便于长时间回放任务观察与回溯。
- **用户赛跑 + 交易导入/导出（预留接口）**：投资经理模块新增用户赛跑账户与交易流水表（同库 `investment_managers.db`），提供用户现金设置与交易导入接口；同时支持导出投资经理/用户交易流水 CSV，便于外部审计与对比分析。
- **投资经理子系统切换 MySQL（优先落库）**：为 `InvestmentManagerRepository` 增加 SQLite/MySQL 双后端（`DATABASE_BACKEND=mysql` 时走 MySQL），并将 `bootstrap` 与投资经理回放 Celery 任务在 MySQL 模式下统一注入 MySQL 仓库；新增 `scripts/migrate_investment_managers_sqlite_to_mysql.py` 用于把 `instance/investment_managers.db` 迁移到 MySQL 新表。
- **投资经理回溯页收益曲线**：在 `investment_manager_detail.html` 增加基于净值快照（`manager_nav.equity`）的收益曲线展示，并输出区间累计收益与最大回撤，方便快速判断经理风格与风险。
- **回放默认股票池扩大**：投资经理 `simulate/backfill` 默认 `universe_limit` 调整为 800（按成交额取前 800 只作为每日 Universe），提高覆盖面；仍支持请求参数传入覆盖，并保持上限 800。
- **Celery 注册投资经理回放任务**：在 `app/celery_app.py` 显式导入 `app.tasks.investment_manager_tasks`，确保 worker 注册并可在 `celery inspect registered` 中看到 `app.tasks.investment_manager_tasks.investment_managers_backfill`。
- **朋友圈（Moments）MVP**：新增朋友圈信息流（基金经理/6 Agent/所有用户同圈），实现 MySQL 表 `moments_posts`/`moments_attachments`，提供发帖/拉取 feed/附件上传接口与 `/moments` 页面；附件落盘 `instance/uploads/moments` 并经 `/uploads/...` 登录态访问。
- **朋友圈收盘自动发帖（Beat 可选）**：新增任务 `app.tasks.moments_tasks.moments_after_close`，可选开启 `MOMENTS_AFTER_CLOSE_BEAT=1` 在 15:10（上海时区）自动为 active 基金经理发布收益战报与净值曲线截图，并为 6 个研究 Agent 发布角色点评模板（后续可接入 LangGraph 输出）。
- **基金经理战报内容升级（今日调仓 + 仓位变化）**：收盘发帖从 `manager_trades/manager_holdings_snap` 抽取当日买卖与原因，展示“今日调仓那支股票/调仓明细”，并对比上一交易日快照输出 Top 持仓与权重变化，使朋友圈战报更贴近真实实盘复盘。
- **今日调仓摘要挑选优化**：基金经理战报“今日调仓那支股票”优先按「今日 vs 上一快照日」的 |权重变化| 最大标的挑选；若缺快照对比则回退到当日「净成交额最大」标的，避免仅取第一笔成交导致摘要偏离核心调仓。
- **朋友圈互动（点赞/评论）**：新增 `moments_likes`/`moments_comments` 表，支持帖子点赞（可取消、计数）与评论（发表/列表/计数），前端信息流增加点赞/评论入口与内嵌评论区展示。
- **Agent 评论自动回复（对话化）**：当用户评论 `actor_type=agent` 的帖子时，异步任务 `reply_to_agent_comment` 将调用本地模型（Ollama `/api/generate`）生成简短回复，并以 `agent:{role}` 身份写入评论区，实现“像和 agent 对话”。启用条件：`ENABLE_CELERY=1` 且 worker 已启动。
- **朋友圈附件 URL 修复**：修正用户上传与经理战报图生成的 `file_url`，避免 `/uploads/uploads/...` 双前缀导致静态访问 404；`/uploads/<path>` 视图增加对历史错误路径的兼容归一化。
- **移动端导航体验优化**：手机竖屏下将顶栏展开菜单从“单列长按钮”改为 3 列网格入口，压缩用户区占屏与内容卡片间距，使移动端信息密度更接近 App 交互。
- **移动端抽屉菜单（链路/用户区折叠）**：手机端默认隐藏研究链路快捷条与用户区（用户管理/个人中心/退出/身份），统一收进汉堡菜单抽屉，点开才显示，提升首屏清爽与可用面积。

## 2026-04-23

- **final_plan 重构第一轮落地**：新增 `RecommendationService` 与 `GET /api/v1/recommendations/daily`，聚合信号旗/选股、买卖计划、AI 证据链和观察单胜率，今日操盘台新增“每日 AI 推荐 Top3”卡片。
- **诊股与产业链边界**：新增 `DiagnosisReportService`、`IndustryChainService` 及 `GET /api/v1/diagnosis/report`、`GET /api/v1/industry-chain`，把 AI 分析、买卖计划、证据链和产业链结构标准化为诊股报告制品。
- **复盘、画像与散户助手边界**：新增 `ReviewTrackingService`、`UserInvestmentProfileService`、`RetailAssistantHubService` 及对应 API（`/reviews/*`、`/user/investment-profile`、`/retail-assistant/*`），为观察单复盘、个性化推荐、知识库问答、朋友圈分享和组合风险仪表盘提供稳定应用契约。
- **final_plan 六阶段前端整合**：新增 `/retail-assistant` 散户 AI 助手总入口并挂到 AI 研究导航；个股详情页新增“AI 诊股报告”和“产业链机会图”区块；模拟观察单页新增每日/每周复盘；个人设置页新增投资画像编辑；各区块按现有 `section-shell`/pill/卡片风格串联操盘台、诊股、买卖计划、证据链、观察单、朋友圈和研报中心。
- **全站便捷加自选**：新增 `static/js/watchlist_quick_actions.js` 统一封装 `qcAddToWatchlist` 与成功提示；在今日操盘台推荐/观察候选、个股详情、模拟观察单、AI 分析、信号旗、市场全景、选股器、中长线选股和散户助手输入框增加“加自选”入口，让用户在看到股票的主要界面都能直接沉淀到自选池。
- **user_plan 上线化重构基座**：新增 `docs/user_plan_refactor_roadmap.md`；新增 `UserAccessPolicyService`、`UserAuditTrailService`、`PagePreferenceService` 及 `/api/v1/user/access-policy`、`/api/v1/user/audit-trail`、`/api/v1/user/page-preferences`，以现有角色映射 Free/Pro/VIP 权益，支持页面偏好和用户足迹审计；个人中心新增权限权益、页面管理、我的足迹，散户助手新增权限摘要，今日操盘台读取隐藏卡片与字体偏好。
- **user_plan 剩余阶段 MVP**：新增 `WatchlistExperienceService` 与 `UserLifecycleService`，补齐 `/api/v1/watchlist/experience`、`/api/v1/user/lifecycle`、`/api/v1/user/notification-preferences`、`/api/v1/user/privacy-consent`、`/api/v1/user/data-export`、`/api/v1/user/account-deletion-request`；自选股页新增深度系统（排序、预警、批量诊股入口、周复盘、分享卡片），个人中心新增推送同步、隐私同意、数据导出、删除申请和订阅入口，散户助手展示上线合规与同步状态。

- **通达信板块反向查询 API**：新增 `GET /api/v1/tdx/symbols/<symbol>/blocks`，按 `SymbolNormalizer.to_db_code`（`CN:{market}{code6}`）查询 `tdx_block_items`，并对历史入库数据保留 `sh/sz/bj{code6}` 兼容匹配；用于个股页展示所属板块。
- **通达信基础表 symbol 对齐统一键**：`cn_stock_basics.symbol` 与 `tdx_block_items.symbol` 入库统一写入 `CN:{market}{code6}`（与 `stock_history.stock_code` 风格一致）；反向查询 API 仍兼容旧行数据。
- **通达信基础表迁移清洗**：入库完成后删除 `symbol` 不以 `CN:` 开头的遗留行，避免同一板块同一股票出现两套映射（迁移期重复 upsert 副作用）。
- **个股详情页展示通达信板块**：`stock_detail.html` 增加「通达信板块」区块并异步拉取上述 API；同时增强 `parseMarketSymbol` 对 `CN:CN:...` 这类重复前缀的兼容解析。
- **科创板市场判定修正**：`SymbolNormalizer` 将 `688` 归为沪市（`sh`），并在 `block_dat_reader` 中对 `688` 与 `60` 采用一致的 `{market}{code6}` 生成规则，避免板块成分股误归 `sz`。
- **通达信基础数据入库可观测性**：`TdxBaseDataService.ingest_all_to_mysql` 增加解析规模与最终 upsert 汇总日志（配合既有的批量 `executemany` 写入）。
- **最小验证脚本**：新增 `scripts/verify_tdx_mysql_counts.py`（只读统计 `cn_stock_basics/tdx_*` 行数，可选打印某标的板块映射样本）。
- **基础数据任务化扩展（财务快照 / 自选股）**：
  - 新增配置开关：`TDX_FINANCE_INGEST_ENABLED`（在线财务快照）、`TDX_WATCHLIST_INGEST_ENABLED`（本地 `.blk` 自选/板块文件）、以及 `TDX_FINANCE_RATE_LIMIT_RPS` / `TDX_FINANCE_MAX_SYMBOLS_PER_RUN` / `TDX_WATCHLIST_PATHS`。
  - 新增 MySQL 表：`cn_finance_snapshots`（按 `symbol+report_date` upsert）、`tdx_watchlists`、`tdx_watchlist_items`。
  - 扩展 `/api/v1/tdx/base-data/ingest` 支持在请求体中传入 `finance/watchlists` 触发两条子链路；并新增查询接口：`GET /api/v1/tdx/watchlists`、`GET /api/v1/tdx/watchlists/<name>/members`、`GET /api/v1/tdx/finance/<symbol>/latest`。
- **MySQL 连接超时**：`mysql_connect` 增加 `connect_timeout/read_timeout/write_timeout`，避免网络抖动时调用方长期阻塞。
- **集成中枢（上游项目落地地图）**：新增领域目录 `app/domain/integration_catalog.py`（静态卡片：上游项目→Atlas 模块/Port/页面入口 + SOLID 对齐说明）、`IntegrationHubService` 组装上下文；页面 `/integration-hub`（`integration_hub.html`，视觉对齐 `capabilities.html`）；顶栏与「能力总览」互链，便于 Gemini 驱动的多项目集成按需导航与审计。
- **集成栈 Facade（深度重构 1）**：新增 `IntegrationStackService`（聚合 Kronos、QuantML、QuantML-Agent、GlobalMarket(OpenBB)、TradingBot（Freqtrade 语义）、PaymentOrchestrator（Hyperswitch 语义）的只读探测）、API `GET /api/v1/integration/stack-status`；`ServiceBundle` 注入该门面；集成中枢页实时拉取 JSON 摘要（不触发外网行情）。
- **集成栈 Facade（深度重构 2）**：新增领域端口 `FinGPTPersistencePort`；`FinGPTRepository` 实现该端口并补充预测/情感行数与最近 ticker 抽样；`RepositoryBundle` 注入 `fingpt_repository`；`IntegrationStackService` 增加 FinGPT 层探测及 MySQL 集成表行数汇总（`ft_*`、`payment_*`、`fingpt_*`、`kronos_*`、`openbb_data_cache`、`quantml_factors`、`agent_market_insights`）。
- **集成栈 Facade（深度重构 3）**：`FinGPTPersistencePort` 补充抽象 `save_prediction` / `save_sentiment`；新增 `FinGPTApplicationService`（`record_prediction` / `record_sentiment` / `probe_integration_stack_layer`）；`IntegrationStackService` 仅依赖该应用服务进行 FinGPT 探测；`ServiceBundle` 暴露 `fingpt_application_service`，后续 LangGraph 或其它业务落库应注入应用服务而非直接使用 `FinGPTRepository`。
- **研究图 FinGPT 节点 Wiring**：修正 `fingpt_forecaster` 对 `react_with_tools` 的调用（补全 `llm`）；`build_custom_trading_graph` / `TradingAgentsService` 支持注入 `fingpt_application_service`；节点生成文本后经 `build_prediction_from_forecast_text` 尽力解析为 `FinGPTPrediction` 并 `record_prediction`；`AiResearchService` 与 Celery `scheduled_daily_analysis` 装配同一应用服务（MySQL 关闭时自动跳过写库）。
- **研究图情感落库**：`sentiment_fingpt_payload` 迁至 `app/application/services/`（叙述文本 → `sentiment_score` / `impact_level` / `summary`，供研究图与 AI 分析复用）；`sentiment_analyst` 节点在 `MySQL`+`FinGPTApplicationService` 可用时对应当前 `ticker` 调用 `record_sentiment` 写入 `fingpt_sentiment`；`graph.py` 增加本模块 `logger` 用于落库失败可观测性。
- **AI 个股分析情感落库**：`AiAnalysisService` 可选注入 `FinGPTApplicationService`；`POST /api/v1/.../ai/analyze`（及 `ai/report` 同源分析）成功生成 Ollama 正文后，以 `{market}:{symbol}` 为 ticker 写入 `fingpt_sentiment`，摘要前缀 `[ai_analyze:<mode>]` 便于与研究会话落库区分开。
- **FinGPT 写入策略可配置**：`AppSettings` 增加 `FINGPT_WRITE_RESEARCH_SENTIMENT` / `FINGPT_WRITE_RESEARCH_PREDICTION` / `FINGPT_WRITE_AI_ANALYZE`（默认均为开启）；`FinGPTApplicationService` 提供 `can_write_*` 与 `write_policy()`，集成栈 `layers.fingpt` 探测结果附带 `write_policy`；Celery 每日分析与 Web 共用同一套环境变量。
- **集成中枢 UI**：`/integration-hub` 顶栏徽章展示上述三项 FinGPT 写入策略（无 MySQL 时徽章为灰）；与 API `stack-status` 中 `layers.fingpt.write_policy` 同源配置。
- **通达信本地日线路径**：`TdxLocalPaths.lday_file` 将沪市判定由「60 或 688」改为「60 或 68xxxx」（覆盖科创板 689 等），与 `SymbolNormalizer` / `block_dat_reader` 一致，避免 `689*` 误走默认分支。
- **API v1 组合根注入修复**：`create_api_blueprint` 补齐 `integration_stack_service` 参数，避免 Flask 启动时因关键字参数不匹配导致注册 API 失败。
- **FinGPT 运维 API**：API v1 上下文注入 `fingpt_application_service`；新增 `GET /api/v1/fingpt/status`（策略+行数+最近 tickers）与 `GET /api/v1/fingpt/recent`（可调 limit，仅最近 tickers），用于运维与集成中枢联动展示；同时 `FinGPTPersistencePort` 补充 `recent_sentiment_tickers` 只读方法由 `FinGPTRepository` 实现。
- **FinGPT 只读列表查询**：`FinGPTPersistencePort` 新增 `list_recent_predictions` / `list_recent_sentiments`（可按 ticker 过滤）；`FinGPTRepository` 实现并对 JSON 字段做安全反序列化；API 新增 `GET /api/v1/fingpt/predictions` 与 `GET /api/v1/fingpt/sentiments`（支持 `limit`/`ticker`），用于审计与回溯。
- **FinGPT 预测幂等写入**：MySQL DDL 为 `fingpt_predictions` 增加唯一键 `ux_fingpt_ticker_date (ticker, prediction_date)`；`FinGPTRepository.save_prediction` 改为 `INSERT ... ON DUPLICATE KEY UPDATE`，避免研究/定时任务重复写入导致噪声与膨胀。
- **FinGPT 情感幂等写入**：MySQL DDL 为 `fingpt_sentiment` 增加 `summary_hash` 与唯一键 `ux_fingpt_sent_ticker_hash (ticker, summary_hash)`；`FinGPTRepository.save_sentiment` 写入时对 `summary` 计算 SHA-256（即使 summary 为空也计算，避免 NULL 无法命中唯一键）并 `ON DUPLICATE KEY UPDATE`，减少 `ai_analyze` / 研究节点重复写入造成的库噪声。
- **集成中枢 FinGPT 运维面板**：`/integration-hub` 增加 FinGPT 只读抽样区块，直接展示 `/api/v1/fingpt/status`、`/api/v1/fingpt/predictions?limit=20`、`/api/v1/fingpt/sentiments?limit=20` 的 JSON，便于审计与回溯。
- **FinGPT 运维面板 ticker 过滤**：集成中枢的 FinGPT 抽样区块增加 `ticker` 输入框（回车触发刷新）；预测/情感请求会附带 `&ticker=` 参数以过滤单标的记录，减少噪声。
- **FinGPT 情感去重脚本**：新增 `scripts/dedupe_fingpt_sentiment.py`，按 `(ticker, summary_hash)` 保留最新 `id`、删除重复行，并尝试补齐唯一索引；用于清理历史脏数据后让 `ensure_mysql_optional_columns` 的唯一键真正落地。
- **FinGPT 预测去重脚本**：新增 `scripts/dedupe_fingpt_predictions.py`，按 `(ticker, prediction_date)` 保留最新 `id`、删除重复行，并尝试补齐唯一索引 `ux_fingpt_ticker_date`；用于历史数据清理与回溯一致性。
- **集成中枢运维指引**：FinGPT 运维面板增加去重脚本执行提示（仅文案），方便现场快速清理历史重复数据并让唯一键落地。
- **FinGPT 重复组只读预览**：扩展 `FinGPTPersistencePort` 支持 `duplicate_*_groups` 统计；新增 `GET /api/v1/fingpt/dupes`（支持 `ticker`/`sample`），并在集成中枢 FinGPT 运维面板增加一键预览重复组，用于决定是否执行去重脚本。
- **FinGPT 去重写入 API（受控）**：新增 `POST /api/v1/fingpt/dedupe/apply`（需要数据入库权限），服务端执行 predictions/sentiments 去重（保留最新 id）；用于无法进入服务器命令行时的应急修复。
- **集成中枢一键去重**：FinGPT 运维面板增加「执行去重」按钮，默认二次确认并可选按 `ticker` 过滤；调用受控 API `POST /api/v1/fingpt/dedupe/apply`，仅具备数据入库权限的账号可用。
- **FinGPT 记录审计元数据**：为 `fingpt_predictions` / `fingpt_sentiment` 增加 `source` / `source_ref` 字段与索引（按来源/时间查询更快）；写入端显式传入来源（研究图 `sentiment_analyst`、`ai_analyze` 等），老库通过 `summary` 前缀回填部分来源，提升可追溯性与数据质量。
- **集成中枢表格化运维视图**：FinGPT 运维面板在保留 JSON 的同时，增加「预测/情感」表格摘要渲染，并支持按 `source`（research_graph/ai_analyze/unknown）过滤查询，提升审计效率与可读性。
- **FinGPT 时间窗过滤（性能）**：`/api/v1/fingpt/predictions` 与 `/api/v1/fingpt/sentiments` 新增 `since_hours` 参数（基于 `created_at >= NOW()-INTERVAL ...`）；集成中枢运维面板增加「近 24h / 近 7d」筛选，减少大表扫描与噪声展示。
- **FinGPT 运维审计体验**：集成中枢运维表格增加“查看全文”弹窗与“一键复制全文”，便于复盘与审计时快速查看 `analysis_summary/summary` 原文，而不必手动在 JSON 中滚动查找。
- **FinGPT 审计时间线**：集成中枢 FinGPT 运维表格新增 `created_at` 列，并提供「近 1h」时间窗筛选；弹窗 meta 同步展示创建时间，便于按时间线追溯写入来源与事件。
- **FinGPT 审计复制体验**：运维表格 `created_at` 支持一键复制；详情弹窗“复制全文”升级为复制 Markdown（title+meta+正文），便于审计留档与复盘记录。
- **修复 Too many connections（SQLAlchemy）**：进一步下调 SQLAlchemy MySQL 连接池默认值（`DB_POOL_SIZE`/`DB_MAX_OVERFLOW` 默认 2/0，`DB_POOL_TIMEOUT` 默认 10s），并设置 `pool_reset_on_return=rollback`，优先保证在多进程/多 worker 下不冲爆 MySQL `max_connections`；需要更高吞吐时再通过环境变量显式调大。
- **修复连接泄漏（raw DBAPI）**：为 `mysql_basic_market_data_repository` 的多处 fallback raw SQL 分支补齐 `finally: cur.close()/conn.close()`（含异常重连路径），避免连接借出后未归还导致 `Threads_connected` 长期高位与触发 (1040, Too many connections)。
- **修复连接泄漏（raw DBAPI）**：为 `mysql_moments_repository` 的 `list_feed`/`toggle_like` 补齐 `finally: cur.close()/conn.close()`（含异常重连路径的游标关闭），并为 `mysql_investment_manager_repository` 的 raw SQL 分支补齐游标关闭，减少高频查询/操作场景下连接与游标资源泄漏风险。
- **修复连接泄漏（raw DBAPI）**：为 `mysql_signal_flag_pool_repository` 的 `list_dates/get_pool` 补齐游标关闭（含异常重连路径），并为 `mysql_analysis_report_repository` 的异常重连路径补齐“重连前关闭旧游标”，进一步降低连接/游标长期堆积导致 MySQL 连接数飙升风险。
- **今日操盘台（用户价值路线 MVP）**：新增 `DailyWorkbenchService` 聚合市场情绪、自选股健康分、信号旗候选、模拟观察单、风控卡片与 FinGPT 证据链；新增 `GET /api/v1/daily-workbench` 与页面 `/`（原首页迁至 `/dashboard`），顶栏增加“今日操盘台/原首页”入口，降低用户在多功能之间跳转的决策成本。
- **自选股智能体（用户价值路线第二优先级）**：新增 `WatchlistAgentService` 聚合自选股/分组行情，输出趋势、量能、新闻、基本面、风险五维健康分、异动解释、分组雷达与行动链接；新增 `GET /api/v1/watchlist/agent`，并升级 `/self-stocks` 页面展示健康分、风险标签、分组雷达和一键详情/AI 分析/投委会/回测入口。
- **买卖计划与风控卡片（用户价值路线第三优先级）**：新增 `TradePlanService` 将行情、近 180 日历史波动与 `RiskApplicationService` 风控预检组合成可执行计划卡（入场价、止损、第一止盈、目标价、建议股数、仓位占比、最大亏损、失效条件、情景推演）；新增 `GET /api/v1/trade-plan`，并在个股详情页增加“买卖计划与风控卡片”模块，自选页增加直达买卖计划入口。
- **信号到模拟交易闭环（用户价值路线第四优先级）**：新增 `SignalObservationService`（轻量 JSON 持久化 `instance/signal_observations.json`）记录信号观察单的入场价、来源、理由、止损/目标、当前价、最大收益、最大回撤与触发状态；新增 `GET/POST /api/v1/signal-observations`、`POST /api/v1/signal-observations/<id>/close` 与 `GET /api/v1/signal-observations/stats`；新增页面 `/signal-observations`，并在信号旗、今日操盘台、自选股智能体中加入“加入观察单/查看观察单”入口。
- **AI 可信度与证据链（用户价值路线第五优先级）**：新增 `AiEvidenceService` 聚合行情快照、新闻、FinGPT 预测/情感、模拟观察单、预测校准摘要、Bull/Bear 证据与用户反馈（轻量 JSON 持久化 `instance/ai_evidence_feedback.json`）；新增 `GET /api/v1/ai/evidence`、`GET /api/v1/ai/evidence/calibration`、`POST /api/v1/ai/evidence/feedback`；AI 个股分析页与个股详情页新增“AI 可信证据链”展示与有用/无用/一般反馈入口。
