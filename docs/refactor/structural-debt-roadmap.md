# 结构性技术债重构路线图

与 `REFACTORING_LOG.md` 配合，记录分阶段目标与验收标准。

## 阶段 0 — 基线（已完成）

- 配置调用点：见 `config-call-sites.md`
- 门禁：`tests/test_settings_provider.py`；`rg "AppSettings\.from_env\(\)" app` 只减不增（允许 `settings_provider.py`）

## 阶段 1 — 配置切片（已完成 `app/`）

- `app/config/slices.py`：`DataBackendSettings`、`QmtExecutionSettings`、`ThsProviderSettings`
- `get_settings()` 进程单例
- 服务注入子配置而非完整 `AppSettings`（QMT/THS 已起步）

## 阶段 2 — DI 收敛（已完成）

- 权威路径：`bootstrap_components` + `service_wiring`
- `wire_trading_execution`；`container` 仅 lazy 补位
- Celery/tasks 使用 `get_settings()`

## 阶段 3 — 路由瘦身（大部分完成）

- `routes_v1_market_core.py` — panorama / quotes / pool / movements / sentiment / headlines
- `routes_v1_stock.py` — 个股详情、K 线、财务、新闻归档等
- `routes_v1_market_aux.py` — 龙虎榜 / 研报 / pulse / basic-data refresh
- `routes_v1_task_ops.py` — Celery 任务消息与运维
- `routes_v1_strategy_copilot.py` — strategy recommend / copilot
- `routes.py` 仅注册与工厂（~130 行）

## 阶段 4 — Repository 边界（已完成）

- Port 返回 `UserAccount` 等 domain 类型
- MySQL / SQLite / Json / Async MySQL 实现对齐 Port
- 门禁：`tests/test_layer_boundaries.py` 禁止 `application` import `infrastructure.database.models`（见 `layer-boundaries.md`）

## 阶段 5 — 插件契约（已完成）

- `PluginLoadReport`、 `PLUGINS_ENABLED`、`PLUGINS_ALLOWLIST`
- 启动顺序：logging → settings → plugins

## 阶段 6 — Repository / Database 解耦（已完成）

- application 层 `infrastructure.repositories.*` / `infrastructure.database.*` 直连清零
- Port + `deps` 工厂 + bootstrap 绑定

## 阶段 7 — 领域共享与 Provider 边界（已完成）

- **7a（已完成）**：`SymbolNormalizer` 下沉至 `app/domain/shared/symbol_normalizer.py`；application 改从 domain 导入
- **7b（已完成）**：`MarketDataProvider` 经 bootstrap 绑定；application 禁止 import `infrastructure.providers.market_data`
- **7c（已完成）**：`tdx_local` / `pytdx` / `tdx_file_adapter` Port 化；application 经 `tdx_local_access` / `pytdx_access` 访问
- **7d（已完成）**：板块/基本面/async/strategies/news/backtest 等 `infrastructure.providers.*` 经 Port + bootstrap 绑定

## 阶段 8 — 适配器 / 缓存 / 解析边界（已完成）

- **8a–8e（已完成）**：见 `REFACTORING_LOG.md` 2026-05-19 各小节；application 层 infra 直连门禁全绿

## 阶段 9 — Celery / Tasks 边界（已完成）

- **9a（已完成）**：`bootstrap_components/infrastructure_binding.py` 共享绑定；`tasks/task_wiring.py`；`market_tasks` / `data_backfill_tasks` / `factor_ic_alerts` 迁移；domain 符号映射；`tests/test_task_layer_boundaries.py`（9a 子集）
- **9b（已完成）**：tasks 禁止 `infrastructure.providers.*` 直连，改经 `task_wiring` / application helpers（scanner、signal_flag、news_backfill、tdx_gpcw、market_history）；`providers.create_ta_indicator_provider` / `create_cn_tdx_gpcw_provider`
- **9c（已完成）**：tasks 禁止 `database` / `messaging` / `rdagent` / 非 `deps` 的 `repositories` 直连；扩展 `deps` 工厂与 `task_wiring`（stock cache、GPCW repo、RD-Agent 编排）；`celery_app` 消息 store 改经 task_wiring
- **9d（已完成）**：tasks 禁止 `infrastructure.adapters.*` / `infrastructure.tracing` 直连；`moments_agent_reply_tasks` / `tracing_tasks` 改经 `task_wiring`；`providers.create_ollama_prompt_adapter`

