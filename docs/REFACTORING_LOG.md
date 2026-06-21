# Refactoring Log

## 2026-06-13 — Phase 16/17 Runtime Compatibility & Bootstrap Refactor

### Goal
Complete Phase 16/17 runtime compatibility cleanup after the physical service migration, with focus on service wiring, declarative route registration, Flask bootstrap stability, and smoke-testable API endpoints.

### Changes
- Added compatibility shims for legacy `app/application/services/*` imports that still appeared in route loaders, Celery tasks, and old presentation modules.
- Fixed `create_app()` bootstrap failures caused by local variable shadowing and stale Phase 16 imports.
- Replaced incorrect `ApiV1Context.services` usage in newly registered declarative routes with the global `ServiceRegistry`.
- Registered missing Phase 16 service factories:
  - `data_lake_manager`
  - `legacy_migration_service`
  - `strategy_wizard_service`
  - `immune_agent_service`
- Fixed Phase 16 domain schema gaps:
  - Added `MarketRegime` to `app/domain/data_truth/guardian_schema.py`.
  - Added minimal `ExecutionProfile` / `MarketDepthSnapshot` models under `app/domain/monitoring/`.
  - Added minimal `StrategySpec` and `SymbioticExecution` schemas for Phase 16/17 imports.
  - Added minimal `StressTestService` for immune simulations.
- Fixed `ImmunityThreat` compatibility:
  - Added default fields.
  - Added `from_dict()`.
  - Restored `asdict` import for synthetic fill serialization.
- Fixed `ModuleLocalMemory` compatibility surface for portfolio memory consumers:
  - `remember_lesson()`
  - `recall_lessons()`
  - `load_all()`
  - `get_memory_stats()`
- Fixed prompt feedback cold start:
  - `PromptEvolutionService.record_feedback()` now seeds an initial prompt before evolving.
- Fixed Alpha Marketplace access:
  - Added public `AlphaMarketplaceService.wallet` property.
- Fixed `routes_v1_data_lake.py` API paths:
  - `/api/v1/data-lake/health`
  - `/api/v1/data-lake/migrate`
  - `/api/v1/data-lake/verify/<symbol>`
- Added a small Flask/Werkzeug compatibility shim for `werkzeug.__version__` so `Flask.test_client()` works in the current dependency set.

### Files Modified
- `app/bootstrap.py`
- `app/bootstrap_components/wiring_market.py`
- `app/bootstrap_components/wiring_ai.py`
- `app/bootstrap_components/presentation.py`
- `app/presentation/api/routes_v1_data_lake.py`
- `app/presentation/api/routes_v1_strategy_wizard.py`
- `app/presentation/api/routes_v1_ai_evidence.py`
- `app/presentation/api/routes_v1_signal_observations.py`
- `app/presentation/api/routes_v1_trade_plan.py`
- `app/presentation/api/routes_v1_user_profile.py`
- `app/presentation/api/routes_v1_provenance.py`
- `app/application/events/bridge.py`
- `app/application/services/immune/immune_agent_service.py`
- `app/modules/ai_agent/services/prompt_evolution_service.py`
- `app/modules/ai_agent/services/ai/decision_feedback_service.py`
- `app/core/mesh/module_local_memory.py`
- `app/core/data_source_registry.py`
- `app/domain/data_truth/guardian_schema.py`
- `app/domain/strategy/strategy_spec.py`
- `app/domain/mesh/borderless_schema.py`
- `app/domain/monitoring/__init__.py`
- `app/domain/monitoring/execution_profile.py`
- `app/domain/monitoring/price_tracer.py`
- `app/domain/risk/risk_companion_models.py`
- `app/modules/system/services/risk/risk_companion_service.py`
- `app/modules/strategy/services/strategy/scenario_optimizer_service.py`
- `app/modules/strategy/services/analytics/stress_tester.py`
- `app/application/services/alpha/alpha_marketplace_service.py`
- `app/application/services/portfolio/portfolio_local_memory.py`
- Legacy `app/application/services/*` compatibility shim files for old imports.

### Verification
- `py_compile` passed for changed Phase 16/17 compatibility files.
- Service resolution passed for:
  - `DataLakeManager`
  - `LegacyDataMigrationService`
  - `StrategyWizardService`
  - `ImmuneAgentService`
  - `AlphaMarketplaceService`
  - `PromptEvolutionService`
  - `PortfolioApplicationService`
- Declarative route discovery passed for:
  - `data_lake`
  - `alpha_marketplace`
  - `truth_badge`
  - `data_verify`
- Flask route smoke test passed:
  - `GET /api/v1/data-lake/health`
  - `200 True ['firewall_status', 'performance', 'primary', 'storage_mode']`
- Alpha Marketplace smoke test passed:
  - token mint/list/purchase flow returned `active` order.
- `create_app()` boots successfully:
  - `rules 634`
  - `token_routes True`
  - `provenance_routes True`
- Graphify updated:
  - `63385 nodes`
  - `121554 edges`
  - `3954 communities`

## 2026-06-13 04:31 — Moments Feed and Investment Manager Leaderboard 400 Fix

### Problem
Runtime logs showed two API endpoints returning HTTP 400:

- `GET /api/v1/moments/feed?limit=30`
- `GET /api/v1/investment-managers/leaderboard?period=day`

### Root Causes
- `moments_service` factory still imported a stale legacy path: `app.application.services.social.moments_service`.
- `MomentsService` constructor expected positional repository injection, but the factory used `repository=...`.
- MySQL raw cursors returned tuples, while `MySQLMomentsRepository.list_feed()` called `dict(row)`.
- `MySQLMomentsRepository.toggle_like()` indexed raw cursor rows as dictionaries with `fetchone()["cnt"]`.
- `MySQLInvestmentManagerRepository.trade_stats_by_manager()` indexed raw cursor rows as dictionaries.
- The leaderboard route assumed `trade_stats_by_manager()` always returned a dict.

### Changes
- Added legacy compatibility shim:
  - `app/application/services/social/moments_service.py`
  - `app/application/services/social/__init__.py`
- Fixed `moments_service` factory to use the real `MomentsService(repo)` constructor.
- Fixed `investment_manager_service` factory to pass required constructor dependencies:
  - repository
  - stock cache
  - signal flag pool repository
- Added MySQL tuple-row helpers:
  - `MySQLMomentsRepository._row_to_dict()`
  - `MySQLInvestmentManagerRepository._row_to_dict()`
- Updated MySQL repository row conversions:
  - `moments_posts` feed rows now convert cursor tuples to dicts.
  - `moment_likes` count rows now convert cursor tuples to dicts.
  - `manager_trades` aggregate rows now convert cursor tuples to dicts.
- Hardened `routes_v1_investment_managers.py` aggregate calculation to accept either dict or iterable rows.

### Verification
- `py_compile` passed for changed repository and route files.
- Service resolution passed:
  - `MomentsService`
  - `InvestmentManagerService`
- Smoke test with login decorator bypassed for service-layer verification:
  - `GET /api/v1/moments/feed?limit=30` returned `200 True ['data', 'status']`
  - `GET /api/v1/investment-managers/leaderboard?period=day` returned `200 True ['data', 'status']`

- Auth blueprint still reports “not configured” when auth services are unavailable.
- Qlib warmup can emit pre-existing dependency/runtime warnings, but it no longer blocks `create_app()`.
- Endpoints decorated with `@login_required` require an authenticated session for full HTTP smoke tests.


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

# 项目重构修改记录 (2026-04-08)

## 1. 架构整体优化
- **代码内聚**：核心业务逻辑、策略模型及数据库访问层已全部迁入 `app/` 目录。
- **存储规范**：统一所有 SQLite 数据库存储于根目录 `instance/` 文件夹。
- **解耦设计**：完全移除了 `app` 层对 `scripts/` 下遗留 Python 脚本的 subprocess 调用，改为直接类引用。

## 2. 行情系统重构 (Market Infrastructure)
- **多源网关**：实现 `MultiSourceMarketProvider`，支持 `Tencent` (主用) -> `Sohu` (备用) -> `Akshare` (兜底) 的自动故障切换。
- **TDX 集成**：历史数据正式接入 **通达信 (TDX)** 行情服务器，大幅提升 K 线获取速度。
- **双保险历史**：`get_stock_history` 采用 `Cache-First` 策略，缺失数据自动通过 TDX 补全并反向填充至本地 SQLite。

## 3. 选股与回测引擎 (Trading Core)
- **情绪路由**：`StrategyApplicationService` 具备大盘感知能力。`smart` 模式下自动分析沪深 300 状态，动态匹配 `趋势突破`、`均值回归` 或 `恐慌抄底` 策略组。
- **全模型集成**：迁移并规范化了 40+ 顶级机构策略模型至 `app/models/`，实现了统一的接口规范。
- **原生回测**：实现了基于新策略模型的原生回测模拟器，支持完整的买卖流水和指标统计。

## 4. 数据库性能调优
- **并发优化**：缓存库开启 `WAL (Write-Ahead Logging)` 模式，支持高频并发读写。
- **批量写入**：所有行情存入操作均优化为 `executemany` 批处理，毫秒级完成全市场更新。
- **激进查询**：优化 `get_all_stocks` 逻辑，确保在非交易时间也能返回最后一次有效的市场快照。

## 5. 后台自动化服务
- **全市场扫描器**：新增 `ScannerApplicationService`。系统启动后会自动在后台轮询全市场 5000+ 股票行情，确保存储库始终新鲜。
- **冷启动保障**：实现 `CORE_SEEDS` 种子机制，确保空库状态下主页也能立即显示核心权重股。

## 6. 关键文件变更
- `app/infrastructure/database/stock_cache_db.py` (新增: 统一缓存层)
- `app/application/services/scanner_service.py` (新增: 后台扫描器)
- `app/infrastructure/providers/market_data.py` (重写: 行情网关)
- `app/infrastructure/providers/strategies.py` (重写: 策略引擎对接)
- `app/models/__init__.py` (更新: 全局策略注册中心)
- `app/bootstrap.py` (更新: 依赖注入与后台服务启动)

---

## 7. 第二阶段重构记录 (2026-04-09)

### 7.1 路由层职责收敛
- 将 `markets/sentiment`、`markets/movements`、`stocks/<symbol>/analysis` 的业务拼装逻辑从 `presentation` 下沉至 `application`。
- `routes.py`仅保留参数解析、鉴权与响应封装，降低控制器复杂度。

### 7.2 应用服务扩展
- 新增 `StockAnalysisService`，统一个股分析视图模型构建。
- 扩展 `MarketApplicationService`：
  - `get_sentiment()`：集中市场情绪指标计算。
  - `get_movements()`：集中异动数据生成规则。
- 修复 `MarketApplicationService` 中 `timedelta` 缺失导入问题。

### 7.3 启动与配置工程化
- `AppSettings` 新增 `enable_background_scanner` 开关（环境变量：`ENABLE_BACKGROUND_SCANNER`）。
- `bootstrap` 中扫描器启动增加开关与 debug-reloader 防重复启动保护。
- `run.py` 移除硬编码 `debug=True`，改为使用应用配置。