## 阶段 10 — Repositories 目录整理 + TimescaleDB（已完成）

- **10a**：`common/` / `mysql/` / `sqlite/` / `postgres/` 分目录；`mysql_*` / `sqlite_*` 命名；门面迁入 `common/facades/`；根目录 shim 兼容旧 import
- **10b**：TimescaleDB 连接（`postgres_settings` / `postgres_client` / `postgres_connection_adapter`）；`PostgresTimescaleBarRepository`（`market_bars` hypertable）
- **10c**：`AppSettings.postgres`、`use_timescaledb`、`timescaledb_uri`；`.env` / `.env.example` 增加 `TIMESCALEDB_*`；`deps.create_timescale_bar_repository` / `create_postgres_connection_port`
- **文档**：`docs/refactor/repositories-layout.md`、`docs/DATABASE_GUIDE.md` 更新

## 阶段 11 — DI 单源（已完成）

- **`service_wiring.wire_legacy_container_services`**：显式装配原 `container` mapping 中的 9 项服务（qlib / ai_analysis / investment_committee / risk / industry_chain / task_pipeline / memory / daily_workbench / trade_plan）；`wire_container_singletons` 改为 alias，不再 import `app.core.container`。
- **`tasks/auto_alpha_tasks`**：改经 `task_wiring.create_swarm_agent_service()`。
- **`app/core/container.py`**：标注仅 legacy 脚本/测试使用。

## 阶段 12 — Application 事务边界（已完成）

- **`MySQLConnectionPort`**：新增 `commit` / `rollback`；`mysql_access.mysql_commit` / `mysql_rollback` 供 application 使用。
- **Application 改动**：`hot_sector_storage_service`、`tdx_dayk_sync_service`、`tdx_base_data_service` 不再 `conn.commit()`；`ten_kings_sniper_service` 改经 `MySQLSniperRepository.get_selection_summary`。
- **门禁**：`tests/test_layer_boundaries.py` 禁止 application 内 `conn.commit` / `conn.rollback` / `._session_factory(`。

## 阶段 13 — 热点板块仓储化 + Workbench DTO（已完成）

- **`HotSectorStoragePort`** + **`MySQLHotSectorRepository`**：`em_hot_sector_*` 表 SQL 从 application 下沉至 `mysql/mysql_hot_sector_repository.py`；`deps.create_hot_sector_repository`。
- **`HotSectorStorageService`**：仅编排拉取与入库参数；路由经 deps 注入 repository。
- **`domain/dto/daily_workbench_dto.py`**：`DailyWorkbenchSnapshotDTO` 及子结构 TypedDict；`build_snapshot` 返回类型标注。
- **`wire_daily_workbench_service`**：bootstrap 装配时注入 signal_flag / observation / trade_plan 等完整依赖（与 API route deps 对齐）。

## 阶段 14 — Workbench 路由复用 + TDX 板块仓储化（已完成）

- **`routes_v1_daily_workbench`**：优先使用 `ctx.daily_workbench_service`（`require_daily_workbench_service`）；移除每请求 `new DailyWorkbenchService`。
- **`wire_daily_workbench_service`**：移至 `wire_presentation_layer_services` 之后装配，确保 `integration_stack_service` 等依赖已就绪。
- **`TdxBlockReadPort`** + **`MySQLTdxBlockRepository`**：`tdx_block_membership_cache` / `tdx_block_stats_service` 不再 application 层 raw SQL；经 `tdx_block_repository_access` + bootstrap 绑定。

## 阶段 15 — TDX 写入仓储化 + HotSector Null（已完成）

- **`TdxDaykWritePort`** / **`MySQLTdxDaykRepository`**：日 K 批量 sync session（latest dates / bars / factors / commit）；`tdx_dayk_sync_service` 不再 `mysql_connect`。
- **`TdxBaseDataWritePort`** / **`MySQLTdxBaseDataRepository`**：基础数据 ingest 事务下沉；`tdx_base_data_service` 仅组装 TNF/板块/自选参数。
- **`NullHotSectorStorageRepository`**：无 MySQL 时 `create_hot_sector_repository` 返回 Null（读空、写显式失败）。
- **`tdx_data_repository_access`** + bootstrap 绑定 dayk/base write ports。

## 阶段 16 — Qlib 导出 + 集成探针仓储化（已完成）

- **`MySQLTdxDaykRepository`** 扩展：`list_history_calendar_dates` / `list_history_stock_codes` / `fetch_history_rows`（供 Qlib bin 导出）。
- **`IntegrationProbePort`** + **`MySQLIntegrationProbeRepository`**：集成栈表行数探针；`integration_probe_access` + bootstrap 绑定。
- **Application**：`qlib_pipeline_service.mysql_to_bin_sync`、`integration_stack_service._mysql_integration_row_counts` 移除 `mysql_connect`。

## 阶段 17 — 仓储文档 + Null/Port 单测（已完成）

- **`docs/refactor/repositories-layout.md`**：索引阶段 13–16 新增 `mysql_*` 仓储、`deps` 工厂与 bootstrap Port 绑定表。
- **`tests/test_mysql_repository_ports.py`**：`NullHotSectorStorageRepository`、deps 工厂、`MySQLTdxDaykRepository` 表名校验。

## 阶段 18 — Data Router MySQL 历史 + 热点回退单测（已完成）

- **`MarketDataService._query_mysql_history`**：经 `get_tdx_dayk_write_port().fetch_history_rows` 按 sh/sz/bj 选表与日期过滤；TDX 无数据时 MySQL 回退。
- **`tests/test_data_router_mysql_history.py`**、**`tests/test_hot_sector_storage_service.py`**：Port mock 与 Null repo → live 回退。
- **`docs/QUANT_ATLAS_GUIDE.md`**：§5.1 阶段 11–17 onboarding 摘要表。

## 阶段 19 — Data Router 写入 Port 化 + 读写分离回退单测（已完成）

- **`MarketDataService._persist_to_mysql`**：`open_sync_session` → `write_bars` → `commit`；`write_backtest_result` 不再依赖构造参数 `mysql_session`。
- **`tests/test_data_router_mysql_history.py`**：持久化 session mock、`ReadWriteSplitDataService` TDX 空时 MySQL 回退。

## 阶段 20 — Data Router 构造精简 + 实时行情委托（已完成）

- **`MarketDataService`**：移除废弃 `mysql_session` / `DataSourceConfig.mysql_connection`；`get_realtime_quote` 委托 `CnRealtimeQuoteService`（A 股）。
- **`ReadWriteSplitDataService`**：读写均经 Port，构造仅保留 `tdx_root_path`。

## 阶段 21 — Scenario Optimizer MySQL 回退 + 跨市场行情（已完成）

- **`DataScenarioOptimizer`**：移除 `mysql_session`；历史研究场景经 `MarketDataService.get_history` MySQL 回退。
- **`ScenarioBasedDataService.monitor_realtime`**：委托 `MarketDataService.get_realtime_quote`。
- **`MarketDataService.get_realtime_quote`**：HK/US 等经 `get_market_data_provider()`。
- **`services/scenario_optimizer_service.py`**：路由兼容 re-export shim。

## 阶段 22 — Factor 衰减检测 + Data Optimizer 路由去 infra 直连（已完成）