### 7.4 scripts 依赖迁移进度
- `app/infrastructure/providers/strategies.py` 已由 `scripts.stock_cache_db` 切换为 `app/infrastructure/database/stock_cache_db.py`。
- 历史数据读取调用改为日期区间模式，修复缓存接口参数不一致问题。

### 7.5 scripts 依赖收口（持续推进）
- 新增 `app/infrastructure/adapters/legacy_tdx_adapter.py`，将 TDX 遗留连接能力封装为适配器。
- `app/infrastructure/providers/market_data.py` 不再直接导入 `scripts.tdx_connect_manager`，改为依赖适配器层。
- 当前 `app/` 内对 `scripts` 的直接引用已收敛到单一文件（`legacy_tdx_adapter.py`），便于后续彻底替换。

### 7.6 全局导入副作用治理
- `bootstrap` 移除 `register_legacy_scripts()` 调用，不再通过全局 `sys.path` 注入 `scripts/`。
- `legacy_tdx_adapter` 改为局部按文件路径加载 `tdx_connect_manager.py`（`importlib`），将 legacy 依赖限制在适配器内部。
- `AppSettings` 移除未再使用的 `legacy_scripts_dir` 字段，降低配置冗余。

### 7.7 Legacy 桥接层退役清理
- 确认 `register_legacy_scripts` 在业务代码中已无调用后，退役旧桥接文件 `app/infrastructure/legacy.py`。
- 保留 legacy 接入能力在适配器层（`app/infrastructure/adapters/*`），避免“全局桥接 + 局部适配”双轨并存。

### 7.8 TDX 端口抽象与测试骨架
- 为 TDX 连接能力引入显式端口协议，降低 `provider` 对具体适配器类的编译期依赖。
- `market_data` 改为依赖抽象端口并通过工厂函数注入默认实现，提升可替换性与可测试性。
- 增加最小测试骨架，覆盖端口可用性与 provider 在无 TDX 时的降级路径。

### 7.9 测试稳定性修正
- 在 `provider` 降级测试中屏蔽实时行情网络调用，避免测试依赖外网环境导致不稳定。
- 测试入参统一使用领域枚举 `MarketCode`，保持与应用层契约一致。

### 7.10 QuoteGateway 端口抽象
- 为腾讯行情 HTTP 调用抽象 `QuoteGateway` 端口，隔离 `provider` 对 `requests` 的直接依赖。
- 新增基础设施适配器实现默认网关，并通过依赖注入接入 `MultiSourceMarketProvider`。
- 增加网关注入后的最小回归测试，验证 provider 在可控输入下的解析与输出结构。

### 7.11 Provider 解析职责内聚
- 在 `market_data` 内新增腾讯返回解析函数，集中处理异常行/字段越界，避免网络层与解析层耦合。
- 通过 `FakeQuoteGateway` 测试验证注入后解析链路可用，确保后续替换网关实现时不影响上层服务。

### 7.12 腾讯行情 Mapper 抽离
- 将腾讯行情字段下标解析从 `provider` 抽离为独立 Mapper，减少单类复杂度并提升复用性。
- Provider 仅负责调用网关与编排流程，行情字段容错逻辑统一交由 Mapper 处理。
- 增加异常样本测试（脏行、缺字段、非数字字段），确保解析层鲁棒性。

### 7.13 Mapper 测试覆盖增强
- 新增 `test_tencent_quote_mapper.py`，覆盖有效行解析与三类异常输入拒绝逻辑。
- 将解析行为从“静默散落在 Provider 中”转为“集中在 Mapper + 单测保护”，降低后续字段变更风险。

### 7.14 SymbolNormalizer 规则抽离
- 将 `market_data` 中代码归一化与交易所前缀判定逻辑抽离为独立 Normalizer。
- Provider 改为依赖 Normalizer 组件，降低类职责耦合并提升规则可测试性。
- 增加沪市/深市/科创板及异常输入测试，确保代码映射规则稳定。

### 7.15 归一化规则测试补充
- 新增 `test_symbol_normalizer.py`，覆盖标准代码、科创板、带前缀输入与非法输入回退逻辑。
- 将交易所前缀拼接统一交由 Normalizer 管理，避免多个调用点出现规则漂移。

### 7.16 StockCache 注入化改造
- 将 `StockCache` 从隐式单例改为显式实例，消除跨模块共享状态带来的隐性耦合。
- 保留兼容入口 `default()` 用于渐进迁移，避免一次性改动过大影响现有调用方。
- Provider/Service 支持外部注入缓存实例，提升可测试性与替换能力。

### 7.17 Cache 迁移回归验证
- 新增 `test_stock_cache_injection.py`，验证显式实例非单例、`default()` 兼容共享语义、Provider 注入绑定行为。
- 通过测试锁定“新旧两套使用方式”契约，降低迁移窗口期回归风险。

### 7.18 Provider 状态实例化
- 将 `MultiSourceMarketProvider` 的 TDX 连接缓存从类级状态迁移为实例级状态，避免跨实例共享副作用。
- 保持延迟初始化策略不变，在首次需要时构建 TDX 连接适配器。
- 增加多实例隔离测试，验证不同 Provider 实例之间状态互不污染。

### 7.19 Provider 多实例回归测试
- 新增 `test_market_provider_instance_state.py`，验证同一实例复用连接、不同实例分别初始化连接。
- 通过工厂计数断言确保实例级状态生效，避免后续重构回退到类级共享状态。

### 7.20 Scanner 生命周期治理
- 为 `ScannerApplicationService` 增加显式 `stop()` 与运行状态查询能力，避免后台线程失控。
- 应用启动时保留自动启动逻辑，应用退出时通过钩子执行优雅停止。
- 补充生命周期测试，验证启动幂等与停止状态切换行为。

### 7.21 Scanner 优雅退出接入
- `scanner_service` 新增线程句柄管理、`stop_background_scan()` 与 `is_running()`。
- `bootstrap` 在启用扫描器时注册进程退出钩子，确保应用结束时主动请求扫描线程停止。
- 新增 `test_scanner_lifecycle.py`，覆盖“启动幂等 + 停止生效”关键路径。

### 7.22 应用异常体系落地
- 新增 `ApplicationError` 基类与常见语义子类（参数校验、鉴权、资源不存在、外部服务异常）。
- 明确应用层异常与 HTTP 映射边界，避免路由层散落返回格式不一致。
- 通过统一异常对象承载状态码、错误码、详情字段，便于前后端联调与日志检索。

### 7.23 API 全局错误映射
- 新增 `presentation/api/error_handlers.py`，注册应用异常与未知异常的统一 JSON 响应格式。
- `routes.py` 在参数校验场景改为抛出 `ValidationError`，由全局处理器统一转 HTTP 400。
- 新增 `test_api_error_handlers.py`，验证业务异常与未知异常映射结果。

### 7.24 错误映射测试去环境依赖
- 由于当前 Flask/Werkzeug 版本组合下 `test_client()` 存在兼容问题，异常映射测试改为纯函数映射断言。
- 在 `error_handlers` 中显式导出 `map_application_error` 与 `map_unexpected_error`，保持处理逻辑可测试且与运行时一致。

### 7.25 请求参数解析器统一
- 将 API 中分散的整型参数解析逻辑抽离为统一解析器，支持默认值、最小值校验与统一异常抛出。
- 路由层改为调用解析器，减少重复 `try/except` 和隐式类型转换行为。
- 为解析器新增纯函数测试，确保参数错误时返回一致的 `ValidationError` 语义。

### 7.26 参数解析规则扩展
- 在统一解析器中补充浮点参数解析能力，用于回测资金等数值参数统一校验。
- `strategies/select`、`long-term-select`、`selector/run`、`backtest` 等接口已切换到统一解析器入口。
- 新增 `test_request_parsers.py` 覆盖默认值、格式错误与最小值约束场景。

### 7.27 API 成功响应结构收敛
- 将成功响应结构统一为 `status + data + meta`，减少历史接口中的重复顶层字段。
- 路由层统一通过响应构建器输出，弱化“不同接口不同包裹方式”的维护成本。
- 保留健康检查等轻量接口的原样输出，避免无意义改动扩大影响面。

### 7.28 响应构建器测试补齐
- 新增 `response_builders.py`，将成功响应结构构建逻辑独立为纯函数。
- 新增 `test_response_builders.py`，覆盖带 `meta` 与无 `meta` 两类输出。
- 路由层 `_ok_response/_ok_collection/_ok_resource` 已统一复用构建器，默认不再输出重复业务别名字段。

### 7.29 响应兼容开关
- 新增 `ENABLE_API_LEGACY_RESPONSE_FIELDS` 配置开关，用于按需恢复历史别名字段（如 `stocks`、`candidates`）。
- 默认保持新结构 `status + data + meta`，开启兼容时在顶层追加旧字段，降低前端切换风险。
- 路由响应封装器支持按开关切换，避免在各接口散落兼容分支逻辑。

### 7.30 兼容开关测试补齐
- 在 `response_builders` 中新增别名注入测试，覆盖开关开启/关闭两种分支。
- 通过纯函数测试锁定兼容行为，减少后续接口调整对前端兼容模式的回归风险。

### 7.31 scripts 运行时依赖清零
- `app/config.py` 模板目录切换到 `app/presentation/web/templates`，并将用户/自选/分组种子文件目录切到 `instance/`。
- `legacy_tdx_adapter` 改为无 scripts 依赖占位实现，TDX 仅作为可选能力，不再要求运行时加载 `scripts`。
- `app/presentation/web/templates` 新增内置页面模板（登录、首页、全景、回测、选股、AI等），页面渲染不再读取 `scripts/templates`。

### 7.32 多市场行情与历史落盘
- `MarketCode` 增加 `CRYPTO` 市场编码。
- `market_data` 实现 `CN + HK + US + CRYPTO` 多市场实时行情：
  - CN: 腾讯行情链路；
  - HK/US: yfinance；
  - CRYPTO: Binance 24hr ticker。
- 历史数据链路实现多市场落盘：US/HK 使用 yfinance history，CRYPTO 使用 Binance klines，均写入统一 cache。

### 7.33 盘中股票池与AI分析能力
- 新增 `PoolApplicationService`，支持基于市场状态 + 策略结果生成盘中动态股票池。
- 新增 `TradingAgentsAdapter`（本地 Ollama 调用 + TradingAgents 路径配置）与 `AiAnalysisService`。
- API 新增：
  - `/api/v1/pool/<market>/live`
  - `/api/v1/ai/analyze`
  - `/api/v1/ai/report`
- 页面新增 `/ai-analysis`，支持发起个股 AI 分析。

### 7.34 个股详情新闻增强
- `news provider` 扩展多市场新闻能力（CN/Akshare，US/HK/yfinance，Crypto 占位新闻）。
- 增加 `get_industry_news` 行业新闻接口，并在 `StockApplicationService` 聚合返回 `industry_news` 字段。
- 个股详情 API 可同时返回个股新闻与行业新闻上下文，供详情页和 AI 分析复用。

### 7.35 服务层契约测试补充
- 新增 `test_pool_and_ai_services.py`，覆盖盘中股票池服务与 AI 分析服务的纯服务契约。
- 使用桩对象隔离外部依赖，确保核心业务编排在无网络环境下可回归。