- **`FactorDecayMonitor.check_decay`**：接 `FactorDecayDetector` + `decay_rate` 阈值；从 factor repo 读取指标。
- **`ScenarioBasedDataService.write_result`**：`WRITER_RESULT` 经 `MarketDataService.write_backtest_result`。
- **`data_optimizer_access`**：TDX 工厂 + `resolve_configured_tdx_root`；`routes_v1_data_optimizer` 移除 `tdx_file_adapter` 直连。

## 阶段 23 — Presentation 边界门禁 + 因子重训 + write-result API（已完成）

- **`test_layer_boundaries`**：`routes_v1_data_optimizer` 禁止 `infrastructure.providers/tdx_local` 直连。
- **`FactorDecayMonitor.trigger_retrain`**：写 experiment + 可选 `factor_retrain` swarm run。
- **`POST /data/write-result`**：WRITER_RESULT 写 MySQL Port。

## 阶段 24 — Hot Sector 路由 deps + OHLCV 校验 + 衰减日志（已完成）

- **`wire_hot_sector_storage_service`** + **`HotSectorRouteDeps`**：`routes_v1_hot_sectors` 移除 `infrastructure.repositories.deps` 直连。
- **`history_row_validator.validate_ohlcv_history_rows`**：`POST /data/write-result` 字段校验。
- **`FactorDecayMonitor._record_decay_event`**：同步 `log_decay_event`（async 实现跳过并 debug）。
- **边界测试**：hot_sectors 路由纳入 presentation 门禁白名单。

## 阶段 25 — TDX Base 读 Port 化 + Hot Sector 挂载 + 衰减异步任务（已完成）

- **`TdxBlockReadPort`** 扩展 watchlist/finance/板块列表；**`TdxBaseReadService`**；`routes_v1_tdx_base` 移除 `mysql_connect` / infra `SymbolNormalizer`。
- **`routes.py`** 重新注册 `register_hot_sector_routes`。
- **`factor_decay_tasks.log_factor_decay_event_task`**：async repo 衰减日志 Celery 落库。

## 阶段 26 — Health MySQL Port 化 + TDX Base deps + Factor Beat 钩子（已完成）

- **`SystemHealthProbeService.probe_mysql`**：`routes_v1_health` 经 `mysql_access` Port，移除 `mysql_connect` 直连。
- **`wire_tdx_base_read_service`** + **`TdxBaseRouteDeps`**：TDX Base 路由与 hot_sector 同模式。
- **`celery_app`**：注册 `factor_decay_tasks`；`log_decay_event` 由 monitor 按需 enqueue（`FACTOR_IC_CELERY_BEAT` 为 IC 巡检，见 roadmap）。

## 阶段 27 — Factor Lifecycle 任务 + Health 路由挂载（已完成）

- **`factor_lifecycle_tasks`**：Celery 同步 runner（`asyncio.run`）；修复原 `await` 语法错误；repo 经 `common.deps`。
- **`FACTOR_LIFECYCLE_CELERY_BEAT=1`**：lifecycle 日检 / IC 计算 / 归档 cleanup 三条 Beat（与 `FACTOR_IC_CELERY_BEAT` IC 告警巡检独立）。
- **`register_health_routes`** 挂入 **`routes.py`**；`/api/v1/system/health` 返回组件级探针（替代 system 简单 alias）。

## 阶段 28 — Presentation 边界扩展（已完成）

- **`legacy_routes`**：默认历史窗口经 `datetime_utils`，移除 `infrastructure.providers.market_data` 直连。
- **`task_ops_access`** + **`routes_v1_task_ops`**：Celery inspect/revoke 经 application helper（bootstrap 绑定）。
- **`SystemHealthProbeService.probe_async_queue`**：health 路由 async queue 探针下沉 application 层。
- **`test_layer_boundaries`**：legacy / task_ops / health 路由纳入 presentation 门禁。

## 阶段 29 — Memory / Monitoring / Metrics 路由（已完成）

- **`MemoryOptimizationService.list_tables`**：`routes_v1_memory` 去 `infrastructure.memory` 直连。
- **`monitoring_access`** / **`metrics_access`**：数据新鲜度与 Prometheus 指标经 bootstrap 绑定。
- **`routes_metrics.py`**：修正 import 与 JSON 响应；presentation 门禁扩展至 memory / monitoring / metrics。

## 阶段 30 — Celery Worker DB cleanup + task_wiring 懒加载（已完成）

- **`worker_db_cleanup`** + **`celery_app` signals**：任务结束释放 MySQL / scoped session；worker 启动绑定 infra helpers。
- **`task_wiring`**：repository 工厂 lazy import，降低 Celery 启动 import 扇出。

## 阶段 31 — Profile 分级 runtime config 校验（已完成）

- **`runtime_config_validator`** + **`bootstrap.create_app`**：`STRICT_BOOTSTRAP` / `DEPLOY_PROFILE` 控制 fail-fast。
- **QMT / MySQL / Celery / TDX** 按 profile 分级 warning vs error。

## 阶段 32 — Celery autodiscover + Worker STRICT 校验（已完成）

- **`celery._discover_task_modules()`** 扫描 `app.tasks.*` 替代显式 import 列表；提前 `celery_app` 别名。
- **`validate_worker_runtime_config`**：`STRICT_BOOTSTRAP=1` 时 worker 子进程 fail-fast。
- **`test_app_bootstrap`**：`BACKGROUND_POLICY` 结构与实现对齐。

## 阶段 33 / UX-1 — 统一归因 Report（已完成）

- **`UnifiedAttributionService`** + 扩展 **`AttributionReportDTO`**（style / slippage / summary）。
- **`routes_v1_attribution`**：`/attribution/analyze` 与 `/attribution/report` 返回统一结构。

## 阶段 34 / UX-2 — 智能异常预警中心（已完成）

- **`AlertCenterService`** + **`AlertEventDTO`**：TaskMessage / 数据新鲜度 / 健康探针聚合。
- **`routes_v1_alert_center`**：`/api/v1/system/alerts` 与 `/summary` 站内预警中心 MVP。

## 阶段 35 / UX-3 — 策略快照与回滚 MVP（已完成）

- **`StrategySnapshotService`** + **`StrategyDeploySnapshotDTO`**：部署时记录 code revision、settings 备份、benchmark 元数据。
- **`routes_v1_strategy_snapshots`**：`/api/v1/strategy/snapshots` 与 `/<id>/rollback`；MVP 回滚为标记 active + redeploy 指引。

## 阶段 36 / SDK Facade（已完成）

- **`QuantAtlasClient`** + **`AttributionFacade` / `AlertsFacade` / `SnapshotsFacade`**：脚本与外部集成薄入口，与 Container/API 并存。

## 阶段 37 / UX-1 前端 — 归因看板（已完成）

- **`attribution_dashboard.html`**：对接统一 `AttributionReportDTO`（style / slippage / summary）；路由 `/attribution-dashboard`。

## 阶段 38 / UX-2 前端 — 预警中心看板（已完成）

- **`alert_center.html`**：对接 `/api/v1/system/alerts`；级别/分类筛选与统计摘要；路由 `/alert-center`。

## 阶段 39 / UX-3 v2 — 快照回写 + 前端（已完成）

- **`rollback(apply_settings=True)`** 写回 `config/settings.json`；**`strategy_snapshots.html`** 管理页；**`capture_deploy_snapshot`** Celery 任务。

## 阶段 40 / UX-2 v2 — 预警通知渠道（已完成）

- **`AlertNotificationService`**：Webhook / 钉钉 / SMTP 邮件；**`POST /system/alerts/dispatch`**；导航 critical 角标。

## 阶段 41 / UX-2 v3 — Beat 定时推送（已完成）

- **`ALERT_DISPATCH_CELERY_BEAT`** + **`AlertDispatchStateStore`**：Beat 周期推送与冷却去重。