### 7.36 TradingAgents LangGraph 可选接入
- `TradingAgentsAdapter` 在 `USE_TRADING_AGENTS_GRAPH=true` 时通过 `sys.path` 加载 `TRADING_AGENTS_PATH` 下的 `TradingAgentsGraph`，调用 `propagate` 跑完整辩论与风控链路；失败时自动回退 Ollama 单轮提示并写入 `graph_fallback_reason`。
- 支持 `TRADING_AGENTS_ANALYSTS`、`TRADING_AGENTS_ONLINE_TOOLS` 环境变量；图模式返回 `reports`/`decision` 与兼容字段 `analysis`（供 API `summary` 使用）。
- 新增 `tests/test_tradingagents_adapter.py` 覆盖摘要、交易日解析与降级行为。

### 7.37 上线前扫描与登录链路修复（2026-04-11）
- **修改记录约定**：此后凡影响行为或契约的代码变更，须在本文件追加小节（日期 + 要点），便于审计回溯。
- **登录后失败根因**：`Flask-Login` 的 `user_loader` 曾直接返回 `UserAccount`，而 `base.html` / 路由依赖 `SessionUser` 的 `role_name`、`can_manage_users()` 等 `UserMixin` 行为，导致二次请求渲染异常。已改为 `SessionUser.from_entity(account)`（`app/bootstrap.py`）。
- **后台扫描器**：恢复尊重 `AppSettings.enable_background_scanner`（`ENABLE_BACKGROUND_SCANNER`）；`FLASK_DEBUG=1` 时仅在 `WERKZEUG_RUN_MAIN=true` 子进程启动，避免 debug reloader 双启线程。
- **工程扫描摘要**（静态核对）：认证 `AuthService.authenticate` + `SessionUser` 登录一致；`UserRepository.get_by_id` 与 `SQLiteUserRepository` 实现一致；API 蓝图大量 `@login_required` 依赖 `current_user.role` 等字段，与 `SessionUser` 对齐；`configure_quant_tools` 仍在服务装配后调用；量化工具门面 `MarketDataAccess` / `StrategyToolBridge` 与 `StrategyApplicationService` 签名一致。
- **测试**：新增 `tests/test_auth_login_flow.py`（POST `/login` 后 GET `/` 应 200 且含用户名）；兼容当前环境对 `werkzeug.__version__` 的缺失（为 Flask 2.0 `test_client` 打补丁）。

### 7.38 `.cursorrules` 扩充（2026-04-11）
- 增补：**变更须写入 `REFACTORING_LOG.md`** 的硬性约定。
- 增补：**编码规范**（UTF-8、PEP 8、类型提示、命名与日志约定等）。
- 增补：**面向对象六项设计原则**（SRP、OCP、LSP、ISP、DIP、迪米特），与架构分层表述对齐。
- 原有 TradingAgents / Tool / 市场范围等条目保留并归入「量化与 Agent 规则」小节。

### 7.39 页面「无响应」与静态资源路径（2026-04-11）
- **现象**：`run.py` 已监听但浏览器长时间白屏/无响应。
- **原因 1**：`base.html` 在 `<head>` 同步拉取 Google Fonts + StackPath Bootstrap CSS，CDN 不可达时阻塞首屏绘制。
- **处理**：字体与 Bootstrap CSS 改为 `media="print" onload="this.media='all'"` 非阻塞加载；Bootstrap 样式与 JS、jQuery 改为 **jsDelivr**；底部脚本保持**同步顺序**（避免 `defer` 导致子模板 `extra_js` 早于 jQuery 执行）。
- **原因 2**：`Flask` 构造时写死 `static_folder=presentation/web/static`（目录不存在），与 `AppSettings.static_folder`（项目根 `static/`）不一致。
- **处理**：`create_app` 使用 `settings.template_folder` / `settings.static_folder` 绝对路径，并在启动时 `mkdir` 确保静态目录存在。
- **`run.py`**：开发服务增加 `threaded=True`，降低单次慢 API 阻塞其它请求的概率。

### 7.40 登录后 Chrome「无法处理请求」排查（2026-04-11）
- **现象**：登录成功跳转后，Chrome 提示 *This page isn't working / unable to handle this request*（多为 HTTP 500 或连接异常）。
- **处理**：默认关闭 `login_user(..., remember=True)`，改为仅当表单勾选 `remember_me=on` 时启用「记住我」Cookie，降低 Flask-Login 持久化 Cookie 在部分环境下的异常概率。
- **处理**：`LoginManager.session_protection` 设为 `basic`；`SESSION_COOKIE_SAMESITE` / `REMEMBER_COOKIE_SAMESITE` 默认 `Lax`。
- **处理**：`user_loader` 整体 `try/except`，避免数据库瞬时错误直接导致未捕获 500。
- **页面**：`login.html` 增加可选「保持登录」勾选；登录页 Google Fonts 改为非阻塞加载（与 `base.html` 策略一致）。

### 7.41 登录 500：`get_by_id` 与陈旧进程（2026-04-11）
- **根因（见 `instance/app.log`）**：`user_loader` 调用 `SQLiteUserRepository.get_by_id` 时，运行中解释器仍加载**旧类定义**（无 `get_by_id`），触发 `AttributeError`，Flask-Login 在解析 `current_user` 时即崩溃，所有 `@login_required` 路由返回 500。
- **处理**：`load_user` 在 `getattr(..., "get_by_id")` 不可用时回退 **`list_users` 按 id 匹配**；并整理 `bootstrap` 中 `logger` 定义位置。
- **运维**：升级代码后务必**完全退出** `run.py` 再启动；若仍异常，删除 `app/**/__pycache__` 后重启。

### 7.42 `user_loader` 改为 SQLite 直连读 users（2026-04-11）
- **背景**：部分环境仍反复 500，日志指向 `get_by_id` 缺失，说明解释器可能长期加载陈旧 `SQLiteUserRepository` 类定义，`getattr` 回退仍不够稳。
- **处理**：`bootstrap.load_user` 改为调用 `_session_user_from_db(user_repository._db_path, user_id)`，用标准库 `sqlite3` 查询 `users` 表并构造 `UserAccount` → `SessionUser`，**不再调用** Repository 上的 `get_by_id` / `list_users`。

### 7.43 个股日 K「忽高忽低」与模拟数据排查（2026-04-11）
- **根因 1（前端）**：`stock_detail.html` 在 `renderChart` 中用 `Math.random()` 由收盘价伪造 OHLC，成交量亦为随机数；API `error` 回调中亦生成随机走势。与后端真实字段无关，但会造成「假 K 线」与剧烈抖动。
- **处理**：K 线与成交量改为严格使用 `/api/v1/stocks/.../history` 返回的 `open/high/low/close/volume`（兼容 `Date`/`Open` 等别名）；失败时仅展示提示文案，**不再注入任何模拟序列**。
- **根因 2（后端）**：TDX 拉取的历史未按请求区间裁剪、未保证时间序时，图表可能异常。
- **处理**：`market_data.py` 增加 `_filter_sort_history`，对返回列表按 `start`/`end` 过滤并升序排序；写入 SQLite 前对 TDX 全量结果做排序，避免缓存内顺序混乱。
- **运维**：新增 `scripts/refresh_stock_history_cache.py`，可一键清空 `stock_history`（或按 `CN:代码` 删除）后由线上请求触发从 TDX 重拉并回写。

### 7.45 日 K 混入周末/非交易日（2026-04-11）
- **现象**：x 轴或数据行出现周六、周日及法定节假日仍带 OHLC，与真实交易日错位，造成「忽高忽低」或缺口错觉。
- **处理**：新增 `app/infrastructure/calendar/cn_sse_calendar.py`，用 **AkShare `tool_trade_date_hist_sina`** 构建上交所交易日集合（与沪深常规休市一致）；在 `_finalize_history_bars` 中对 `MarketCode.CN` **剔除非交易日**；日历不可用或日期超出覆盖范围时退化为 **仅剔除周末**。
- **前端**：`stock_detail.html` 对 `CN` 再按本地历剔除周六日，与后端双保险（节假日以前端历无法完全识别，依赖后端日历）。

### 7.44 个股 K 线仍抖动（如 300308）二次治理（2026-04-11）
- **前端**：`renderChart` 在个别索引上若 OHLC 解析失败曾回退为 `[0,0,0,0]`，在真实价格旁出现「贴地」假柱，视觉上呈剧烈忽高忽低；改为**仅保留有效 OHLCV 行**再绑轴，不再绘制零价柱。
- **后端**：TDX/SQLite 偶发重复交易日、非有限值或 high/low 与开收不自洽时，图表同样失真；新增 `_sanitize_ohlc_bar` / `_finalize_history_bars`（按日去重、包络修正、丢弃非法收盘价），在写入缓存与读缓存返回前统一执行。

### 7.47 TradingAgents 工作流：市场约束、quant_tools 注入与 Checkpoint（2026-04-11）
- **quant_tools**：新增 `SUPPORTED_MARKETS_PROMPT_BLOCK`、`list_quant_tool_names()`、`quant_tools_agent_system_suffix()`，集中声明 CN/HK/US/CRYPTO 边界与已绑定工具名，供各 Agent system prompt 拼接。
- **custom_trading_workflow**：六角色 + Supervisor + 辩论节点均拼接上述后缀；`build_custom_trading_graph(..., checkpointer=)` 支持 LangGraph `checkpointer`（默认 `MemorySaver`）。
- **research_checkpointer**：`LANGGRAPH_CHECKPOINTER=memory|postgres`，`LANGGRAPH_POSTGRES_URI` / `DATABASE_URL`；Postgres 首次 `setup()`；失败或未装依赖时回退内存。
- **TradingAgentsService**：`run_research(..., thread_id=)` 使用 `configurable.thread_id`；`aget_state` 合并 `conversation_log` 多轮时间线；`close()` 释放 Postgres 上下文。依赖增加 `langgraph-checkpoint-postgres`（生产建议配合 `psycopg[binary]` / 系统 libpq）。

### 7.46 TradingAgents 精简六角色工作流（2026-04-11）
- **新增**：`app/agents/custom_trading_workflow.py`（LangGraph）：Supervisor → Macro / Fundamental / Technical / Sentiment / Backtest Optimizer → Bull–Bear 多轮 → Risk-Seeking vs Risk-Averse 多轮 → Risk Manager；工具链绑定 `app/tools/quant_tools.py`（`get_market_data`、`run_backtest`、`get_kline_chart`、`stock_selector`、`get_user_watchlist`）。
- **新增**：`app/agents/trading_agents_service.py` 中 `TradingAgentsService.run_research(ticker, query, user_id)`，返回结构化字段 + `full_report_markdown`。
- **依赖**：根目录 `requirements.txt` 增加 `langchain-openai`、`langgraph`、`langgraph-prebuilt`；运行前仍需 `configure_quant_tools()` 与有效 LLM 环境变量（见服务内 `_default_llm`）。