## 阶段 42 / UX-3 v3 — 部署钩子 + 代码回滚（已完成）

- **`capture_on_deploy`** 挂钩投资经理部署；**`apply_code`** 受控 git/svn checkout（prod 双开关门禁）。

## 阶段 43 / UX-2 v4 — 微信模板消息（已完成）

- **`WeChatTemplateAlertChannel`**：告警出站第四通道，与 Webhook/钉钉/邮件并列。

## 阶段 44 / UX E2E + SDK 文档（已完成）

- **`test_phase44_ux_smoke`**：归因 / 预警 / 快照 API 与看板页面冒烟；**`docs/sdk-ux-quickstart.md`**。

## 阶段 45 / UI-OPT — Decision Dashboard 升级操盘台（已完成）

- **Focus Bar + URL 上下文**：`focus_context.js`；`/api/v1/daily-workbench?symbol=`。
- **晨会三栏 + 健康条 + 决策证据**：`morning_call` / `health_banner` / `decision.evidence`。
- **快讯信号标注**：Celery `enrich_market_headlines` + `HeadlineSignalCache`；`HEADLINE_SIGNAL_CELERY_BEAT`。
- **`test_phase45_ui_opt_workbench`**：服务/API/页面/Beat 冒烟。

## 阶段 47–48 / UI-OPT — 可操作错误 + 全局健康指示（已完成）

- **`actionable_error_catalog`** + API `error.hints`；**`QCApiError`** 前端 banner。
- **`SystemHealthBannerService`** + **`GET /system/health-banner`**；导航健康灯 + 顶栏提示。
- **`test_phase47_48_ui_opt`**。

## 阶段 50 / UI-OPT — 因子对标 + 交易预检（已完成）

- **`AttributionCompareService`** + **`/attribution/compare`**；**`PreTradePreflightService`** + **`/trading/preflight`**。
- **AI 诊股 / 个股详情** 对标 UI；策略 Copilot 交易预检弹窗；**`test_phase50_compare_preflight`**。

## 阶段 57 / UI-OPT — 任务 SSE 推送（已完成）

- **`TaskEventHub`** + **`GET /system/tasks/<id>/stream`**；`task_feedback.js` EventSource 优先；**`test_phase57_task_stream`**；**`docs/ui_opt-completion.md`**。

## 阶段 56 / UI-OPT — 数据覆盖度指示（已完成）

- **`DataCoverageService`** + **`/stocks/.../data-coverage`**；分析/证据链 `data_coverage` + 置信度降权；**`test_phase56_data_coverage`**。

## 阶段 55 / UI-OPT — 全局焦点路由（已完成）

- **`FocusContextService`** + **`GET /focus/context`**；全站焦点栏 + URL/`qa:focus-change`；**`test_phase55_focus_context`**。

## 阶段 54 / UI-OPT — 数据事实化 + 结论追踪（已完成）

- **`market_fact`** + **`QCTraceLink`**；K 线/报价 `close_fact`；假设证据 `trace_ref`；**`test_phase54_market_fact_trace`**。

## 阶段 53 / UI-OPT — 假设验证分析（已完成）

- **`HypothesisEvaluationService`** + **`/ai/hypotheses`**；分析/证据 API 支持 `user_hypothesis`；**`ai_analysis.html`** 假设验证面板；**`test_phase53_hypothesis_analysis`**。

## 阶段 52 / UI-OPT — 对齐层 + K 线智能采样（已完成）

- **`DateAligner`** + **`market_time_slot`** 快讯/信号对齐；**LTTB** `stock_history` `max_points`/`width`；**`test_phase52_alignment_sampling`**。

## 阶段 51 / UI-OPT — 异步任务反馈（已完成）

- **`TaskProgressStore`** + **`GET /system/tasks/<id>/feedback`**；registry `estimated_steps`；**`QCTaskFeedback`** 任务中心轮询 UI。
- **`test_phase51_task_feedback`**。