### 7.48 六分析师工作流内聚至 `app.agents.research`（2026-04-11）
- **目的**：与 TradingAgents-CN / `tradingagents` 包**运行时解耦**；核心业务与六 Agent 图实现全部落在本仓库 `app/agents/research/`。
- **结构**：`state.py`（状态与 `RESEARCH_GRAPH_NODES`）、`react_loop.py`、`catalog.py`、`graph.py`（`build_custom_trading_graph`）、`report.py`（`package_full_report`）。
- **兼容**：`app/agents/custom_trading_workflow.py` 仅 re-export；`TradingAgentsService` 改为 `from .research import ...`。
- **文档**：`docs/agents_self_contained.md` 说明归属与对 CN 子目录的定位（参考可删）。

### 7.49 A 股财务与研报数据基础层（2026-04-11）
- **Provider**：`app/infrastructure/providers/cn_akshare_fundamentals.py` — AkShare 东财 `stock_financial_abstract`、`stock_*_sheet_by_report_em`（`SH`/`SZ` 前缀）、`stock_research_report_em`；按表隔离异常、行数上限、可 JSON 序列化。
- **门面**：`FundamentalDataAccess`（`app/services/data/fundamental_access.py`）；`bootstrap` 注入 `QuantToolRuntime.fundamental_access`。
- **REST**（需登录，仅 CN）：`GET /api/v1/stocks/CN/{symbol}/fundamentals`、`GET /api/v1/stocks/CN/{symbol}/research-reports?limit=`。
- **Agent 工具**：`get_cn_financial_statements`、`get_cn_research_reports`（Pydantic 含 `evidence`/`confidence`）；**Fundamental Analyst** 绑定上述两工具。

### 7.50 借鉴 TradingAgents-CN：新闻规则过滤 + `get_stock_news` 工具（2026-04-11）
- **规则引擎**：`app/services/news/relevance_filter.py`（自包含，无 pandas），评分逻辑对齐 CN `news_filter.py`。
- **数据门面**：`StockNewsAccess` → `StockApplicationService.get_stock_detail` 之个股/行业新闻（与 Web/API 同源）。
- **quant_tools**：`get_stock_news`（`relevance_score`、`filter_mode`）；**Sentiment Analyst** 绑定；`QuantToolRuntime.stock_news_access` 由 `bootstrap` 注入。

### 7.53 因子 IC 定时告警与交易员 API 收紧（2026-04-12）
- **Celery**：新增 `app.tasks.factor_ic_alerts.run_factor_ic_monitor` / `factor_ic_monitor_tick`；环境变量 `FACTOR_IC_CELERY_BEAT=1` 时 Beat 每日 18:35（Asia/Shanghai）执行；`FACTOR_IC_WARN` 默认 0.05；弱 |IC| 因子数 >0 时向 `TaskMessageStore` 推送 `factor_ic_alert`，并设 `_suppress_default_task_message` 以免与全局 `task_postrun` 重复一条。
- **消息中心**：`message_center.html` 增加 `factor_ic_alert` 样式与说明；`task_label` 注册中文简称。
- **手动巡检**：`POST /api/v1/system/factor-ic-check`（需 `ENABLE_RD_AGENT` + 研究员及以上）；量化实验室页「巡检并写入消息中心」按钮调用同上接口。
- **角色**：`SessionUser.may_trigger_server_data_ingestion`、`may_run_expensive_ai_pipeline`；`POST /api/v1/market/basic-data/refresh`、`/llm/models`、`/ai/research` 禁止交易员与访客。

### 7.52 对照 `docs/case.md` 的路线图与缺口补齐（2026-04-12）
- **文档**：新增 `docs/ROADMAP_FROM_CASE.md`，将 case 方案分阶段映射到本仓库实现状态，并与 `docs/roadmap_qlib_rd_agent.md` 交叉引用。
- **因子监控**：`FactorCatalogService.monitor_summary`；`GET /api/factor/monitor`（`quant_lab_routes`）；量化实验室页「因子健康监控」面板。
- **导航**：顶栏新增「AI 研究」分组（量化实验室、研究闭环、AI 分析、AI 研究报告）；「策略」保留回测与参数优化。
- **用户角色**：`researcher`（研究员）、`trader`（交易员）纳入创建用户校验与中文展示；`SessionUser.can_run_research_writes`；`POST /api/v1/qlib/ingest|dump_bin|update_all` 与 `POST /api/v1/rd-agent/runs`（及兼容 `POST /api/rdagent/run`）限制为管理员/开发者/研究员。

### 7.51 新闻归档存储 + 行业加权 + `probe_ticker`（2026-04-11）
- **SQLite**：`instance/news_archive.db`，`NewsArchiveRepository`（`archived_news` + `news_symbol_meta`）；替代 CN Mongo 统一新闻持久化思路。
- **轻量新闻拉取**：`StockApplicationService.get_news_snapshot`（无 180 日 K 线/指标）；`StockNewsAccess` 按 `cache_max_age_hours` / `force_refresh` 合并归档与远程。
- **增强打分**：`industry_boost_tokens` + `rank_news_items(..., industry_boost_keywords=)`。
- **工具**：`probe_ticker`（K 线 + `fetch_profile`）；REST `GET .../news-archive`（登录只读）。

---

## 8. 集成 daily_stock_analysis 核心能力 (2026-04-21)

### 8.1 领域模型与基础设施增强
- **扩展领域实体**：在 `app/domain/entities.py` 中新增 `ChipDistribution`（筹码分布）和 `TrendAnalysisResult` 实体，为深度技术分析提供数据承载。
- **行情提供者扩展**：`MarketDataProvider` 端口新增 `get_chip_distribution` 抽象方法。
- **AkShare 筹码分布实现**：在 `app/infrastructure/providers/market_data.py` 中利用 `ak.stock_cyq_em` 实现了 A 股筹码分布抓取逻辑。
- **分析枚举补全**：在 `app/domain/enums.py` 中补全了 `TrendStatus`、`VolumeStatus`、`BuySignal`、`MACDStatus` 和 `RSIStatus` 等核心分析状态枚举。

### 8.2 深度技术分析与搜索能力
- **趋势分析服务**：新建 `app/services/analysis/technical_trend_service.py`，完整移植了 DSA 的均线排列、乖离率检测、MACD 金叉/死叉及 RSI 信号逻辑。
- **网络搜索集成**：新增 `WebSearchProvider` 端口，并实现 `MultiEngineSearchProvider`，支持 **Tavily** 与 **Bocha** 双引擎全网情报搜索。
- **LangChain 工具增强**：
  - 新增 `get_chip_distribution` 工具：供 Agent 分析获利盘压力。
  - 新增 `search_web_intelligence` 工具：供 Agent 获取全网实时突发新闻与情绪。
  - `QuantToolRuntime` 与系统提示词片段同步更新以支持新工具。

### 8.3 Agent 系统进化 (LangGraph Dashboard)
- **决策仪表盘节点**：在 LangGraph 研究流程中新增 `decision_dashboard` 节点（Chief Investment Strategist）。
- **Dashboard Prompt**：引入 `app/agents/research/dashboard_prompt.py`，负责将多位分析师结论合成为结构化的“核心结论、投资评分、狙击点位、检查清单、风险提示”仪表盘。
- **报告包装优化**：`app/agents/research/report.py` 现在将“决策仪表盘”作为 Markdown 报告的首选展示区域，极大提升了 AI 分析的可读性。

### 8.4 自动化流程、验证与导入
- **智能导入服务**：新建 `app/services/import_service.py`，支持基于正则表达式的代码识别及基于 pandas 的 CSV 文件智能解析。
- **每日分析服务**：新建 `app/services/daily_analysis_service.py`，负责驱动批量自选股分析与全市场大盘复盘。
- **AI 预测验证体系**：
  - 新增 `app/infrastructure/repositories/analysis_report_repository.py`：基于 SQLite 存储 AI 预测结论（Dashboard 镜像）。
  - 新增 `app/services/validation/prediction_validator.py`：自动比对 AI 历史预测与实际行情。
- **Celery 异步任务**：新增 `app.tasks.scheduled_daily_analysis`（定时批量分析）与 `app.tasks.validate_ai_predictions`（预测准确率回测）。

### 8.5 Web 页面：能力总览（2026-04-21）
- **新增页面**：`/capabilities`（`app/presentation/web/templates/capabilities.html` + `pages.py` 路由）。
- **目的**：将行情、选股、回测、AI 研究、数据中心、消息中心等能力以卡片化入口聚合，并提供“输入代码直达个股/AI/回测”的快捷入口，降低用户找功能成本。
- **导航接入**：顶栏与全站「链路」快捷条新增“能力总览/能力”入口。

### 8.6 数据流向调整：历史/当日落盘改为通达信日K（2026-04-21）
- **目标**：历史数据与当日落盘数据统一从 `TDX_ROOT_PATH/vipdoc/*/lday/*.day` 读取；目录下股票数即“全市场股票数”。
- **新增服务**：`app/application/services/tdx_dayk_sync_service.py`
  - `full_sync_from_tdx_dayk`：**历史全量** 导入到 **MySQL `stock_history`** + `instance/qlib_export`（CSV）并可选 `dump_to_qlib_bin`。
  - `daily_sync_from_tdx_dayk`：**当日** 从通达信日K取当日 bar，写入 MySQL/CSV 并增量更新 `qlib_bin`。
- **兼容修正**：`BasicMarketDataService.backfill_stock_history_from_tdx` 旧入口保留，但内部转为调用新链路，避免“名为 MySQL 实写 SQLite”的偏差。
- **任务入口**：`app.tasks.data_backfill_tasks.backfill_all_history_tdx` 语义更新为 “TDX dayk → MySQL/CSV/Qlib”；新增 `sync_today_history_tdx` 当日落盘任务。

### 8.7 CN 代码唯一键升级：market+六位（2026-04-21）
- **动机**：通达信不同目录下可能存在相同 6 位 code；为避免冲突，CN 统一使用 `{market}{code6}`（`sh/sz/bj`）作为唯一标识。
- **规范**：
  - **DB/缓存键**：`CN:{market}{code6}`（如 `CN:sh600519`、`CN:sz000001`、`CN:bj430047`）
  - **Qlib instrument/CSV 文件名**：`SH/SZ/BJ + 6 位`（如 `SH600519.csv`）
- **落地范围**：`SymbolNormalizer.to_db_code`、通达信全量/当日同步、StockCache 历史读取、Qlib CN instrument 映射等关键路径已切换到新键；旧的“仅 6 位”输入仍兼容（自动推断 sh/sz，bj 建议显式）。

### 8.8 通达信基础数据入库：板块/股票名称（2026-04-22）
- **新增 MySQL 表**：
  - `cn_stock_basics`：通达信 `.tnf` 股票列表解析得到的 `symbol(=sh/sz/bj+6位)` 与 `name`
  - `tdx_blocks` / `tdx_block_items`：`block_*.dat` 板块与成分股映射
- **新增导入服务**：`app/application/services/tdx_base_data_service.py`，`ingest_all_to_mysql()` 一键导入上述基础数据。
- **新增 API**：`POST /api/v1/tdx/base-data/ingest`、`GET /api/v1/tdx/blocks`、`GET /api/v1/tdx/blocks/<kind>/<name>/members`。
- **新增页面**：`/tdx-blocks`（导航：数据 → 通达信板块），支持一键入库与浏览成分股。
