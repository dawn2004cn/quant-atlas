# Refactoring Log

## 2026-06-14（Phase VII 收尾：多实例路由注册 + 冒烟测试隔离）

| 维度 | 交付物 | 文件 |
|------|--------|------|
| **嵌套 Blueprint 前缀** | `optimization` / `user_tiers` / `lifecycle` / `phase18` 子 Blueprint 去掉重复的 `/api/v1`，修正双重前缀 404 | `routes_v1_optimization.py`, `routes_v1_user_tiers.py`, `routes_v1_lifecycle.py`, `routes_v1_phase18.py` |
| **路由注册** | 每次 `create_api_blueprint()` 重置 `_registered_routes`；`ai_hedge_fund` 子 Blueprint 改为函数内创建 | `routes.py`, `routes_v1_ai_hedge_fund.py` |
| **冒烟登录** | 测试 fixture 写入隔离 `users.json`（admin123），不依赖仓库 `config/users.json` 密码 | `tests/test_route_smoke_critical.py` |
| **CI** | 单条 pytest 命令跑 Phase 66–68 + smoke | `.github/workflows/ci-smoke.yml` |

## 2026-06-14（Phase VII：联邦心跳 / FedAvg 闭环 / CI 冒烟）

机构级联邦部署补齐节点心跳、FedAvg 聚合轮次与 CI 回归流水线。

| 维度 | 交付物 | 文件 |
|------|--------|------|
| **节点心跳** | `heartbeat()`、`list_nodes()` 含 stale 标记；注册 upsert | `institution_tier_service.py` |
| **FedAvg 轮次** | `run_fedavg_round()` + 持久化 aggregated model；eligible 更新过滤 | `institution_tier_service.py` |
| **集群状态** | `get_cluster_status()`；API status/heartbeat/round/model | `routes_v1_user_tiers.py` |
| **专业工作台** | 联邦 Tab：心跳、提交更新、FedAvg、集群状态 | `professional_workbench.html` |
| **可选依赖** | `requirements-compute.txt`（Polars） | `requirements-compute.txt`, `requirements.txt` |
| **CI** | GitHub Actions 冒烟：Phase 66–68 + 关键 API | `.github/workflows/ci-smoke.yml` |
| **测试** | `test_phase68_federated.py`, `test_route_smoke_critical.py` | `tests/` |

- **新 API**：`GET /institution/federated/status`；`POST /institution/federated/nodes/<id>/heartbeat`；`POST /institution/federated/aggregate/<model>/round`；`GET /institution/federated/models/<model>`

## 2026-06-14（Phase VI：复杂度治理 / 向量化计算 / ZK 披露增强）

依据 `feasibility_audit_and_roadmap.md` 复杂度治理与合规隐私计算方向推进。

| 维度 | 交付物 | 文件 |
|------|--------|------|
| **Wiring 冒烟** | `validate_wiring(registry)` 解析工厂；启动日志输出 resolved 数 | `complexity_budget_service.py`, `wiring_optimization.py` |
| **路由冒烟测试** | 启动 ≥500 路由 + 关键 factory 可解析 | `tests/test_phase67_wiring_smoke.py` |
| **向量化回测** | NumPy/Polars 双后端；`backend` 参数；结果含 `backend` 字段 | `boutique_tier_service.py`, `routes_v1_user_tiers.py` |
| **ZK 证明修复** | `verification_nonce` 持久化；`verify_stored_proof`；`public_dict()` | `compliance_service.py` |
| **上架自动证明** | `list_token` 创建 ZK proof；listing 含 `zk_proof_hash` | `alpha_marketplace_service.py` |
| **Marketplace UI** | 分级披露弹窗 + ZK 验证按钮 | `marketplace.html` |
| **API** | `POST /compliance/zk-proof/verify`；`POST /alpha/marketplace/proof/verify` | `routes_v1_optimization.py`, `routes_v1_alpha_marketplace.py` |

## 2026-06-14（Phase V：用户频谱闭环 — 审计哈希链 / Hub UI / 因子挖掘）

依据 `user_spectrum_requirements.md` 补齐五层用户能力前端入口与安全层审计链。

| 维度 | 交付物 | 文件 |
|------|--------|------|
| **审计哈希链** | `DecisionSnapshot` 增加 `content_hash` / `chain_hash`；订单级与全链验证 | `fund_tier_service.py` |
| **审计 API** | `GET /fund/audit/<order_id>/verify`；`GET /fund/audit/chain/verify` | `routes_v1_user_tiers.py` |
| **精品店挖掘** | `POST /boutique/factor-mining/run` 桥接遗传因子挖掘 | `routes_v1_user_tiers.py` |
| **用户频谱 Hub** | 五层 Tab SPA + 快捷链接 | `user_spectrum_hub.html`, `pages_ai.py`, `base.html` |
| **测试** | 哈希链完整性 / 篡改检测 / Tick 状态 / 因子挖掘 | `tests/test_phase66_user_spectrum.py` |

- **页面**：`/user-spectrum-hub`（导航：AI → 🎯 用户频谱中心）

## 2026-06-14（Phase IV：接口层 / 部署层 — Tick 推送 / Docker·K8s / 预检 UI）

依据 `feasibility_audit_and_roadmap.md` 接口层与部署层交付，补齐 Tick 级 WebSocket、私有化部署与预检 UI 闭环。

| 维度 | 交付物 | 文件 |
|------|--------|------|
| **Tick 推送** | `subscribe_ticks` / `tick_update` 事件；Tick 广播线程 + EventBus 桥接 | `websocket_adapter.py`, `tick_stream_service.py`, `realtime.py` |
| **Realtime API** | `GET /realtime/status`、`GET /realtime/ticks/status` | `routes_v1_realtime.py` |
| **预检 UI** | 个股页 POST `/trading/preflight`（ATR/合规）；专业工作台「预检→流水线」 | `stock_detail.html`, `professional_workbench.html`, `routes_v1_trading_preflight.py` |
| **私有化部署** | Docker Compose（web + worker + redis）；K8s Deployment + Redis | `deploy/docker/*`, `deploy/k8s/*` |
| **配置** | `ENABLE_TICK_WS`、`WS_TICK_INTERVAL_SEC` | `.env.example` |

- **Socket 事件**：客户端 `emit('subscribe_ticks', {symbols:['600519']})` → 接收 `tick_update`
- **部署**：`docker compose -f deploy/docker/docker-compose.yml up -d`；K8s 见 `deploy/k8s/deployment.yaml`

## 2026-06-14（Phase III：机构壁垒期 — 执行算法 / RBAC / 联邦部署 / 专业工作台）

依据 `user_spectrum_requirements.md` Phase III 完成机构级能力整合。

| 维度 | 交付物 | 文件 |
|------|--------|------|
| **执行算法** | VWAP / TWAP / Iceberg / POV 统一切片调度 | `institution_tier_service.py`, `routes_v1_user_tiers.py` |
| **RBAC** | 角色持久化 + `require_rbac` 装饰器 + 流水线权限校验 | `institution_tier_service.py`, `rbac_guard.py`, `trade_execution_pipeline_service.py` |
| **联邦部署** | 节点注册、部署配置、FedAvg 聚合 | `institution_tier_service.py` |
| **专业工作台** | 6 Tab SPA：组合优化/归因/合规/执行/流水线/联邦 | `professional_workbench.html`, `pages_ai.py`, `base.html` |
| **服务工厂** | `rbac_service`, `execution_algo_service`, `federated_deployment_service`, `market_impact_model_service` | `wiring_optimization.py` |

- **新增 API**：`POST /institution/execution/{vwap,twap,iceberg}`；`GET/POST /institution/federated/config`；`GET/POST /institution/federated/nodes`；`GET /institution/rbac/me`
- **页面**：`/professional-workbench`（导航：策略 → 🏛️ 专业工作台）

## 2026-06-14（Phase II/III：专业与信任期 + 机构执行链路）

依据 `user_spectrum_requirements.md` Phase II/III 整合合规预检、工业归因与机构级执行。

| 维度 | 交付物 | 文件 |
|------|--------|------|
| **交易流水线** | `TradeExecutionPipelineService`：Compliance → PreTrade → Impact(大单) → Audit | `trade_execution_pipeline_service.py` |
| **Fast Path 扩展** | 新增 `compliance_guardrail_check`、`trade_pipeline_execute`；Copy-Trade 走完整流水线 | `wiring_optimization.py`, `retail_tier_service.py` |
| **Phase II 投资** | Black-Litterman 组合优化 API | `investment_tier_service.py`, `routes_v1_user_tiers.py` |
| **Phase II 基金** | `POST /fund/trade/pipeline`、`GET /fund/audit/<order_id>`；主从账户经流水线镜像 | `fund_tier_service.py`, `routes_v1_user_tiers.py` |
| **预检增强** | `PreTradePreflightService` 集成 `ComplianceGuardrailService` | `pre_trade_preflight_service.py` |
| **服务工厂** | 注册 `trade_execution_pipeline_service`、`compliance_guardrail_service`、`audit_trail_service` 等 | `wiring_optimization.py` |

- **新增 API**：`POST /investment/optimize/black-litterman`；`POST /fund/trade/pipeline`；`POST /optimization/trade/pipeline`

## 2026-06-14（可行性审核 + 全用户频谱重构：合规隔离 / 双路径 / 复杂度治理）

依据 `docs/feasibility_audit_and_roadmap.md` 与 `docs/user_spectrum_requirements.md` 实施四维度优化（优先级：合规 > 性能 > 稳定性 > 演化）及 Phase I 用户频谱能力整合。

| 维度 | 交付物 | 文件 |
|------|--------|------|
| **合规隔离** | Alpha Marketplace 去金融化：`purchase` → `contribute()`，声誉积分替代 Wallet 货币；分级披露 API；Wallet 端点映射为声誉 | `alpha_marketplace_service.py`, `routes_v1_alpha_marketplace.py`, `marketplace.html` |
| **双路径分离** | Bootstrap 注册 Fast Path（`pre_trade_validate`, `copy_trade_execute`）与 Slow Path（`ai_mentor`, `prompt_evolution`, `memory_fabric_index`） | `wiring_optimization.py`, `services.py`, `retail_tier_service.py` |
| **复杂度治理** | 注册 `compliance_service` / `complexity_budget_service` / `anti_decay_evolution_service` 工厂；启动时 wiring 校验 | `wiring_optimization.py`, `wiring_system.py`, `service_wiring.py` |
| **Alpha 抗衰减** | 上架时计算 `diversity_bonus`；贡献时额外奖励低相关性因子 | `alpha_marketplace_service.py` + `AntiDecayEvolutionService` |
| **Phase I 散户** | NL→Strategy 自动附加向量化回测预览 | `routes_v1_user_tiers.py` |
| **Phase I 镜像交易** | Copy-Trading 信号经 DualPathRouter Fast Path 分发 | `retail_tier_service.py` |

- **新增 API**：`POST /alpha/marketplace/contribute`；`GET /alpha/reputation/balance`；`GET /alpha/reputation/leaderboard`；`GET /alpha/marketplace/disclosure/<token_id>`
- **兼容**：`POST /alpha/marketplace/buy`、`GET /alpha/wallet/*` 保留为声誉体系别名

## 2026-06-08（Phase 4 Sprint 0：去中心化启动 + DecisionFeedback + SSE 推理流）

- **Registry**：`topological_service_order()`；`wire_to` 按依赖拓扑注入；`ContextModule.initialize` 字段。
- **`initialize_all_modules`**：传入 `session_factory`；优先调用模块 `initialize()`。
- **Collaboration**：`wire_module` 自主装配；`services.py` 不再单独 wire collaboration。
- **主动智能**：`health_aware.py` Jarvis 降级提示；`DecisionFeedback` 实体 + `POST /api/v1/decision/feedback`。
- **SSE**：`AiAnalysisService.analyze_stream()` + `GET /api/v1/ai/analyze/stream`。
- **文档**：`docs/phase4-refactor.md`；**测试**：`tests/application/test_phase4_decision_feedback.py`。

## 2026-06-08（Phase 2 Sprint 12：register_factory 复杂服务 + infra 重绑 + legacy modules 下线）

- **`register_factory`**：`gpcw_service`、`industry_chain_service`、`data_infrastructure_service`（含 SocketIO 分支）、`tdx_base_read_service`。
- **`rewire_infra_dependent_services()`**：`bind_application_infrastructure` 后清空并重绑 gpcw/memory/task_pipeline/rdagent。
- **删除 wire**：`wire_gpcw_service`、`wire_industry_chain_service`、`wire_tdx_base_read_service`；`data_infrastructure` 内联块移除。
- **`core/modules.py`**：瘦身为 `module_manifest()` → `context_module_manifest()` 兼容 shim；静态 4 模块注册删除。
- **`GET /api/v1/system/microkernel`**：仅返回 v2 `modules`（registry 发现），移除 `legacy_modules`。
- **测试**：扩展 `test_service_loader`；新增 `tests/core/test_modules_shim.py`。

## 2026-06-08（Phase 2 Sprint 11：Registry name 收尾 + EvidenceGraph + ContextModule manifest）

- **`evidence_graph_service` / `user_access_policy_service` / `user_decision_context_service`**：修正 `name=`；删除 `wire_optional` 内联 wire；factor 服务改由 registry 注入。
- **`Services.evidence_graph_service`**：bootstrap 属性 + `configure_evidence_graph_service()` 统一 event handler 与路由 getter。
- **`context_module_manifest()`**（`app/core/registry.py`）：`GET /api/v1/system/microkernel` 返回 `context_modules`（v2）+ `legacy_modules`（v1 静态，deprecated）。
- **`core/modules.py`**：`module_manifest()` 标注 deprecated。
- **测试**：`tests/core/test_context_module_manifest.py`、`tests/application/test_evidence_graph_service.py`；扩展 `test_service_loader`。

## 2026-06-08（Phase 2 Sprint 10：_uid 全量迁移 + rdagent Registry + TDX 熔断）

- **`rdagent_run_service`**：修正 `name="rdagent_run_service"`；删除 `wire_rdagent_run_service`（改由 registry `wire_to` 注入）。
- **`legacy_tdx_adapter.py`**：`tdx_legacy` 熔断；OPEN 时 `execute` 返回 `None` 并 `mark_system_degraded`；`print` 改 `logger`。
- **路由 `_uid()` 迁移（剩余 12 文件）**：`legacy_routes`、`simulation`、`swarm_topology`、`ui`、`watchlist_agent`、`daily_workbench`、`watchlist_experience`、`reviews`、`decision_replay`、`strategy_snapshots`、`investment_managers`、`user_system`。
- **测试**：`tests/infrastructure/test_legacy_tdx_adapter.py`；扩展 `test_service_loader` 覆盖 rdagent。

## 2026-06-08（Phase 2 Sprint 9：Registry 服务 preload + Tencent 熔断 + _uid 路由迁移）

- **`app/bootstrap_components/service_loader.py`**：`preload_service_modules()` 在 `configure_service_registry` 前 import 全部 `@register_service` 模块。
- **`memory_optimization_service` / `task_pipeline_service`**：修正 `name=`；删除 `wire_task_pipeline_service`、`wire_memory_optimization_service`、`wire_investment_committee_service`（改由 registry `wire_to` 注入）。
- **`tencent_quote_gateway.py`**：`tencent_quotes` 熔断；OPEN 时返回空并 `mark_system_degraded`。
- **路由 `_uid()` 迁移**（Top 5 + trade_plan）：`signal_observations`、`smart_briefing`、`jarvis`、`strategy_shadow`、`quant_ai`、`trade_plan` 改用 `require_authenticated_user_id()`。
- **测试**：`tests/bootstrap/test_service_loader.py`、`tests/infrastructure/test_tencent_quote_gateway.py`。

## 2026-06-08（Phase 2 Sprint 8：CCXT 熔断 + 行情降级标记 + 路由 Registry 收尾）

- **`ccxt_adapter.py`**：`get_ohlcv` / `create_order` / `get_order` 经 `CircuitBreakerRegistry`（`ccxt_{exchange_id}`）；OPEN 时 OHLCV 返回空并 `mark_system_degraded`。
- **`market_data.py`**：Tencent/yfinance/L2 降级路径调用 `_mark_market_data_degraded(reason)`，触发 `X-System-Degraded` 响应头。
- **路由装饰器补全**：`quant_ai`、`tdx_base`、`ten_kings`、`portfolio_user`、`task_pipeline`、`recommendation`；修正 `sentiment` / `nl` / `challenge` 签名 `(blueprint, ctx=None)`。
- **`routes.py`**：`_register_legacy_routes` 精简为空壳；`admin_stock_cache` 仍在 `create_api_blueprint` 特殊处理。
- **文档**：`docs/phase2-refactor.md` Phase 2 总结。

## 2026-06-08（Phase 2 Sprint 0–1：Registry 启动链 + Collaboration ContextModule 试点）

- **`app/presentation/api/route_loader.py`**：新增 `preload_route_modules()`，在 `discover_routes()` 前 pkgutil 扫描 `routes_v1_*`，使 `@register_routes` 装饰器先于 auto-discovery 生效。
- **`app/presentation/api/routes.py`**：注册流程改为 preload → discover → legacy fallback。
- **`app/bootstrap_components/service_wiring.py`**：新增 `configure_service_registry(config)`；`wire_collaboration_module` 合并协作 wire 链。
- **`app/bootstrap_components/services.py`** / **`app/bootstrap.py`**：`registry_config` 传入 `create_services`；`service_registry` 写入 `app.extensions`。
- **`app/core/module_scanner.py`**：改为基于 `registry.discover_routes` + `route_loader`。
- **`app/core/modules.py`**：标注 deprecated（manifest 兼容保留）。
- **`app/modules/collaboration/`**：首个物理 ContextModule；`CollaborationContextModule` + `ENABLE_COLLABORATION`。
- **`context_modules.py`**：`collaboration` 从 `UserContextModule` 拆出；`routes_v1_collaboration` 改 `context="collaboration"`；新增 `CollaborationCtx`。
- **测试**：`tests/presentation/test_route_loader.py`。

## 2026-06-08（Phase 2 Sprint 2–3：AI DecisionContext + OpenBB 熔断）

- **`AiAnalysisService.analyze()`**：返回 dict 新增 `decision_id` / `decision`（`DecisionContextDTO`）；保留原有 `symbol`/`ai`/`context` 等字段向后兼容。
- **`openbb_adapter.py`**：`get_realtime_quotes` / `get_stock_history` / `get_stock_profile` 对外部 OpenBB 调用加 `@circuit_breaker`；OPEN 时降级为空结果并记录 warning。
- **测试**：`tests/test_pool_and_ai_services.py` 断言 decision 字段。

## 2026-06-08（Phase 2 Sprint 4：模块驱动 wire + DecisionTrace + ContextVar）

- **`app/bootstrap_components/module_wiring.py`**：`wire_context_modules()` 按 `discover_modules(config)` 调用各模块 `wire()`。
- **`ContextModule.wire`**：`register_module` 自动采集类上的 `wire` 静态方法。
- **`DecisionTraceService`**：进程内按 `decision_id` 记录/查询；`AiAnalysisService` 分析后自动 `record`。
- **API**：`GET /api/v1/decision/trace/<decision_id>`。
- **`request_context` 中间件**：Flask `before_request` 注入 `request_id` / `user_id` ContextVar；响应头回写 `X-Request-ID`。
- **测试**：`tests/application/test_decision_trace_and_module_wiring.py`。

## 2026-06-08（Phase 2 Sprint 5：Risk 收敛 + Redis Trace + ContextVar 路由迁移）

- **`TradingRiskFacade`**：`risk_service` 统一实现 `check_order` / batch / Kelly / vol-target；`watchlist_risk_service` 独立承载 `RiskAlertService`。
- **`DecisionTraceService`**：可选 Redis 持久化（`TASK_MESSAGE_REDIS_URL`），键前缀 `quant:decision:trace:`，TTL 7 天；不可用时回退内存。
- **`routes_v1_collaboration`**：用户 ID 改经 `require_authenticated_user_id()` / `_uid()`。
- **`app/modules/portfolio_risk/`**：第二个物理 ContextModule（portfolio + risk wire）。
- **测试**：`tests/application/test_trading_risk_and_trace.py`。

## 2026-06-08（Phase 2 Sprint 6：portfolio_risk 拆分 + Ollama 熔断 + 投委会 DecisionContext）

- **`PortfolioContextModule`**：仅保留 watchlist/signal_flag；portfolio/risk/trade_plan 路由改 `context="portfolio_risk"`。
- **`OllamaPromptAdapter`**：`@circuit_breaker("ollama_generate")`；OPEN 时 `degraded: true`；记录 `prompt_version`。
- **`AICommitteeSelectionService.run_selection()`**：返回 `decision_id` / `decision` 并写入 DecisionTrace。
- **`routes_v1_portfolio_users`** / **`routes_v1_ai_committee_selection`**：用户 ID 改经 `_uid()`。
- **测试**：`tests/application/test_sprint6_ai_and_context.py`。

## 2026-06-08（Phase 2 Sprint 7：Degraded 响应头 + Wiring 去重 + FinGPT 熔断）

- **`degraded_context.py`**：`mark_system_degraded()` ContextVar；`X-System-Degraded` / `X-System-Degraded-Reason` 由 request 中间件注入。
- **Ollama / OpenBB / FinGPT**：熔断或降级时标记 degraded；`AiAnalysisService` 传播 Ollama degraded 标记。
- **Bootstrap wiring**：`wire_context_modules` 提前至 `wire_legacy` 之前；移除 legacy 中重复的 `wire_risk_alert_service` 与 presentation 层 `wire_portfolio_service`。
- **测试**：`tests/core/test_degraded_context.py`。

## 2026-06-06（V9 Cross-Node EventBus 统一门面）

- **`ClusterEventBusFacade`**（`app/core/cluster_event_bus.py`）：`ensure_cluster` / `manifest` / `publish_remote`；`EVENT_BUS_CLUSTER_MODE=auto|cluster|local`。
- **`bootstrap.py`**：Mesh 启动改经 `get_cluster_event_bus().ensure_cluster`；`app.config["CLUSTER_EVENT_BUS"]` 缓存 manifest。
- **API**：`GET /api/v1/system/event-bus/cluster`。
- **文档**：`docs/redis.md` 补充 Mesh/执行 Redis 与 `.env` 示例。
- **测试**：`tests/unit/test_cluster_event_bus.py`。

## 2026-06-06（V7 React Flow + Narrative 2.0）

- **`swarm_designer_flow.html`**：React Flow 可视化编辑研究图谱；`PUT /api/v1/swarm/topology/research-graph` 保存至 `instance/research_topology/` 覆盖层。
- **`TopologyLoader.save_override`**：优先加载 instance 覆盖，再回退 bundled JSON。
- **`NarrativeSynthesisService.synthesize_causal_report`**：全量 SequenceChain 步骤 → 长篇 Markdown 因果研报；`GET /briefing/causal-report`；`narrative_level=full` 时附带到日报。
- **测试**：`test_topology_save`、`test_causal_report_template_from_sequence_chain`。

## 2026-06-06（V9 Agent 发现协议 + V7 拓扑 API + 完成度文档）

- **`AgentDiscoveryProtocol`**：从 `research_graph_topology.json` 广播本节点 Agent 能力；`GET /api/v1/mesh/agents/discover`。
- **`MeshNodeRegistry`**：本地节点 `capabilities` 合并研究图谱角色；`agent_topology_id=research_default`。
- **Swarm**：`GET /swarm/topology/research-graph`；预设 `research_default`；Designer 下拉可加载运行时拓扑。
- **`docs/option_1_9.md`**：§1.1 实测完成度快照（V7 后端 ~90%、V9 分布式 ~80%）。

## 2026-06-06（7.0 拓扑数据化 + 6.0 协作推送 + 8.0 执行驱动抽象）

- **`research_graph_topology.json` + `TopologyLoader`**：`graph.py` 边/条件路由改由 JSON 驱动；`RESEARCH_GRAPH_NODES` 与拓扑同步。
- **`TeamBlackboardService`**：提交/共识经 `RealtimeGatewayService` Socket.IO 推送至 `team_blackboard:{team_id}`。
- **`TradingBotService` / `BotEngine`**：移除 `ExchangePort` 依赖，统一 `ExecutionGateway`；`resolve_bot_execution_gateway` 按市场选驱动。

## 2026-06-06（V9 真值守卫增强 + Mesh 多节点验收）

- **`byzantine_consensus.py`**：中位数法定多数 + 离群源标注（拜占庭式多源共识）。
- **`UnifiedDataTruth.quorum_consensus`**：聚合 TDX / Qlib / AkShare 收盘价；`latest_akshare_bar` 读取器。
- **`DataTruthGuardianService.quorum_scan`**：批量拜占庭扫描；异常时 Mesh fan-out `TruthDeviationEvent`。
- **API**：`POST /data-truth/quorum`；`GuardianManifest.quorum_enabled`（`DATA_TRUTH_QUORUM_ENABLED`）。
- **测试**：`test_byzantine_consensus`、`test_mesh_multi_node`（CN→US 跨区 fan-out + peer 注册表）。

## 2026-06-06（8.0 无界执行：多市场 Redis 驱动插件）

- **`RedisMarketExecutionDriver`**：按市场分队列的 Redis Stream 驱动，Redis/worker 不可用时回退 `PaperExecutionDriver`。
- **`driver_registry.build_borderless_router`**：统一注册 `paper_*` + `redis_*`（CN/US/HK/CRYPTO）；交易所标签 `alpaca_sim` / `futu_sim` / `binance`。
- **`BorderlessExecutionRouter`**：`redis_*` 缺失时回退 `paper_*`；`list_drivers` 输出 `describe()` 元数据。
- **修复**：`market_router` 对 CRYPTO 固定走 `redis_crypto`，此前未注册导致下单失败。
- **环境变量**：`EXECUTION_REDIS_URL`、`EXECUTION_REDIS_FALLBACK_PAPER`、`EXECUTION_REGISTER_REDIS_DRIVERS`、`EXECUTION_REDIS_TIMEOUT`。
- **测试**：`test_borderless_execution_service` 增补 US/Crypto 路径；修复 `redis_executor` 缺 `OrderType` 导入。

## 2026-06-06（7.0→8.0 重心：叙事证据链 + Swarm 拖拽 + NATS Mesh）

- **`NarrativeSynthesisService`**：注入 `sequence_chain_service`；`synthesize_daily_briefing` 从 `SequenceChain` 拉取辩论/仲裁证据节点写入 LLM prompt 与模板叙事；响应新增 `evidence_nodes`。
- **`wire_smart_daily_briefing_service`**：向叙事层传递 `sequence_chain_service`（在 `wire_swarm_arbiter` 之后已可用）。
- **`swarm_designer.html`**：HTML5 拖拽重排节点；侧栏展示 `GET /system/agent-topology` 动态权重并在积木块上显示 `×weight`。
- **`NATSMeshTransport`**：`app/core/mesh/transport.py` 新增 NATS 传输；`create_mesh_transport` 支持 `MESH_TRANSPORT=redis|nats|memory`；`bridge.py` 读取 `MESH_NATS_URL`。
- **测试**：`test_narrative_synthesis_service` 增补 SequenceChain 证据叙事用例；`test_mesh_transport_nats_fallback`。
- **文档**：`docs/option_1_9.md` §3 环境变量与 §4 缺口表更新。

## 2026-06-06（option_1_9.md 重构：集成验收与文档收口）

- **`docs/option_1_9.md`**：重写为唯一收口文档——Option 规划 ↔ 产品 V1–V9 对照表（纠正原稿「Option 8.0 分布式」= 产品 **V9**、「7.0 仅设计」过时表述）、§2 分阶段验收矩阵、§3 自动化/人工清单、附录 API 速查。
- **`docs/QUANT_ATLAS_V1_V9_集成验收.md`**：瘦身为跳转页，指向 `option_1_9.md`。
- **`tests/integration/test_v1_v9_acceptance_smoke.py`**：增补 Foundation 冒烟（`WorkflowService`、`CapabilityRegistry`、`SystemPulseService`）。
- **`docs/QUANT_ATLAS_平台手册.md`**：§12 主索引改为 `option_1_9.md`。

## 2026-06-06（V1–V9 集成验收与文档收口）

- **`docs/QUANT_ATLAS_V1_V9_集成验收.md`**：版本谱系 V1–V9、集成架构图、API 总览、环境变量、自动化 pytest 命令、人工验收清单、已知缺口。
- **`tests/integration/test_v1_v9_acceptance_smoke.py`**：V4 EventBus、V6–V9 服务 manifest/场景 冒烟（无 Redis/无 DB 依赖）。
- **`docs/QUANT_ATLAS_平台手册.md`**：§12 索引新增验收文档；§12.1 版本演进速查表。

## 2026-06-06（Quant Atlas 9.0 Step Four：数据真值守卫 / Data Truth Guardian）

- **`guardian_schema.py`**：`GuardianScanRequest`、`DataHealAction`、`GuardianManifest`。
- **`DataTruthGuardianService`**：批量 `TruthSentry` 扫描、待核验列表（`domain.verification`）、自愈动作（`resync_qlib` / `clear_pending`）、`instance/data_truth/heal_log.jsonl`；可选 Celery 派发 Qlib 增量同步。
- **Mesh**：`TruthDeviationEvent` / `AnalysisStaleEvent` 加入默认 fan-out。
- **API**：`GET /data-truth/manifest`、`GET /data-truth/pending`、`POST /data-truth/scan`、`POST /data-truth/heal`、`GET /data-truth/heal-log`。
- **接线**：`wire_data_truth_guardian_service()`。

## 2026-06-06（Quant Atlas 9.0 Step Five：决策剧场 / Decision Theater）

- **`DecisionTheaterService`**：融合 `build_research_pipeline_snapshot`、EventBus 近期事件、`list_pending` 真值告警，编译 `DecisionReplayScene` v2 剧场图。
- **API**：`GET /decision-theater/space`。
- **UI**：`research_pipeline.html` 嵌入 Three.js Decision Theater 画布。
- **接线**：`wire_decision_theater_service()`。

## 2026-06-06（Quant Atlas 9.0 Step Three：超维模拟器 / Hyper-Simulator）

- **`hyper_sim_schema.py`**：`HyperSimRunRequest`（`backtest_mc` / `price_path` / `combined`）、`HyperSimEvidence`。
- **`monte_carlo_engine.py`**：交易序置换检验（`monte_carlo_permutation`）、GBM 路径模拟（`simulate_gbm_paths`、VaR/CVaR）、`estimate_drift_vol`。
- **`HyperSimulatorService`**：融合 `ToolFacadeService.run_backtest` / `StrategyApplicationService`、可选 War Room 情景叠加（`SimulationScenario.from_preset`）；运行记录 `instance/hyper_sim/runs.jsonl`；输出含 `evidence` + `confidence`。
- **API**：`GET /simulation/hyper/manifest`、`GET /simulation/hyper/recent`、`POST /simulation/hyper/run`。
- **接线**：`wire_hyper_simulator_service()`（依赖 simulation_gateway + strategy/tool_facade）。

## 2026-06-06（Quant Atlas 9.0 Step Two：无界执行 / Borderless Execution）

- **`execution_schema.py`**：`ExecutionRouteDescriptor`、`BorderlessOrderRequest`、`ExecutionManifest`。
- **`market_router.py`**：标的 → `MarketCode` 推断（CN/US/HK/CRYPTO）与 driver 选择（paper / redis / qmt）。
- **`PaperExecutionDriver`** + **`BorderlessExecutionRouter`**：多市场网关注册与统一 `ExecutionGateway` 路由。
- **`BorderlessExecutionService`**：下单编排、`OrderManager` 记录、`emit_trade_executed` 审计 lineage；成交可选 mesh fan-out（`TradeExecutedEvent` 加入默认 fan-out）。
- **API**：`GET /execution/manifest`、`GET /execution/route`、`POST /execution/orders`、`GET /execution/orders`、`GET /execution/orders/<id>`。
- **环境变量**：`BORDERLESS_EXECUTION_ENABLED`（默认 true）、`EXECUTION_DEFAULT_MODE=paper|redis|qmt`。
- **接线**：`wire_borderless_execution_service()`。

## 2026-06-06（Quant Atlas 9.0 Step One：分布式智能集群 / Federated Agent Mesh）

- **`mesh_schema.py`**：`MeshNodeDescriptor`、`MeshEventEnvelope`、`MeshPublishRequest`；区域 `CN/US/HK/EU` 与联邦 Agent 角色枚举。
- **`app/core/mesh/`**：`protocol`（topic 命名）、`transport`（Redis Pub/Sub + `MemoryMeshTransport` 测试后端）、`node_registry`（本地 + 可选 Redis 节点表）、`DistributedEventBus`（环回防护 `origin_node_id`、区域过滤）、`bridge`（本地 `EventBus` ↔ 远端 fan-out）。
- **`MeshForwardedEvent`**：远端信封再注入本地 EventBus，供订阅方按 `original_event` 过滤。
- **默认 fan-out**：`DebateRoundEvent`、`MetaArbiterActivatedEvent`、`CrossTeamSiteAlertEvent`、`WorkflowCompletedEvent` 等。
- **`MeshGatewayService`** + **API**：`GET /mesh/manifest`、`GET /mesh/nodes`、`GET /mesh/events/recent`、`POST /mesh/publish`。
- **环境变量**：`MESH_ENABLED`、`MESH_NODE_ID`、`MESH_REGION`、`MESH_REDIS_URL`（默认可复用 `TASK_MESSAGE_REDIS_URL`）。
- **启动**：`bootstrap.py` 在 `MESH_ENABLED=true` 时调用 `start_mesh_bridge()`；`wire_mesh_gateway_service()`。

## 2026-06-06（Quant Atlas 8.0 P2：决策回溯空间 / Decision Replay Space）

- **`decision_replay_scene.py`**：`SceneNode` / `SceneEdge` / `DecisionReplayScene` 3D 场景描述符（位置、颜色、边界）。
- **`DecisionReplaySpaceService`**：融合 `UserKnowledge` 行为拓扑、决策模式、认知偏见与可选 `EvidenceReplay` 时间轴，编译沉浸式场景图。
- **API**：`GET /decision-replay/space?symbol=&market=CN&minutes_back=120`。
- **UI**：`/decision-replay` Three.js（jsDelivr ES module）轨道控制 2.5D 漫步；导航 AI 投研 → 决策回溯空间。
- **接线**：`wire_decision_replay_space_service()`。

## 2026-06-06（Quant Atlas 8.0 P1：投研流水线 2.0 / Team Workflow）

- **`team_workflow_schema.py`**：`TeamWorkflowDescriptor` 人机混合节点（`human_task`、`approval_gate`、`blackboard_post`、`research_publish`、`agent_swarm`、`arbiter`）。
- **`team_workflow_presets.py`**：内置 `lead_review_pipeline`、`fast_agent_loop` 两套预设。
- **`TeamWorkflowService`**：Lead 保存流水线、启动运行、人工/审批 `advance`、自动执行 Agent/黑板/投研流节点；运行记录 `instance/team_workflows/`。
- **API**：`GET/POST /teams/{id}/workflows`、`POST .../workflows/{id}/run`、`POST .../workflow-runs/{id}/advance`、`GET .../workflow-runs`。
- **UI**：`team_workflow_panel.html` 接入 `/collaboration`；`team_context_bar` 派发 `team-context-changed`。
- **接线**：`wire_team_workflow_service()`（依赖 collaboration + blackboard + research + swarm）。

## 2026-06-06（Quant Atlas 8.0 P0：跨团队元仲裁 / MetaArbiter）

- **`MetaArbiterService`**：当 ≥3 独立团队对同一标的形成高置信共识时，激活站点级 `meta_verdict`（跨团队加权 + 可选本地 Debate Arbiter 融合）；记录 `instance/cross_team/meta_verdicts.jsonl`。
- **`MetaArbiterActivatedEvent`**：元仲裁激活经 EventBus 发布；`alerts` WebSocket 通道扩展。
- **`CrossTeamMetaLearningService`**：全站告警创建时自动调用元仲裁，告警附带 `meta_verdict` / `meta_confidence` / `meta_rationale`。
- **API**：`POST /system/meta-arbiter/synthesize`、`GET /system/meta-arbiter/recent`、`GET /system/meta-arbiter/symbol/<symbol>`。
- **UI**：`cross_team_pulse.html` 展示元仲裁裁决与 rationale。
- **接线**：`wire_meta_arbiter_service()` + `attach_meta_arbiter()` 延迟绑定。

## 2026-06-06（Quant Atlas 7.0 Step Four：多模态感知 / 语音简报 + Jarvis 语义穿透）

- **`VoiceBriefingService`**：基于 `SmartDailyBriefingService` 叙事层生成播报文稿；优先 OpenAI TTS（`OPENAI_API_KEY` / `TTS_VOICE`），失败或未配置时回退浏览器 `speechSynthesis`；音频缓存 `instance/voice_briefings/`。
- **API**：`GET /briefing/voice-daily`、`GET /briefing/voice-daily/audio/<file_id>`。
- **`JarvisSemanticRouterService`**：模糊意图路由（语音简报、War Room、赚钱风格选股）；`UserKnowledge` 跨年度成功模式匹配 + `StrategyApplicationService` 候选打分。
- **`CommandPlanService.build_semantic_plan()`**：复合指令语义层扩展；`POST /command/plan` 默认启用 semantic。
- **API**：补全 `GET /system/ask`（Command Orb）；`POST /jarvis/semantic-route`；`GET /jarvis/winning-patterns`。
- **UI**：`/voice-briefing` 晨间播客页；`base.html` Jarvis 面板展示模式匹配候选。
- **接线**：`wire_voice_briefing_service()`、`wire_jarvis_semantic_router_service()`。

## 2026-06-06（Quant Atlas 7.0 Step Three：反事实模拟战 / SimulationGateway War Room）

- **`simulation_scenario.py`**：`SimulationScenario` / `WarRoomPosition` / `WarRoomRunRequest`；情景类型含加息、全市场冲击、板块黑天鹅、波动率飙升、自定义假设。
- **`SimulationGatewayService`**：持仓压力重估（beta/板块敏感度）、`debate_bus.publish_debate_round` 虚拟事件注入、可选 `SwarmArbiterService.consensus_only` 重估；运行记录 `instance/war_room/runs.jsonl`。
- **API**：`GET /simulation/war-room/scenarios`、`GET /simulation/war-room/recent`、`POST /simulation/war-room/run`。
- **UI**：`/war-room` Alpine 压力测试面板（导航 AI 投研 → War Room）。
- **接线**：`wire_simulation_gateway_service()`（依赖 portfolio + watchlist + swarm_arbiter）。

## 2026-06-06（Quant Atlas 7.0 Step Two：生成式叙事智能 / Narrative Synthesis）

- **`NarrativeSynthesisService`**：结合 `UserKnowledgeService`（关注标的、成功模式、行为拓扑）与 `UserDecisionContextService`（叙事密度/角色）生成因果叙事；LLM 优先、模板回退。
- **`SmartDailyBriefingService`**：新增 `user_id`/`role`/`use_narrative`；输出 `narrative` 块与 per-stock `narrative` 字段。
- **API**：`GET /api/v1/briefing/smart-daily?top_n=3&narrative=1&role=trader`。
- **接线**：`wire_smart_daily_briefing_service()`（依赖 strategy + user knowledge + decision context）。

## 2026-06-06（Quant Atlas 7.0 Step One：图驱动 Swarm 编排 / Swarm Designer）

- **`topology_schema.py`**：`SwarmTopologyDescriptor` JSON 图描述符（节点 kind/agent_role、边、entry/exit）。
- **`swarm_topology_presets.py`**：内置 `integrated_parallel`、`debate_pipeline` 两套预设。
- **`topology_compiler.py`**：`TopologyCompiler` 将 JSON 拓扑编译为 LangGraph `StateGraph`。
- **`integrated_graph.py`**：支持 `topology=` 动态配置；新增单分析师/辩论/仲裁节点执行器。
- **`SwarmTopologyService` + API**：`GET/POST /swarm/topology/*`（预设、积木块、校验、用户保存）。
- **UI**：`/swarm-designer` Alpine.js 拖拽画布 + JSON 预览（导航 AI 投研 → Swarm Designer）。

## 2026-06-06（Quant Atlas 6.0 Step Five：预警中心集成 + Realtime 推送）

- **`AlertCenterService`**：合并 `cross_team_meta_learning` 全站共识告警；新增分类 `consensus`。
- **`CrossTeamSiteAlertEvent`**：多团队一致共识时经 EventBus 发布；WebSocket `alerts` 房间广播。
- **`RealtimeGatewayService`**：manifest 增加 `alerts` 通道（`CrossTeamSiteAlertEvent`）。
- **前端**：`base.html` 订阅 `alerts` 房间；`alert_center.html` 支持群体共识筛选与实时插入动画。
- **API**：`GET /system/alerts?category=consensus` 与 cross-team 告警统一展示。

## 2026-06-06（Quant Atlas 6.0 Step Four：跨团队元学习 / 群体智能仲裁）

- **`CrossTeamMetaLearningService`**：团队共识注册（HMAC 匿名 `team_fp`）；≥3 团队 48h 内同标的同 verdict → 全站异动提醒（`instance/cross_team/site_alerts.jsonl`）。
- **匿名模式池**：`ArbiterReviewLearningService.record_review` 汇入成败模式（无 symbol/tenant/user）；`anonymous_patterns.json` 聚合 `predicted→actual`。
- **挂钩**：`TeamBlackboardService.synthesize_consensus` 自动注册跨团队信号；`wire_cross_team_meta_learning_service()`。
- **API**：`GET /system/cross-team/alerts`、`/patterns`；`POST /system/cross-team/scan`。
- **UI**：`cross_team_pulse.html` 接入 `/collaboration` 工作区。

## 2026-06-06（Quant Atlas 6.0 Step Three：Headless 外壳 / 协作 UI 组件化）

- **`page_shell.py`**：`render_page_shell()` + `ux_env_hints()`；`pages.py` 业务逻辑外移，`stock_detail` / `collaboration` 路由精简为 HTML 外壳。
- **Headless Bootstrap API**：`GET /ui/stock-detail-context`、`/ui/collaboration-workspace-context`、`/ui/capabilities`（`routes_v1_ui.py`）。
- **协作 Capability 组件**（Alpine.js + API v1）：`team_context_bar`、`team_blackboard`、`team_research_feed`；共享 `static/js/collaboration/team_context_store.js`。
- **`collaboration_workspace.html`**：独立协作工作区页面 `/collaboration`；导航「系统 → 协作投研工作区」。
- **`stock_detail.html`**：工作区默认布局扩展 3 个团队组件；`PagePreferenceService` / `workspace_shell` 同步更新。

## 2026-06-06（Quant Atlas 6.0 Step Two：团队黑板 / 投研流 / 证据链共享）

- **ORM**：`team_blackboard_entries`（`TeamBlackboardEntry`）。
- **`TeamBlackboardService`**：成员/Agent 证据提交、列表、加权共识合成（可选接入 `DebateArbiterService`）。
- **`TeamResearchChannelService`**：基于 Moments 的团队投研流；证据链发布与逻辑挑战评论。
- **`SequenceChain`**：新增 `visibility`（private/team/public）、`team_id`、`owner_user_id`；`SequenceChainService.set_scope()` + 列表按 `team_id`/`visibility` 过滤。
- **`secure_share_token`**：HMAC 签名 + 过期校验；`DecisionSnapshotService` 创建快照时生成 `share_expires_at`。
- **API**：`GET/POST /teams/{id}/blackboard`、`POST .../blackboard/consensus`；`GET/POST /teams/{id}/research-feed`（含 publish/challenge）；`POST /teams/{id}/sequence-scope`；`GET /system/sequence-chain?team_id=`。
- **接线**：`wire_team_collaboration_services()`（依赖 `collaboration_repository` + `moments_service`）。

## 2026-06-06（Quant Atlas 6.0 Step One：多租户核心 / SQL 持久化）

- **领域实体**：`Tenant`、`Team`、`TeamMembership`（`app/domain/entities.py`）。
- **ORM**：`tenants`、`teams`、`team_memberships`、`user_lifecycle_settings`、`user_knowledge_profiles`（`models/collaboration.py`）。
- **`MySQLCollaborationRepository`**：个人租户自动创建；lifecycle/knowledge 行级 `tenant_id` 隔离。
- **`UserLifecycleService` / `UserKnowledgeService`**：MySQL 可用时双写 SQL + JSON 回退；`sync_status.mode=sql_tenant`。
- **API**：`GET /user/tenant-context`、`POST /teams`、`POST /teams/{id}/members`。

## 2026-06-06（Quant Atlas 5.0 Phase Three：Live-Document / Jarvis 5.0 主动预测）

- **`LiveResearchDocumentService` + `live_research_lab.html`**：12s 轮询统一研报；三色灯（数据真值/技术共振/Agent 辩论）自动刷新；`GET /stocks/{market}/{symbol}/live-document`。
- **`JarvisProactiveService`**：自选股 + `UserKnowledgeService` 高弹性偏好扫描；`GET /jarvis/proactive`；`base.html` 全局浮动主动信号面板。
- **工作区默认布局**：`live-research-lab` 置顶；`attribution-timeline` 订阅 `live-document-updated` 事件联动。

## 2026-06-06（Quant Atlas 5.0 Phase Two：仲裁复盘 / 影子接管 / 智能降级）

- **`ArbiterReviewLearningService`**：复盘错误 verdict 动态调整 `_STANCE_WEIGHTS`；`POST /system/arbiter/review`、`GET /system/arbiter/learning`。
- **`StrategyCoPilotService`**：48h 影子策略对比 + 仲裁置信度 ≥0.8 时生成 handover 建议；`POST /strategy/copilot/handover`；`/strategy/copilot` 响应增加 `shadow_strategies` / `handover`。
- **`SmartDegradeGateway`**：基于 Redis 延迟与 SystemPulse 切换 stream/batch/degraded；`realtime.py` 行情广播接入；`GET /system/stream-topology`。

## 2026-06-06（Quant Atlas 5.0 Phase One：SequenceChain 内核 + 反馈闭环仲裁）

- **`SequenceChain` / `SequenceChainService`**：EventBus 订阅辩论→共识→修正→成交，构建 `provenance_id` 因果链；持久化 `instance/sequence_chains/chains_index.jsonl`。
- **事件扩展**：`ArbiterConsensusEvent`、`CorrectionIntentEvent`；`TradeExecutedEvent` 强制 `provenance_id`；`emit_trade_executed()` 辅助函数。
- **`CorrectionIntentService`**：verdict 切换时向 `TradePlanService` 注入风险参数 patch（regime_shift / stance_flip）。
- **`DebateArbiterService._finalize_consensus`**：共识后发布事件并触发 CorrectionIntent。
- **API**：`GET /system/sequence-chain`、`GET /system/sequence-chain/{id}`、`GET /system/correction-intents`。

## 2026-06-06（诊股 / K 线 history API 503·400 修复）

- **`dto_validation.validate_request`**：查询参数 DTO 以 `req=` 关键字注入，避免与路径参数 `market`/`symbol` 位置冲突导致 503。
- **`wire_diagnosis_report_service`**：bootstrap 接线 `DiagnosisReportService`，修复 `/diagnosis/report` 400（service_unavailable）。
- **`DiagnosisReportService`**：标的规范化为 `sh/sz/bj` 小写 canonical（如 `sz000338`）。

## 2026-06-06（Quant Atlas 4.0 Phase Four：共振计 / 工作区 / LLM 仲裁 / 心理卫士联动）

- **`GET /stocks/{market}/{symbol}/resonance`**：`TechnicalResonanceMeter` 实时共振 API；`components/stock/resonance_meter.html`。
- **`workspace_shell.html` + `stock_detail_layout`**：`PagePreferenceService` 支持拖拽布局持久化。
- **`DebateArbiterService.synthesize_with_llm`**：`GET /system/arbiter/consensus?mode=llm`；失败回退启发式。
- **`behavior_topology_guardian`**：行为拓扑预警并入 `psychology-guardian` / `psychology-status`；Retail Hub 新增模块卡片。

## 2026-06-06（Quant Atlas 4.0 Phase Three：行为拓扑 / Agent 拓扑 / UI / Deep Replay）

- **`behavior_topology.py` + `UserKnowledgeService`**：`interaction_events` 采集；疲劳期/确认偏误/注意力收窄检测；`GET /user/knowledge/topology`。
- **`AgentTopologyService`**：30 日归因 + 市场 regime 动态调权；`GET /system/agent-topology`；MetaLearning 演化后持久化 `instance/agent_topology.json`。
- **`EvidenceReplayService` + `evidence_replay_store`**：时间轴回溯 + What-if；`GET /ai/evidence/replay`、`POST /ai/evidence/what-if`。
- **UI 组件**：`strategy_copilot.html`、`evidence_replay.html`（Alpine.js）。
- **Replay 快照**：`debate_bus` / `TruthSentry` 写入 jsonl 回放库。

## 2026-06-06（Quant Atlas 4.0 Phase Two：Arbiter Hybrid + 归因时间轴组件）

- **`app/agents/research/debate_bus.py`**：LangGraph 辩论轮次 publish `DebateRoundEvent` 并缓冲供仲裁。
- **`app/agents/research/graph.py`**：bull/bear/risky/safe 节点接入 `publish_debate_round`。
- **`DebateArbiterService` / `SwarmArbiterService`**：基于多轮辩论加权共识；bootstrap 注册 `swarm_arbiter_service`。
- **API**：`GET /api/v1/system/arbiter/consensus`、`POST /api/v1/system/arbiter/run`。
- **UI**：`components/stock/attribution_timeline.html`（Alpine + 辩论共识徽章）。

## 2026-06-06（Quant Atlas 4.0 Phase One：EventBus / UnifiedDataTruth / TruthSentry / UI 组件化）

- **`app/core/event_bus.py`**：`Event` 增加 `priority` / `ttl_seconds`；handler 按 priority 调度；过期事件丢弃。新增 `DebateRoundEvent`、`TruthDeviationEvent`、`AnalysisStaleEvent`。
- **`app/infrastructure/data_truth/`**：`UnifiedDataTruth` 实现 `DataQualityPort`，对比 TDX lday 与 qlib_bin 收盘价（默认阈值 0.5%）。
- **`app/infrastructure/realtime/truth_sentry.py`**：订阅 `MarketDataUpdatedEvent` 发布 truth/stale 事件；`app/domain/verification.py` 维护 `verification_status`。
- **`providers` / `realtime` bootstrap**：数据质量 monitor 切换 `UnifiedDataTruth`；启动 TruthSentry；行情广播同步 `MarketDataUpdatedEvent`。
- **`SystemPulseService` / `AiEvidenceService` / `RealtimeGatewayService`**：truth 通道与 `verification_status`。
- **`stock_detail.html`**：决策简报拆为 `components/stock/decision_brief_strip.html`（Alpine.js + 事件轮询）。

## 2026-06-07（TDX 检查点增量落盘）

- **`tdx_sync_checkpoint.flush_sync_checkpoint`** + **`TDX_SYNC_CHECKPOINT_FLUSH_EVERY`**（默认 10）：`_run_sync` 每 N 只成功即 `append_ok_codes`，进程中断不丢进度。

## 2026-06-07（Timescale 失败时优先 MySQL/CSV/qlib）

- **`run_full_data_consistency.py`**：`timescale_backfill_state.paused` 或 `FULL_BACKFILL_SKIP_TIMESCALE=1` 时自动 `--skip-ts`，串行 MySQL resume → qlib → verify。

## 2026-06-06（Timescale 分页 backfill 断点修复）

- **`tdx_dayk_sync_service.timescale_full_sync_from_tdx_dayk`**：分页（`limit`/`offset`）时在全市场列表上切片；不再先 `filter_codes_resume` 再 offset，避免 `next_offset=1400` 时 `codes_total=0` 误判完成。

## 2026-06-06（QuestDB 离线仍可 CH/Timescale/MySQL 补齐）

- **`preflight_timeseries_targets(require_questdb=False)`**：仅写 ClickHouse 时不再强依赖 QuestDB 连通。
- **`run_full_data_consistency.py`**：preflight 重试；QuestDB 不可达时仍从 TDX 跑 CH/Timescale/MySQL；日志写入容错。

## 2026-06-06（全链路一致性脚本 + MySQL 快检）

- **`scripts/run_full_data_consistency.py``**：串行 CH → Timescale → MySQL(失败重试+续跑) → qlib → verify，日志 ``instance/full_data_consistency.log``。
- **`mysql_qlib_sync_status`**：默认用检查点估算缺口，避免 MySQL 大表 COUNT 超时卡死 ``sync-all``。

## 2026-06-06（历史同步：脏日期过滤 + sync-all + 缺口检测）

- **`history_row_validator`**：跳过 TDX 非法日历日期（如 ``2041-90-51``），避免整股 MySQL 写入失败。
- **`timeseries_sync_status`**：不可达库单独标记；Timescale 结合 ``sample_sh600519`` 判断缺口。
- **`run_timeseries_sync_pipeline.py sync-all``**：串行 CH → Timescale → MySQL/CSV/qlib → verify。

## 2026-06-05（API 404：情绪日记 + AI Hedge Fund）

- **`routes.py`**：注册 ``register_sentiment_routes``、``register_ai_hedge_fund_routes``，修复 ``GET /api/v1/market/sentiment/diary`` 与 ``POST /api/v1/ai-hedge-fund/analyze`` 404。
- **`routes_v1_ai_hedge_fund.py``**：子蓝图前缀改为 ``/ai-hedge-fund``，挂到 ``api_v1`` 主蓝图下。

## 2026-06-05（MySQL / CSV / qlib 对齐管道）

- **`mysql_qlib_sync_status`**：MySQL 生产/影子表、``qlib_export``、``qlib_bin`` 快照。
- **`run_timeseries_sync_pipeline.py`**：``status-mysql`` / ``sync-mysql-csv`` / ``dump-qlib`` / ``run-mysql-missing``；默认 ``TDX_SYNC_ENABLE_TIMESCALE=0``。
- **`full_sync_all_from_tdx`**：``enable_timescale`` 改读 ``TDX_SYNC_ENABLE_TIMESCALE``，与已对齐三库解耦。

## 2026-06-05（Services 启动：stock / market_narrative 初始化修复）

- **`app/bootstrap_components/services.py`**：补全缺失的 `_try_init_stock_service`；修正 `_try_init_market_narrative_service` 误写为 `stock_service` 的问题，恢复 `MarketNarrativeService` 装配。修复 `python run.py` 启动时 `AttributeError: '_try_init_stock_service'`。

## 2026-06-05（分步时序同步管道 + CH 写入验收 + Timescale 断点）

- **`ClickHouseAdapter.execute_dml`** + **`write_bars_clickhouse`**：INSERT 失败不再虚增 `rows_written`（此前 HTTP 非 200 仍计数，导致 step1 显示 CH 847 万行但库内为 0）。
- **`timeseries_sync_status`**：`collect_timeseries_sync_status` / `run_timeseries_verify` 三库快照与对账。
- **`scripts/run_timeseries_sync_pipeline.py`**：`status` / `sync-clickhouse` / `sync-timescale` / `sync-failed` / `run-missing` / `verify`。
- **`tdx_timescale_sync_service`**：`timescale_backfill_state.json` 断点；高失败率暂停；默认 workers≤2。
- **`tdx_dayk_sync_service`**：Timescale 专用 worker 上限；连接瞬断重试；`timescale_sync_codes_from_tdx_dayk`；全量跳过 `ok_codes.txt`。
- **`docs/timeseries_backfill.md`**：补充分步管道说明。

## 2026-06-04（全量重跑：清表 + 探活 + 三库回填）

- **`timeseries_fresh_backfill`**：`truncate_all_timeseries_targets`、`preflight_timeseries_targets`。
- **`run_full_history_backfill_once.py`**：`FULL_BACKFILL_FRESH=1` / `FULL_BACKFILL_TRUNCATE=1` 先清 QDB/CH/Timescale；启动前 CH/SQL 探活；默认关闭逐批 matview。
- **`ClickHouseAdapter.connect`**：由 ``/ping`` 改为 ``SELECT 1``，避免密码错误仍显示 connected。

## 2026-06-04（Celery Worker 注册 Beat 任务）

- **`app/celery_app.py`**：`discover_task_modules` 提升为模块级函数；``worker_process_init`` 中调用，修复独立启动 Worker 时 ``KeyError: tdx_timescale_sync_tick`` / ``scanner_core_tick`` 未注册。

## 2026-05-25（CLI Timescale 写入：ensure_timescale_bar_port）

- **`timescale_bar_access.ensure_timescale_bar_port`**：CLI 未 bootstrap 时绑定 ``PostgresTimescaleBarRepository``，修复误报 ``timescale write produced no rows``（实为 port 未绑定、写入未执行）。
- **`tdx_timescale_sync_service` / `run_full_history_backfill_once.py``**：启动前调用 ``ensure_timescale_bar_port()``。

## 2026-05-25（全量脚本仅跑 Timescale）

- **`run_full_history_backfill_once.py`**：``FULL_BACKFILL_TIMESCALE_ONLY=1`` 跳过 QuestDB+CH，接续已完成的 step1 只跑 Timescale。

## 2026-05-25（全量脚本 Timescale 步：免 Qlib bootstrap）

- **`create_tdx_dayk_sync_service(require_qlib=False)`** + **`_TimescaleOnlyQlibStub`**：``run_full_history_backfill_once`` 第 2 步不再因 ``Qlib infrastructure not configured`` 退出。

## 2026-05-25（QuestDBAdapter PG 连接复用 + 全量 worker=3）

- **`QuestDBAdapter`**：PG 模式复用 ``_pg_conn``，避免每批 INSERT 新建连接导致 8813 拒绝。
- **`run_full_history_backfill_once.py``**：默认 ``TIMESERIES_SYNC_WORKERS=3``。

## 2026-05-25（QuestDB 旧表 schema 适配：date + timestamp）

- **`questdb_table_layout`**：`SHOW COLUMNS` 探测 `timestamp`/`date`/`trade_date`，写入、DEDUP、读链统一列名。
- **`questdb_ohlcv_writer`**：PG INSERT 写入 designated `timestamp`；DEDUP keys 随表结构。
- **`ohlcv_latest_reader` / `ohlcv_history_reader`**：QuestDB 查询用 `coalesce(date, cast(timestamp as date))`。

## 2026-05-25（全量入库脚本修复 + QuestDB PG 优先写入）

- **`scripts/run_full_history_backfill_once.py`**：修复 `step1` 摘要打印缩进错误；启动时打印 TDX 全市场规模与预估批次数。
- **`timeseries_ohlcv_sync_service`**：`ensure_questdb_dedup` 移至 `sync_mode` 解析之后，避免 `NameError`。
- **`questdb_ohlcv_writer`**：`QUESTDB_USE_PG_WIRE=1` 时优先 PG `INSERT`（8813），ILP 仅作备选；回填循环增加 `print` 批进度。

## 2026-05-24（QuestDB 默认 PG 线协议 8813）

- **`QuestDBAdapter`**：``QUESTDB_USE_PG_WIRE=1`` 时走 ``QUESTDB_PG_PORT``（8813）psycopg；8812 仅作 HTTP ``/exec`` 备选。
- **`.env`**：明确 ``QUESTDB_PG_PORT=8813`` 与 ``QUESTDB_HTTP_PORT=8812`` 分工，避免误连 8812。

## 2026-05-24（全量入库 CLI 修复 + QuestDB exec 回退）

- **`tdx_ohlcv_reader.ensure_tdx_local_file_port`**：CLI/Celery 未 bootstrap 时惰性绑定 TDX 文件端口。
- **`timeseries_ohlcv_sync`**：修复 `TIMESERIES_SYNC_ALL_MARKET` 吞掉分页 `limit` 的问题。
- **`questdb_ohlcv_writer`**：`questdb.ingress` 4.x + ILP 失败时 HTTP `/exec` 批量 INSERT 回退。
- **`scripts/run_full_history_backfill_once.py`**：一键 QuestDB+CH → Timescale 全量分页。

## 2026-05-24（幂等 + 增量防漏：重叠窗口 / min-latest / 去重）

- **`ohlcv_incremental_policy`**：统一 `TIMESERIES_INCREMENTAL_OVERLAP_DAYS` / `TDX_SYNC_INCREMENTAL_OVERLAP_DAYS`；增量从 `latest - overlap` 起同步；TDX filter 同步应用重叠。
- **QuestDB/CH**：游标改为 **min(latest)** 跨库；写入前 dedupe；CH `DELETE` + `mutations_sync=1`。
- **TDX dayk**：MySQL + Timescale 最新日合并取 **min** 再过滤；Timescale/MySQL 仍 `ON CONFLICT` / `ON DUPLICATE KEY`。
- **测试**：`tests/test_ohlcv_incremental_policy.py`。

## 2026-05-24（历史同步优化：读链/增量/幂等/对账）

- **读链**：`HISTORY_PREFER_TIMESERIES=1` 时 CN 顺序 questdb → clickhouse → timescale → mysql（`history_adapters._build_cn_history_adapters`）。
- **QuestDB/CH 同步**：按 `max(trade_date)` 真增量；写入前 `DELETE` 日期区间（`TIMESERIES_UPSERT_DELETE_RANGE`）；Beat 全市场（`TIMESERIES_SYNC_ALL_MARKET`）。
- **TDX 代码表缓存**：`tdx_code_cache.get_tdx_cn_universe`；回填批不再每批全目录扫描。
- **Timescale 增量**：`enable_mysql=False` 时用 `batch_get_latest_dates_timescale` 作游标；Beat 默认 `mode=incremental`。
- **Beat**：`TDX_USE_SCHEDULED_DAILY_CHAIN=1` 时用 `scheduled_cn_history_daily` 替代分拆 TDX+qlib 任务。
- **对账**：`ohlcv_reconciliation_service` + `POST /system/ohlcv-reconciliation`；可选 Beat 周六抽检。
- **ClickHouse DDL**：`ReplacingMergeTree`；`ohlcv_sync_common.safe_table_name` 补全。

## 2026-05-24（TDX 唯一数据源 + Timescale 独立任务）

- **数据源**：QuestDB / ClickHouse / Timescale 回填均从 **TDX lday** 读取；`ohlcv_sync_common.resolve_sync_symbols` 扫描 TDX，不再依赖 MySQL `stock_history_*`。
- **`tdx_dayk_sync_service`**：常规 `full_sync` / `incremental_sync` 默认 `TDX_SYNC_ENABLE_TIMESCALE=0`；新增 `timescale_full_sync_from_tdx_dayk`（仅 Timescale，`enable_mysql=False`）；`enable_mysql` 控制 MySQL 增量游标。
- **`tdx_timescale_sync_service`** + **`tdx_timescale_sync_tasks`**：独立 Celery / `POST /system/tdx-timescale-sync`；Beat `TIMESCALE_TDX_SYNC_BEAT`。
- **文档**：`docs/timeseries_backfill.md`、`.env.example` 三管道说明。

## 2026-05-24（QuestDB/ClickHouse 历史数据全量回填）

- **`timeseries_ohlcv_sync_service`**：从 MySQL `stock_history_*` 枚举标的；并发拉取；`skip_existing` 跳过已回填；`run_timeseries_ohlcv_backfill` 分页全市场。
- **CLI**：`python -m app.cli timeseries-backfill --full --lookback-days 1500`；`--force` 强制重写。
- **DDL**：`scripts/questdb_stock_history_ddl.sql`、`scripts/clickhouse_stock_history_ddl.sql`。
- **API**：`POST /system/timeseries-ohlcv-sync` 支持 `full`、`force`、`offset`、`batch_size`。

## 2026-05-24（自选 SocketIO 刷新 + ClickHouse 日 K 同步）

- **`timeseries_ohlcv_sync_service`**：统一 QuestDB ILP + ClickHouse INSERT；`POST /system/timeseries-ohlcv-sync`。
- **`clickhouse_ohlcv_sync_service`** + `scripts/clickhouse_stock_history_ddl.sql`。
- **`self_stocks.html`**：监听 `quant:quote` 实时更新价格/涨跌幅。

## 2026-05-24（QuestDB 同步任务 + SocketIO 行情推送）

- **`questdb_ohlcv_sync_service`**：MySQL/TDX 日 K → QuestDB ILP（`stock_history`）；`POST /system/questdb-ohlcv-sync`；Beat 16:35。
- **`bootstrap_components/realtime`**：`ENABLE_SOCKETIO` 挂载 Flask-SocketIO；`ENABLE_QUOTE_WS_BROADCAST` 线程推送 `quote_update`。
- **`base.html`**：登录用户加载 socket.io 客户端，`quant:quote` 事件。
- **修复**：`websocket_adapter.py` `from flask import request`。

## 2026-05-24（QuestDB / ClickHouse 接入多数据源 K 线）

- **`ohlcv_history_reader`**：从 `stock_history`（`QUESTDB_OHLCV_TABLE`）读 OHLCV；ClickHouse 需配置 `CLICKHOUSE_OHLCV_TABLE`。
- **`MultiSourceHistoryProvider`**：A 股链增加 `questdb`、`clickhouse`（Timescale 之后）；`last_source` 标记命中源。
- **API**：`GET /api/v1/data/timeseries-bars`；健康探针含 `ohlcv_tables` 行数。

## 2026-05-24（QuestDB / ClickHouse 环境变量与探活）

- **`timeseries_settings`**：`QUESTDB_*`（HTTP 8812、PG 8813、ILP 9009）、`CLICKHOUSE_*` 从环境加载。
- **`timeseries_factory`**：工厂与健康探针 `timeseries_health_probe`。
- **`QuestDBAdapter` / `ClickHouseAdapter`**：`/exec` 与 JSONEachRow 查询；连接探活带认证。
- **API**：`GET /api/v1/data/timeseries-health`（登录）。
- **`.env.example`**：时序库配置段（密码占位，勿提交真实密钥）。

## 2026-05-24（元学习 Prompt 演化异步闭环）

- **`meta_learning_evolve_service`**：`asyncio.run(evolve_prompts)`；`instance/meta_learning` 持久化 patterns/state；24h 冷却。
- **`retail_meta_learning_tasks`**：Celery `meta_learning_evolve_tick`；Beat `RETAIL_META_LEARNING_BEAT` 周六 18:50。
- **`POST /api/v1/system/retail-meta-learning-evolve`**：管理员手动触发（`?force=1` 跳过冷却）。
- **`DynamicPromptBuilder`**：合并文件库规避模式到 `_load_error_patterns`。
- **`retail_meta_learning_status`**：展示上次演化、模式数量、最近 patterns。

## 2026-05-24（研报证据链 + 决策快照只读分享）

- **`EvidenceTraceabilityService`**：`yanbao_items` 匹配标的生成 `report_citations`；因子「研报覆盖」计数；`decision-brief` 经 `basic_market_data_service.yanbao_list` 注入。
- **`DecisionResearchSnapshotDTO`**：`share_token`、`share_public_path`；`FileDecisionSnapshotRepository.get_by_share_token`。
- **API**：`GET /api/v1/decision/snapshots/public/<share_token>`（免登录只读）。
- **页面**：`/share/decision/<token>` → `decision_snapshot_public.html`；个股证据弹窗、快照列表/复盘页展示研报摘要与「复制只读外链」。

## 2026-05-24（证据链溯源 + 决策快照 + 买卖计划软警告）

- **`EvidenceTraceabilityService`**：决策简报 `supporting_evidence`（成交量突破、RSI、MA20 距离 + 250 日分位）。
- **`DecisionSnapshotService`**：`POST/GET /api/v1/decision/snapshots`；页面 `/decision-snapshot/<id>` 复盘封存行情。
- **`TradePlanService`**：修复 `build_plan` 死代码；`soft_warnings` 结合 `SupportResistanceCalculator` 止损/支撑位提示。
- **`stock_detail.html`**：证据链弹窗、「生成快照」、买卖计划副驾驶警告展示。
- **`strategy_snapshots.html`**：Tab「决策研究快照」列表、复制分享链接、`?tab=decision` 深链。
- **`decision_flow_contract`**：自检探针含 `supporting_evidence`、决策快照、trade-plan 软警告。

## 2026-05-24（Timescale 物化视图 schema ensure 修复）

- **`timescale_adjusted_views.py`**：对已存在的 `market_bars_qfq`/`hfq` 物化视图不再 `DROP TABLE`；按 `relkind` 迁移旧物理表；已有物化视图仅补唯一索引，避免 ensure 失败与重复清空。

## 2026-05-24（影子成本线 + Top3 用户观察单 + 元学习状态 API）

- **`shadow_portfolio_weights.build_cost_basis_map`**：`portfolio_trade_service.calculate_holdings` 提供成本/浮盈。
- **`ShadowMirroringService`**：高浮盈/深浮亏优先减仓文案；`picks` 展示 `avg_cost`/`pnl_pct`。
- **`RecommendationService.daily_top`**：传入 `user_id`，胜率按当前用户观察单统计。
- **`GET /retail-assistant/meta-learning-status`**：AutoValidator Agent 排名与 Top3 调权说明。
- **`retail_assistant.html`**：元学习状态卡片。

## 2026-05-24（心理卫士成交反馈 + 影子操盘画像）

- **`psychology_execution_loader`**：`retail_user_{id}` 策略绑定；从 `execution_records` 同步读取成交事件。
- **`psychology_trade_hooks`**：QMT 成交后写入 `psychology_operations.json`（action buy/sell）。
- **`QMTExecutor` / `TradeSignalDTO`**：可选 `user_id`；成交反馈与心理样本双写。
- **`PsychologyGuardianService`**：FOMO/恐慌检测含 buy/sell；`data_sources` 含 `execution_feedback`。
- **`ShadowMirroringService`**：按投研画像 `risk_level`、重仓阈值个性化追涨/减仓文案。

## 2026-05-24（心理卫士用户巡检 + 审计足迹 + 分析修复）

- **`POST /api/v1/retail-assistant/psychology-scan`**：当前用户单检，可选 `notify` 推送（尊重 `psychology_alerts`）。
- **`run_psychology_guardian_for_user`**：批量服务抽取单用户入口；`build_psychology_guardian_service` 统一装配。
- **`PsychologyGuardianService`**：合并 `user_audit_trail` 交易类动作；修复 `analyze_user_behavior` 误用 `operation_history` 变量；时间戳解析兼容审计格式。
- **`trade_plan/adopt`**：写入审计 `trade_plan_adopt`，供心理卫士采样。
- **UI**：散户助手「立即巡检」；结果展示 `data_sources`；`refactor-status` 说明 Beat 环境变量与用户/管理员入口。

## 2026-05-24（心理卫士推送偏好 + 个股页迷你条）

- **`user_lifecycle_service`**：`DEFAULT_NOTIFICATION_PREFS` 增加 `psychology_alerts`（默认开）。
- **`user_notification_prefs.psychology_alerts_enabled`**：推送消息中心前检查偏好；Celery 无 lifecycle 时回读 `instance/user_lifecycle.json`。
- **推送门控**：`push_alerts_to_message_center`、自选 hook、批量巡检、`psychology-guardian?notify=1` 均尊重偏好。
- **UI**：`profile.html` 通知中心勾选 + 保存；`retail_assistant` 心理推送开关；`qa_user_center.mountPsychologyMiniStrip` + `stock_detail` 账户级提示条（非单股诊心理）。

## 2026-05-24（心理卫士横幅 + psychology-status API）

- **`GET /retail-assistant/psychology-status`**：轻量摘要供前端横幅。
- **`PsychologyGuardianService.status_summary`**：封装告警条数、首条消息与跳转链接。
- **`qa_user_center.mountPsychologyBanner`**：操盘台/自选股有告警时展示红色提示条。
- **`decision_flow_contract`**：自检增加 `psychology-status`；`refactor-status` 展示定时任务说明。

## 2026-05-24（心理卫士 Celery 巡检 + 导航高亮）

- **`psychology_guardian_batch_service`** / **`retail_psychology_tasks`**：批量扫描有操作记录的用户并推送消息中心。
- **`celery_app`**：`RETAIL_PSYCHOLOGY_BEAT=1` 时 11:35、15:12 执行；`ENABLE_RETAIL_PSYCHOLOGY_SCAN` 可关闭。
- **`POST /api/v1/system/retail-psychology-scan`**：手动触发（需数据写入权限）。
- **导航铃铛**：未读含心理提醒时橙色高亮，显示 `心理数/总数`；点击直达心理筛选。
- **集成中枢**：心理消息入口 + 手动巡检按钮。

## 2026-05-24（散户快捷入口 + 导航徽章 + 自选仓位权重）

- **`GET /retail-assistant/quick-actions`**：每日闭环快捷链接（操盘台/Top3/心理/影子/消息）。
- **`build_weights_from_watchlist`**：影子操盘优先使用自选组合权重（与组合详情一致）。
- **`message_center`**：支持 `?filter=psychology`；进入页更新 `quantMsgLastSeenTs` 清除导航徽章。
- **`base.html`**：导航铃铛 title 展示心理提醒条数。
- **`capabilities` / `retail_assistant`**：快捷入口条。

## 2026-05-24（消息中心心理筛选 + 影子仓位权重）

- **`routes_v1_task_ops`**：`task-messages` 支持 `category=retail_psychology`、`event` 过滤。
- **`message_center.html`**：全部 / 任务 / 心理卫士 筛选；心理消息展示建议与跳转链接。
- **`shadow_portfolio_weights`**：按行情估算持仓占比；`ShadowMirroringService` 重仓提示与加权减仓摘要。

## 2026-05-24（TDX 全量同步失败续跑 / 检查点）

- **`app/application/services/data/tdx_sync_checkpoint.py`**：`instance/tdx_sync/` 落盘 `failed_codes.txt`、`ok_codes.txt`、`last_run.json`；`filter_codes_resume` 跳过已成功代码。
- **`tdx_dayk_sync_service._run_sync`**：每轮结束写入检查点；返回 `failed_codes` / `checkpoint` 路径。
- **`retry_failed_from_tdx`**：仅重跑失败列表（`mysql_insert_only=False`，不清 `*_new`）。
- **`full_sync_all_from_tdx`**：支持 `resume_skip_ok`、`clear_checkpoint`。
- **`scripts/run_tdx_full_sync_all.py`**：`--retry-failed`、`--resume`、`--failed-file`、`--clear-checkpoint`；续跑时强制 `TDX_MYSQL_TRUNCATE_SUFFIX_TABLES=0` 与 UPSERT。

## 2026-05-24（影子操盘深化 + 心理观察单 + UI 校准徽章）

- **`ShadowMirroringService`**：按大师风格结合 PE/涨跌幅/持仓输出逐标的 `picks` 与组合摘要。
- **`routes_v1_retail_assistant/shadow-mirror`**：注入行情、自选与组合持仓。
- **`psychology_guardian_service`**：合并观察单 `adopt` 事件；FOMO 检测含 `adopt`。
- **`trade_plan/adopt`**：采纳后写入心理操作日志（`record_plan_adoption_event`）。
- **`daily_workbench` / `retail_assistant` / `self_stocks`**：Top3 展示 AI 校准徽章；影子操盘展示逐标的建议。

## 2026-05-24（心理卫士消息中心 + Top3 AutoValidator 调权）

- **`psychology_operation_store`**：记录用户自选股 add/remove 及当日涨跌幅。
- **`psychology_watchlist_hooks`**：加减自选后自动分析；有告警时 `task_message_store` 推送至消息中心。
- **`psychology_guardian_service`**：`load_operation_history`、`push_alerts_to_message_center`；`GET psychology-guardian?notify=1` 手动推送。
- **`routes_v1_portfolio_users`**：watchlist 变更挂钩心理卫士。
- **`recommendation_service`**：候选按综合分排序；`agent_calibration`（AutoValidator 记忆）参与 score 与 `estimated_win_rate`。
- **`task_message_store`**：新增标签 `retail.psychology_guardian`。

## 2026-05-24（refacter 对照页与自检探针 · 续）

- **`decision_flow_contract_service`**：`self_check_probes` 增加散户 Top3 / refactor-status / 心理卫士 / 影子操盘；`ui_surfaces` 增加 `retail_assistant`、`daily_workbench`。
- **`qa_user_center.js`**：`loadRefactorStatus`、`renderRefactorStatus`、`mountRefactorStatusPanel`。
- **`capabilities.html` / `architecture_roadmap.html`**：挂载 refacter 四维对照面板。
- **`retail_assistant.html`**：Top3、refacter 对照、心理卫士、影子操盘交互区；`overview` 模块卡片扩充。
- **`retail_assistant_hub_service.overview`**：注册 daily_top / psychology / shadow 模块。

## 2026-05-24（docs/refacter.md 散户闭环落地）

- **`recommendation_service`**：Top 推荐增加 `one_line_verdict`、产业链 `linkage`、决策简报/诊股链接；行业节点匹配 `INDUSTRY_CHAIN_CONFIG`。
- **`routes_v1_retail_assistant`**：`daily-top-picks`、`psychology-guardian`、`shadow-mirror`、`refactor-status`。
- **`retail_assistant_hub_service.refactor_status`**：四维能力对照表（供产品与架构页）。
- **`daily_workbench`**：今日推荐升级为 **AI Top 3** 卡片（区间/胜率/采纳）。
- **`self_stocks`**：影子操盘对接 API，移除硬编码演示数据。
- **`decision_flow_contract_service`**：增加 `retail_assistant` 契约条目。
- **`docs/refacter.md`**：改写为「愿景 vs 落地状态」对照文档。

## 2026-05-24（用户中心链路 · 十期：架构路线图对照）

- **`decision_flow_contract_service`**：契约版本 `2026-05-ux-decision-flow-v2`（含 ui_surfaces / self_check_probes）。
- **`qa_user_center.js`**：`renderUiSurfacesTable`、`loadDecisionFlowContract`。
- **`architecture_roadmap.html`**：动态 ui_surfaces 对照表、决策链路自检、鲜度/活跃任务；矩阵与增强卡片标注「已落地」项。

## 2026-05-24（用户中心链路 · 九期：研报/龙虎榜 + 决策流自检）

- **`routes_v1_market_aux`**：`/market/longhu`、`/market/yanbao` 响应附加 `data_timestamp` / `is_realtime` / `freshness`。
- **`decision_flow_contract_service`**：扩展 `evidence_hubs`、`ui_surfaces`、`self_check_probes`（7 项 API 探针）。
- **`qa_user_center.js`**：`runBasicDataRefresh`、`runDecisionFlowSelfCheck`、`renderEvidenceFeedFreshness`。
- **`capabilities.html`**：决策链路自检面板（调用契约探针列表）。
- **`yanbao_hub.html` / `longhu_bang.html`**：鲜度条、活跃任务、同步进度、个股「简报」链。

## 2026-05-24（用户中心链路 · 八期：鲜度 API + 能力总览 + Swarm）

- **`hot_sector_storage_service`**：`resolve_sectors` 响应附加 `data_timestamp` / `is_realtime` / `freshness`（`enrich_market_payload`）。
- **`hot_sectors.html`**：优先使用 API 返回的鲜度字段渲染条。
- **`qa_user_center.js`**：`renderHotSectorFreshness` 支持服务端鲜度 DTO。
- **`capabilities.html`**：全景鲜度、活跃任务；快速直达跳转 `#decision-brief-strip`。
- **`swarm_dashboard.html`**：鲜度/活跃任务、观测台/消息中心链、演示运行 Celery 进度（若有 `task_id`）、任务详情 Trace 链。

## 2026-05-24（用户中心链路 · 七期：通达信板块 / 观测台 / AI 研报）

- **`qa_user_center.js`**：`renderDecisionBriefMini`、`stockDetailBriefHref`（决策简报迷你渲染复用）。
- **`tdx_blocks.html`**：全景/快照鲜度条、活跃任务、成分股「简报」链。
- **`observability.html`**：市场鲜度 + 活跃任务；修复 `task-messages` 事件字段展示。
- **`AiResearchReport.js`**：研究报告完成后加载决策简报面板、「采纳到观察单」、`ai_research_report` 来源。

## 2026-05-24（用户中心链路 · 六期：任务中心 + 热点板块 + 研究页）

- **`app/tasks/registry.py`**：`GET /api/v1/tasks` 列表不再序列化 `func`，显式返回 `estimated_steps` 等元数据。
- **`static/js/qa_user_center.js`**：`renderHotSectorFreshness`、`mountActiveJobsPanel`；`runRegisteredTask` 支持 `onStarted`。
- **`task_center.html`**：卡片展示分阶段步骤、默认参数执行、活跃任务条、`QAUserCenter.runRegisteredTask` 异步进度。
- **`hot_sectors.html`**：快照鲜度条、成分股「简报」链至 decision-brief。
- **`research_pipeline.html` / `ai_research_report.html`**：市场全景鲜度 + 活跃任务侧栏。

## 2026-05-24（用户中心链路 · 五期：集成中枢 + 自选股）

- **`app/tasks/registry.py`**：`refresh_basic_market_data` 注册 `estimated_steps`（龙虎榜/研报/完成）与默认 `kind=all`。
- **`static/js/qa_user_center.js`**：`runRegisteredTask`、`fetchMarketQuotesFreshness`（`/markets/{m}/quotes`）、`freshnessBadgeHtml`。
- **`static/css/common.css`**：`.qc-freshness-badge` 行内鲜度标签样式。
- **`integration_hub.html`**：侧栏活跃任务、`QCTaskFeedback` 快捷触发基础市场刷新；修复 `task-messages` 字段（`ts`/`label`/`detail`）。
- **`self_stocks.html`**：自选卡片行情鲜度徽章、组合鲜度条、「简报」链至 decision-brief、「采纳」→ `POST /trade-plan/adopt`。

## 2026-05-24（用户中心链路 · 四期：全站 JS + 操盘台/全景/观察单）

- **`static/js/qa_user_center.js`**：全局 `QAUserCenter`（决策简报、采纳计划、鲜度条、活跃任务）；`base.html` 引入。
- **`static/css/common.css`**：`.qc-freshness-strip` 全站样式。
- **`daily_workbench.html`**：焦点标的决策简报条、活跃任务列表、买卖计划「采纳观察单」、上证鲜度提示。
- **`market_panorama.html` / `global_radar.html`**：全景数据鲜度条（`GET /markets/CN/panorama`）。
- **`signal_observations.html`**：按来源筛选（Copilot / 采纳 / 操盘台等）。

## 2026-05-24（用户中心链路 · 三期：stock_detail 前端对接）

- **`stock_detail.html`**：`loadDecisionBrief()` 单请求渲染简报、归因时间轴、产业链（`sector_context`）；行情鲜度条 `stockFreshnessStrip`；Copilot/买卖计划「采纳到观察单」→ `POST /api/v1/trade-plan/adopt`；`renderIndustryChain` 兼容 Map 与轻量产业链两种 DTO。
- **`message_center.html`**：侧栏 `loadActiveJobs()` 对接 `GET /api/v1/system/active-jobs`（刷新页后续传进度）。

## 2026-05-24（用户中心链路 · 二期：采纳计划 + decision-brief 增强）

- **`trade_plan_adoption_service`**：`build_plan` → `signal_observation` 持久化（观察单即「已采纳计划」）。
- **`routes_v1_trade_plan`**：`POST /trade-plan/adopt`、别名 `POST /trade-plans/adopt`。
- **`decision_brief_service`**：内嵌 `attribution_timeline` / `timeline_summary`、`sector_drilldown` 组件、quote 鲜度、`adopt_plan` 动作。
- **`routes_v1_strategy_copilot`**：`trade_plan_action` 改为 POST adopt + `strategy_id` / `reason` 预填。

## 2026-05-24（用户中心链路：聚合 DTO + 鲜度 + 任务续传）

- **`industry_chain_map_service`**：`build_chain` 别名 → `get_chain_map`，修复 `/industry-chain` 与诊股报告调用契约。
- **`routes_v1_stock`**：`/quotes` 附加 `data_timestamp` / `is_realtime`；`stock_detail` 与 `decision-brief` 增加 `sector_context`（`SectorContextService`）。
- **`routes_v1_market_core`**：全景 `panorama` 经 `enrich_market_payload` 附加鲜度字段。
- **`routes_v1_strategy_copilot`**：响应增加 `suggested_trade_plan` + `trade_plan_action`（复用 `trade_plan_service`）。
- **`routes_v1_task_ops`**：`GET /system/active-jobs`（`ActiveJobTrackerService` + 当前用户过滤）。
- **`market_tasks.refresh_basic_market_data`**：龙虎榜/研报分阶段 `report_task_progress`。
- **`stock_route_helpers`**、`data_freshness_service.enrich_market_payload`：路由层复用。

## 2026-05-24（多目标写入一致性）

- **`TDX_SYNC_STRICT_TARGETS=1`（默认）**：Timescale 失败不再吞异常；MySQL/Timescale/CSV 任一未写入则整股 `failed` 并 `rollback`；有失败股时拒绝 `swap_mysql_tables`。
- 建议全量时 **`TDX_MYSQL_COMMIT_PER_CHUNK=0`**，每股单事务提交，便于失败回滚。

## 2026-05-24（MySQL 2013 写入超时）

- **`mysql_sync_connect`**：同步专用直连，`TDX_MYSQL_READ/WRITE_TIMEOUT` 默认 600s。
- **`MySQLTdxDaykSyncSession`**：2013/2006/1205 自动重连重试；默认每块 commit（`TDX_MYSQL_COMMIT_PER_CHUNK`）；块大小默认 400。

## 2026-05-24（MySQL 1040 / 全量前准备）

- **`mysql_client`**：`dispose_mysql_engines`、`mysql_admin_execute`（直连 TRUNCATE，1040 重试）。
- **`full_sync_all_from_tdx`**：启动前释放连接池；默认 `TDX_MYSQL_TRUNCATE_SUFFIX_TABLES=1` 清空 `*_new`；`INSERT` 仅当 `TDX_MYSQL_INSERT_ONLY=1`（默认 upsert 可续跑）。
- **`TDX_MYSQL_MAX_WORKERS`** / **`_cap_mysql_sync_workers`**：限制并发，避免打满 `max_connections`。

## 2026-05-24（Timescale 物化视图 + qlib 前复权）

- **Timescale 仅存 2 表**：`market_bars`、`market_adjustment_factors`；`market_bars_qfq` / `market_bars_hfq` 改为物化视图（`timescale_adjusted_views.py`），同步后 `refresh_adjusted_materialized_views`。
- **默认**：`TIMESCALE_USE_ADJUSTED_MATVIEWS=1`，`TIMESCALE_STORE_ADJUSTED_BARS=0`；`TIMESCALE_REFRESH_MATVIEWS_ON_SYNC=1`。
- **qlib_bin**：默认 `QLIB_BIN_USE_TIMESCALE_QFQ=1`，导出**前复权** OHLCV。

## 2026-05-24（TDX 一键全量：MySQL + 因子 + Timescale + CSV + qlib_bin）

- **`TdxDaykSyncService.full_sync_all_from_tdx`**：单入口写齐五类产物；``*_new`` 时先灌表再 ``swap`` 后 ``mysql_to_bin_sync``。
- **`scripts/run_tdx_full_sync_all.py``**：``--swap-tables`` / ``--truncate-factors`` / ``--production``。
- **`MySQLTdxDaykRepository.truncate_adjustment_factors`**：全量前清空因子表。

## 2026-05-24（MySQL 日 K 重灌：影子表 + TDX 源）

- **`mysql_tdx_dayk_repository`**：`table_suffix` / `insert_only` 写入；`TDX_MYSQL_WRITE_CHUNK` 分块；`swap_reload_tables()` 原子 RENAME。
- **`TdxDaykSyncService.reload_mysql_history_from_tdx`**：仅 TDX lday + xdxr；默认 `stock_history_*_new`；`TDX_MYSQL_SYNC_WORKERS` 默认 3。
- **`scripts/run_tdx_reload_mysql_history.py`**：重灌与可选 `--swap-tables`。

## 2026-05-24（Timescale P1：xdxr 缓存 / bin 读 qfq）

- **`xdxr_cache.py`** + **`lday_reader.fetch_xdxr_data`**：进程内 LRU（`TDX_XDXR_CACHE_SIZE`）+ 并发限流（`TDX_XDXR_MAX_CONCURRENT`）。
- **Timescale 写入口径**：仅 TDX `lday` + `xdxr`（`TdxDaykSyncService` / `run_tdx_full_sync_timescale.py`），**不从 MySQL 回填**（MySQL 数据质量不可作为源）。
- **`qlib_pipeline_service`**：`QLIB_BIN_USE_TIMESCALE_QFQ=1` 时 `mysql_to_bin_sync` 优先读 `market_bars_qfq`。
- **Tests**：`test_xdxr_cache.py`。

## 2026-05-24（Timescale 写入性能 P0）

- **`postgres_timescale_bar_repository`**：`executemany` 分块批量 upsert；`TimescaleSyncSession` 单连接四表写入；模块级 `_SCHEMA_LOCK` 防多线程 `ensure_schema` 竞态。
- **`tdx_dayk_sync_service`**：线程内复用 `open_sync_session`（每股 commit）；池结束提交 `close_thread_timescale_session`；`TdxSyncStatsDTO` 汇总 timescale 行数。
- **配置**：`TIMESCALE_UPSERT_BATCH_SIZE`（默认 1500）、`TIMESCALE_STORE_ADJUSTED_BARS`（默认 1；0 则仅写 raw+因子）。
- **`timescale_sync_session.py`**：thread-local 会话辅助。

## 2026-05-24（运维脚本：TDX 全量 → Timescale）

- **`scripts/run_tdx_full_sync_timescale.py`**：bootstrap + `full_sync_from_tdx_dayk`（MySQL + Timescale + CSV）；支持 `--limit` / `--dump-qlib-bin`。
- 依赖：`pip install "psycopg[binary]>=3.2.0"`；PG 库 `quant_atlas` 需存在（可 `CREATE DATABASE` + `timescaledb` 扩展）。

## 2026-05-24（TimescaleDB 复权因子 + 前/后复权表）

- **`postgres_timescale_bar_repository`**：`market_adjustment_factors`、`market_bars_qfq`、`market_bars_hfq` hypertable；`upsert_ohlcv_package` 单事务写入四表。
- **`qfq_calculator.apply_hfq_to_rows`**：后复权计算；`TdxDaykSyncService` 同步包写入 Timescale。
- **`get_bars(adjust=raw|qfq|hfq)`**、**`get_factors`** 供读取。
- **Tests**：`test_qfq_hfq_calculator.py`、`test_timescale_ohlcv_package.py`。

## 2026-05-24（TimescaleDB 接入 TDX 日 K 双写）

- **`domain/ports/timescale_bar_port.py`**、`timescale_bar_access`：Port + bootstrap 绑定 `create_timescale_bar_repository`。
- **`tdx_dayk_sync_service`**：`USE_TIMESCALEDB=1` 时 `_persist_timescale_bars` 双写 `market_bars`；`SyncResult.timescale_rows`。
- **`history_adapters.TimescaleHistoryAdapter`**：CN 读路径 MySQL 之后尝试 TimescaleDB。
- **Tests**：`tests/test_timescale_dayk_dual_write.py`。

## 2026-05-24（股票历史入库 — 文档对齐）

- **`docs/HISTORY_DATA_READ_WRITE_FLOW.md`**：按阶段 A–D 重写（TDX→MySQL 主链路、读优先级、Beat、任务表、运维命令）。
- **`docs/CELERY_WORKER_DEPLOY.md`**：补充 `TDX_DAYK_CELERY_BEAT` 与推荐 Celery 任务表。

## 2026-05-24（股票历史入库 — 阶段 D）

- **读路径**：`MarketDataService` / `stock_service` A 股 **MySQL 优先**；`MultiSourceHistoryProvider` CN 顺序为 mysql → qlib → tdx → akshare → sqlite；`MySQLHistoryAdapter` 经 `create_tdx_dayk_repository`。
- **`MySQLTdxDaykRepository`**：`fetch_history_rows_for_code`、`list_stock_codes_updated_since`；`TdxDaykWritePort` 协议扩展。
- **`mysql_to_bin_sync`**：`days_lookback` 仅重导窗口内有更新的标的；`QLIB_MYSQL_BIN_DAYS_LOOKBACK` 配置项。
- **增量 TDX 同步**：`incremental_sync_from_tdx_dayk` 默认 `dump_qlib_bin=False`（与 Beat 分步 dump 一致）。
- **Tests**：`test_mysql_dayk_read_export.py`；`test_data_router_mysql_history` 适配新 Port 方法。

## 2026-05-24（股票历史入库 — 阶段 C）

- **`celery_app.py`**：`TDX_DAYK_CELERY_BEAT=1` 时注册 16:05 `sync_incremental_tdx`（`dump_qlib_bin=False`）与 16:25 `mysql_to_qlib_incremental_sync`；与 `QLIB_CELERY_BEAT` 并存时跳过重复的 16:10 mysql 任务。
- **`data_backfill_tasks.py`**：`sync_incremental_tdx` 支持 `dump_qlib_bin`；新增 `scheduled_cn_history_daily` 一键日更链路。
- **`config/config.cfg`**：增加 `TDX_DAYK_CELERY_BEAT` 开关说明。
- **`tasks/registry.py`**、**`tdx_dayk_tasks.py`**：标注推荐任务名与别名。
- **`tests/test_scheduled_cn_history_daily.py`**：日更编排与 Beat 注册单测。

## 2026-05-24（股票历史入库 — 阶段 A/B）

- **`infrastructure/repositories/common/deps.py`**：新增 `create_tdx_dayk_sync_service()`，统一 Celery / API / 脚本构造 `TdxDaykSyncService`。
- **`tasks/tdx_dayk_tasks.py`**、**`tasks/data_backfill_tasks.py`**、**`routes_v1_data_infrastructure.py`**、**`basic_market_data_service.py`**、**`core/container.py`**：改经工厂创建；`sync_today_history_tdx` 与增量日更对齐。
- **`tdx_dayk_sync_service.py`**：`SyncResult.status`（ok/skipped/failed）；统计区分 skipped/failed；增量模式 `TDX_SYNC_LDAY_TAIL` 尾部读 lday；写库前 `validate_ohlcv_history_rows`。
- **`domain/dto/sync_dto.py`**：`TdxSyncStatsDTO` 增加 `codes_skipped` / `codes_failed`。
- **`tests/test_tdx_dayk_sync_factory.py`**：工厂与 tail/状态单测。

## 2026-05-23（阶段 11：DI 单源 — 消除 bootstrap 对 container 补位）

- **`bootstrap_components/service_wiring.py`**：新增 `wire_legacy_container_services` 及 8 个显式 `wire_*` 函数；`wire_container_singletons` 改为 alias，不再 `from app.core.container import container`。
- **`bootstrap_components/services.py`**：改调用 `wire_legacy_container_services`。
- **`tasks/task_wiring.py`**：新增 `create_swarm_agent_service()`；**`tasks/auto_alpha_tasks.py`** 改经 task_wiring，移除 container 依赖。
- **`app/core/container.py`**：文档标注 legacy-only。

**验证**：`pytest tests/test_layer_boundaries.py tests/test_task_layer_boundaries.py -q`；`create_app()`。

## 2026-05-23（阶段 12：Application 禁止直连 commit / session_factory）

- **`domain/ports/mysql_connection_port.py`**、`mysql_connection_adapter.py`：Port 新增 `commit` / `rollback`。
- **`application/services/data/mysql_access.py`**：新增 `mysql_commit` / `mysql_rollback`。
- **Application**：`hot_sector_storage_service`、`tdx_dayk_sync_service`、`tdx_base_data_service` 改经 mysql_access；`ten_kings_sniper_service.get_selection_detail` 改经 `MySQLSniperRepository.get_selection_summary`。
- **门禁**：`tests/test_layer_boundaries.py::test_application_does_not_commit_or_touch_session_factory`。

**验证**：同上 + `rg "conn\\.commit" app/application` 应为空。

## 2026-05-23（阶段 13：热点板块仓储化 + DailyWorkbench DTO）

- **`domain/ports/hot_sector_storage_port.py`**：`HotSectorStoragePort` Protocol。
- **`mysql/mysql_hot_sector_repository.py`**：`em_hot_sector_*` 读写与快照 prune；`deps.create_hot_sector_repository`。
- **`HotSectorStorageService`**：移除 application 层 raw SQL / `mysql_connect`；路由经 deps 注入 repository。
- **`domain/dto/daily_workbench_dto.py`**：`DailyWorkbenchSnapshotDTO` 等 TypedDict；`DailyWorkbenchService.build_snapshot` 返回类型标注。
- **`wire_daily_workbench_service`**：bootstrap 注入 signal_flag / observation / trade_plan 等完整依赖。

**验证**：`pytest tests/test_layer_boundaries.py -q`；`create_app()`。

## 2026-05-23（阶段 14：Workbench 路由复用 + TDX 板块仓储化）

- **`route_deps.require_daily_workbench_service`**：`routes_v1_daily_workbench` 复用 `ctx.daily_workbench_service`，保留 deps 回退构造。
- **`services.py`**：`wire_daily_workbench_service` 移至 `wire_presentation_layer_services` 之后；`pool_service` alias 同步后移。
- **`TdxBlockReadPort`**、`mysql/mysql_tdx_block_repository.py`、`tdx_block_repository_access`；`tdx_block_membership_cache` / `tdx_block_stats_service` 改经 Port。
- **`deps.create_tdx_block_repository`** + `infrastructure_binding.bind_tdx_block_read_port`。

**验证**：`pytest tests/test_layer_boundaries.py -q`；`create_app()`。

## 2026-05-23（阶段 15：TDX 写入仓储化 + HotSector Null）

- **`mysql/mysql_tdx_dayk_repository.py`**：`MySQLTdxDaykSyncSession`（batch latest / write bars / factors / commit）。
- **`mysql/mysql_tdx_base_data_repository.py`**：基础数据 ingest 全事务；`mysql/null_hot_sector_repository.py`。
- **`tdx_data_repository_access`** + `deps.create_tdx_dayk_repository` / `create_tdx_base_data_repository`；bootstrap 绑定。
- **Application**：`tdx_dayk_sync_service`、`tdx_base_data_service` 移除 raw SQL / `mysql_connect`；`create_hot_sector_repository` 无 MySQL 时返回 Null。

**验证**：`pytest tests/test_layer_boundaries.py -q`；`bind_application_infrastructure(force=True)`。

## 2026-05-23（阶段 16：Qlib 导出 + 集成探针仓储化）

- **`MySQLTdxDaykRepository`**：新增 history 只读方法（calendar / stock codes / fetch rows）；`qlib_pipeline_service.mysql_to_bin_sync` 改经 `require_tdx_dayk_write_port()`。
- **`IntegrationProbePort`**、`mysql/mysql_integration_probe_repository.py`、`integration_probe_access`；`integration_stack_service` 移除 `mysql_connect`。
- **`deps.create_integration_probe_repository`** + bootstrap 绑定。

**验证**：`pytest tests/test_layer_boundaries.py -q`；`rg "mysql_connect" app/application` 应仅剩 `mysql_access.py`。

## 2026-05-23（阶段 17：仓储文档 + Null/Port 单测）

- **`docs/refactor/repositories-layout.md`**：补充 hot_sector / tdx_* / integration_probe 仓储与 `deps` 工厂、bootstrap Port 绑定表。
- **`tests/test_mysql_repository_ports.py`**：Null 热点仓储、deps 无 MySQL 工厂、TDX dayk 表名校验。

**验证**：`pytest tests/test_mysql_repository_ports.py tests/test_layer_boundaries.py -q`。

## 2026-05-23（阶段 18：Data Router MySQL 历史 + 热点回退单测）

- **`data_router_service.MarketDataService`**：`_query_mysql_history` 接 `TdxDaykWritePort`；get_history TDX 空结果时 MySQL 回退。
- **Tests**：`test_data_router_mysql_history.py`、`test_hot_sector_storage_service.py`。
- **`docs/QUANT_ATLAS_GUIDE.md`**：§5.1 阶段 11–17 摘要表。

**验证**：`pytest tests/test_data_router_mysql_history.py tests/test_hot_sector_storage_service.py -q`。

## 2026-05-23（阶段 19：Data Router 写入 Port 化 + 读写分离回退单测）

- **`data_router_service.MarketDataService`**：`_persist_to_mysql` 经 `TdxDaykSyncSessionPort` 写入；`write_backtest_result` 移除对 `mysql_session` 构造参数的硬依赖。
- **Tests**：`test_data_router_mysql_history.py` 扩展 persist / `ReadWriteSplitDataService` MySQL 回退。

**验证**：`pytest tests/test_data_router_mysql_history.py -q`。

## 2026-05-23（阶段 20：Data Router 构造精简 + 实时行情委托）

- **`data_router_service`**：移除 `mysql_session` 构造参数；`get_realtime_quote` 委托 `CnRealtimeQuoteService`（CN）。
- **`ReadWriteSplitDataService`**：构造签名精简为 `tdx_root_path` 可选。

**验证**：`pytest tests/test_data_router_mysql_history.py -q`。

## 2026-05-23（阶段 21：Scenario Optimizer + 跨市场行情）

- **`scenario_optimizer_service`**：`DataScenarioOptimizer` 移除 `mysql_session`；`HISTORICAL_RESEARCH` MySQL 回退；`monitor_realtime` 接 quote 路由。
- **`data_router_service`**：非 CN 行情经 `MarketDataProvider`。
- **`services/scenario_optimizer_service.py`**：presentation 路由 re-export shim。
- **Tests**：`test_scenario_optimizer_service.py`、跨市场 quote 单测。

**验证**：`pytest tests/test_scenario_optimizer_service.py tests/test_data_router_mysql_history.py -q`。

## 2026-05-23（阶段 22：Factor 衰减 + Data Optimizer 路由边界）

- **`forward_testing_service.FactorDecayMonitor`**：接 domain `FactorDecayDetector` 与 `decay_rate` 阈值。
- **`scenario_optimizer_service.write_result`**：WRITER_RESULT 写 MySQL Port。
- **`data_optimizer_access`** + **`routes_v1_data_optimizer`**：经 `TdxLocalFilePort` 工厂，去除 presentation 对 `tdx_file_adapter` 直连。
- **Tests**：`test_phase22_research_data_optimizer.py`。

**验证**：`pytest tests/test_phase22_research_data_optimizer.py tests/test_scenario_optimizer_service.py -q`。

## 2026-05-23（阶段 23：Presentation 边界 + 因子重训 + write-result API）

- **`test_layer_boundaries`**：已重构 data optimizer 路由禁止 providers/tdx_local 直连。
- **`FactorDecayMonitor.trigger_retrain`**：经 `IExperimentRepository` + swarm `factor_retrain` preset。
- **`routes_v1_data_optimizer`**：`POST /data/write-result`。

**验证**：`pytest tests/test_layer_boundaries.py tests/test_phase22_research_data_optimizer.py -q`。

## 2026-05-23（阶段 24：Hot Sector deps + OHLCV 校验 + 衰减日志）

- **`service_wiring.wire_hot_sector_storage_service`** + **`HotSectorRouteDeps`**；热点路由经 bootstrap 服务。
- **`history_row_validator`** + **`POST /data/write-result`** 字段校验。
- **`FactorDecayMonitor._record_decay_event`**：同步 factor repo 衰减日志。
- **Tests**：`test_phase24_hot_sector_history_validation.py`、presentation 边界扩展。

**验证**：`pytest tests/test_layer_boundaries.py tests/test_phase24_hot_sector_history_validation.py -q`。

## 2026-05-23（阶段 25：TDX Base 读 Port 化 + Hot Sector 挂载 + 衰减异步任务）

- **`TdxBaseReadService`** + **`TdxBlockReadPort`** 扩展；`routes_v1_tdx_base` 去除 `mysql_connect`。
- **`routes.py`**：`register_hot_sector_routes` 挂载。
- **`tasks/factor_decay_tasks.py`**：async `log_decay_event` Celery 落库；monitor 检测后 enqueue。

**验证**：`pytest tests/test_layer_boundaries.py tests/test_phase25_tdx_hot_sector_decay.py -q`。

## 2026-05-23（阶段 26：Health Port 化 + TDX Base deps + Factor Beat）

- **`SystemHealthProbeService`** + **`routes_v1_health`**：MySQL 探针经 `mysql_access`。
- **`TdxBaseRouteDeps`** + **`wire_tdx_base_read_service`**。
- **`celery_app`**：注册 `factor_decay_tasks`；Beat 说明见 roadmap（IC 巡检 vs 按需 decay log）。

**验证**：`pytest tests/test_layer_boundaries.py tests/test_phase26_health_tdx_deps.py -q`。

## 2026-05-23（阶段 27：Factor Lifecycle 任务修复 + Health 路由挂载）

- **`factor_lifecycle_tasks`**：`asyncio.run` 同步 runner；修正 `create_factor_repository` 路径；Celery 条件注册。
- **`celery_app`**：`FACTOR_LIFECYCLE_CELERY_BEAT=1` 启用 lifecycle / IC / cleanup 三条 Beat；worker 导入 `factor_lifecycle_tasks`。
- **`routes_v1_health`**：改为 `register_health_routes(blueprint, ctx)` 相对路径；**`routes.py`** 挂载；移除 `routes_v1_system` 简单 `/system/health` 别名。

**验证**：`pytest tests/test_layer_boundaries.py tests/test_phase26_health_tdx_deps.py tests/test_phase27_factor_lifecycle_health.py -q`。

## 2026-05-23（阶段 28：Presentation 边界扩展 — legacy / task_ops / health）

- **`legacy_routes`**：默认历史窗口改经 `core.utils.datetime_utils.default_history_window`。
- **`task_ops_access`**：Celery inspect/revoke 经 application helper（bootstrap `bind_task_ops_infrastructure`）；`routes_v1_task_ops` 去 `infrastructure.adapters` 直连。
- **`SystemHealthProbeService.probe_async_queue`**：health 路由 async queue 探针 Port 化。
- **边界测试**：`legacy_routes`、`routes_v1_task_ops`、`routes_v1_health` 纳入 presentation 门禁。

**验证**：`pytest tests/test_layer_boundaries.py tests/test_phase28_presentation_cleanup.py -q`。

## 2026-05-23（阶段 29：Memory / Monitoring / Metrics 路由去 infra 直连）

- **`MemoryOptimizationService.list_tables`**：`routes_v1_memory` 移除 `arrow_pool` 直连。
- **`monitoring_access`** + **`metrics_access`**：bootstrap 绑定；`routes_v1_monitoring` / `routes_metrics` 经 application helper。
- **`routes_metrics.py`**：修正 `datetime` import 顺序与 JSON 响应。
- **边界测试**：memory / monitoring / metrics 路由纳入 presentation 门禁。
- **附带修复**：`mysql_investment_manager_repository.py` 损坏的 import 块（阻塞 pytest 收集）。

**验证**：`pytest tests/test_layer_boundaries.py tests/test_phase29_presentation_cleanup.py -q`。

## 2026-05-23（阶段 30：Celery Worker DB cleanup + task_wiring 懒加载）

- **`worker_db_cleanup.cleanup_worker_db_resources`**：`task_postrun` / `task_failure` 对称释放 MySQL 连接与 worker scoped session。
- **`celery_app`**：`worker_process_init` 绑定 `ensure_task_bindings`；任务结束统一 cleanup。
- **`task_wiring`**：repository factory 改为函数内 lazy import（`common.deps`），避免 `market_tasks` 导入时触发全量 repo 注册。

**验证**：`pytest tests/test_phase30_celery_worker_cleanup.py -q`。

## 2026-05-23（阶段 31：Profile 分级 runtime config 校验）

- **`runtime_config_validator`**：`DEPLOY_PROFILE`（dev/prod/trading）+ `STRICT_BOOTSTRAP` 分级 fail-fast。
- **校验项**：MySQL URI 结构、Celery broker、QMT 路径（启用时）、trading profile 需 QMT、TDX 路径存在性（warning/error 分级）。
- **`bootstrap.create_app`**：引导末尾调用 `validate_runtime_config(settings)`。

**验证**：`pytest tests/test_phase31_runtime_config_validator.py tests/test_app_bootstrap.py -q`。

## 2026-05-23（阶段 32：Celery autodiscover + Worker STRICT 校验 + bootstrap 测试）

- **`celery_app`**：`_discover_task_modules()` 扫描 `app.tasks.*` 替代 15 条显式 import（Celery 默认 autodiscover 不适用扁平 tasks 包）。
- **`validate_worker_runtime_config`**：`worker_process_init` 在 `STRICT_BOOTSTRAP=1` 时 fail-fast。
- **`test_app_bootstrap`**：`BACKGROUND_POLICY` 断言与 `resolve_background_policy` 对齐。

**验证**：`pytest tests/test_phase32_celery_autodiscover.py tests/test_app_bootstrap.py -q`。

- **附带修复**：`execution_feedback_tasks.py` async/sync 语法（pkgutil 扫描新暴露）。

## 2026-05-23（阶段 33 / UX-1：统一归因 Report）

- **`AttributionReportDTO`** 扩展：`style_contributions`、`slippage`、`summary`、`scope`/`symbol`。
- **`UnifiedAttributionService`**：合并 `AttributionAnalyzer`、风格分解 Port、可选 slippage 分析。
- **`routes_v1_attribution`**：`/analyze`、`/report` 返回统一 DTO；支持 POST positions / factor 参数。

**验证**：`pytest tests/test_phase33_unified_attribution.py -q`。

## 2026-05-23（阶段 34 / UX-2：智能异常预警中心）

- **`AlertEventDTO` / `AlertCenterFeedDTO`**：统一告警模型（level / category / source）。
- **`AlertCenterService`**：聚合 TaskMessageStore、数据新鲜度、系统健康探针。
- **`routes_v1_alert_center`**：`GET /system/alerts`、`GET /system/alerts/summary`。

**验证**：`pytest tests/test_phase34_alert_center.py -q`。

## 2026-05-23（阶段 35 / UX-3：策略快照与回滚 MVP）

- **`StrategyDeploySnapshotDTO` / `StrategyRollbackResultDTO`**：部署快照与回滚结果模型。
- **`StrategySnapshotPort`** + **`FileStrategySnapshotRepository`**：`instance/strategy_snapshots` JSON 持久化。
- **`StrategySnapshotService`**：捕获 Git/SVN revision、`config/settings.json` 备份、基准数据新鲜度元数据；回滚返回 redeploy 步骤。
- **`routes_v1_strategy_snapshots`**：`POST/GET /strategy/snapshots`、`GET .../<id>`、`POST .../<id>/rollback`。

**验证**：`pytest tests/test_phase35_strategy_snapshots.py -q`。

## 2026-05-23（阶段 36 / SDK Facade：归因 / 预警 / 快照）

- **`app/sdk/facades/`**：`AttributionFacade`、`AlertsFacade`、`SnapshotsFacade` 薄封装 application 服务。
- **`QuantAtlasClient`**：暴露 `.attribution` / `.alerts` / `.snapshots`；`create_client()` 工厂；保留可选 `swarm` 与 `@strategy` 装饰器。
- **`app/sdk/__init__.py`**：公开 SDK 导出面。

**验证**：`pytest tests/test_phase36_sdk_facade.py -q`。

## 2026-05-23（阶段 37 / UX-1 前端：归因看板对接统一 DTO）

- **`pages.attribution_dashboard`**：注册 `/attribution-dashboard` 页面路由；导航「验证 → 策略归因」。
- **`attribution_dashboard.html`**：对接 `/api/v1/attribution/report`；展示 `summary`、`style_contributions`、 `slippage`、scope；ECharts 风格/因子/行业柱图。

**验证**：登录后访问 `/attribution-dashboard`；API `GET /api/v1/attribution/report?period=30d`。

## 2026-05-23（阶段 38 / UX-2 前端：智能预警中心看板）

- **`pages.alert_center`**：注册 `/alert-center`；导航「系统 → 预警中心」。
- **`alert_center.html`**：对接 `/api/v1/system/alerts`；级别/分类筛选、统计卡片、60s 自动刷新。

**验证**：登录后访问 `/alert-center`。

## 2026-05-23（阶段 39 / UX-3 v2：快照 settings 回写 + 前端 + Celery）

- **`StrategySnapshotService.rollback(apply_settings=True)`**：自动写回 `config/settings.json`，写前备份为 `settings.json.bak.*`。
- **`StrategyRollbackResultDTO`**：新增 `settings_applied`、`settings_backup_path`。
- **`routes_v1_strategy_snapshots`**：回滚 POST body 支持 `apply_settings`。
- **`tasks/strategy_snapshot_tasks`**：`capture_deploy_snapshot` Celery 任务供部署流水线挂钩。
- **`strategy_snapshots.html`** + `/strategy-snapshots`：快照列表、创建、回滚 UI。

**验证**：`pytest tests/test_phase35_strategy_snapshots.py -q`；登录后访问 `/strategy-snapshots`。

## 2026-05-23（阶段 40 / UX-2 v2：预警通知渠道 + 导航角标）

- **`AlertNotificationService`** + **`WebhookAlertChannel` / `DingTalkAlertChannel` / `EmailAlertChannel`**：env 配置 outbound 推送。
- **`routes_v1_alert_center`**：`POST /system/alerts/dispatch`；预警看板「推送通知」按钮。
- **`tasks/alert_dispatch_tasks`**：`dispatch_alert_notifications` Celery 任务。
- **`base.html`**：导航「预警中心」角标对接 `/system/alerts/summary`（critical 优先）。

**环境变量**：`ALERT_WEBHOOK_URL`、`DINGTALK_WEBHOOK_URL`、`SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`/`ALERT_EMAIL_TO`。

**验证**：`pytest tests/test_phase40_alert_notification.py -q`。

## 2026-05-23（阶段 41 / UX-2 v3：Beat 定时预警推送 + 去重）

- **`ALERT_DISPATCH_CELERY_BEAT`**：`celery_app._build_beat_schedule` 新增 `alert-dispatch-periodic`（默认关，`ALERT_DISPATCH_BEAT_MINUTES=30`）。
- **`AlertDispatchStateStore`**：同指纹告警在 `ALERT_DISPATCH_COOLDOWN_MINUTES` 内不重复推送；手动「推送通知」传 `respect_dedup=false` 跳过去重。

**环境变量**：`ALERT_DISPATCH_CELERY_BEAT`、`ALERT_DISPATCH_BEAT_MINUTES`、`ALERT_DISPATCH_MIN_LEVEL`、`ALERT_DISPATCH_LIMIT`、`ALERT_DISPATCH_COOLDOWN_MINUTES`。

**验证**：`pytest tests/test_phase40_alert_notification.py tests/test_phase41_alert_beat.py -q`。

## 2026-05-23（阶段 42 / UX-3 v3：部署钩子 + 受控代码回滚）

- **`strategy_snapshot_hook.capture_on_deploy`**：投资经理 `deploy_next_batch` / `apply_monthly_deploy_schedule` 成功后自动快照（`STRATEGY_SNAPSHOT_ON_DEPLOY`，默认开）。
- **`code_checkout.py`**：`rollback(apply_code=True)` 受控执行 git/svn checkout；需 `STRATEGY_SNAPSHOT_ALLOW_CODE_CHECKOUT=1`，prod 另需 `STRATEGY_SNAPSHOT_FORCE_CODE_CHECKOUT=1`。
- **`StrategyRollbackResultDTO`** 扩展 `code_applied` / `code_checkout_message`；快照页新增「完整回滚」按钮。

**验证**：`pytest tests/test_phase42_strategy_snapshot_v3.py tests/test_phase35_strategy_snapshots.py -q`。

## 2026-05-23（阶段 43 / UX-2 v4：微信模板消息预警）

- **`WeChatTemplateAlertChannel`**：公众号模板消息推送；env `WECHAT_ALERT_APP_ID/SECRET/TEMPLATE_ID/TO_OPENIDS`。
- **`build_default_alert_channels`** 纳入 `wechat`；dispatch 可选 `channels: ["wechat"]`。

**验证**：`pytest tests/test_phase40_alert_notification.py -q`。

## 2026-05-23（阶段 57 / UI-OPT：任务 SSE 推送）

- **`TaskEventHub`** + **`TaskStreamService`**：`TaskMessageStore.push` 广播生命周期事件；`GET /system/tasks/<id>/stream` SSE 推送反馈。
- **前端**：`QCTaskFeedback.watch` 优先 EventSource，失败回退轮询。
- **文档**：`docs/ui_opt-completion.md` UI-OPT 完成清单。

**验证**：`pytest tests/test_phase57_task_stream.py -q`。

## 2026-05-23（阶段 56 / UI-OPT：数据覆盖度指示）

- **`DataCoverageService`** + **`assess_bar_coverage`**：近 N 交易日 K 线覆盖率、滞后 gap、`level`/`warning`/`confidence_penalty`。
- **API**：`GET /stocks/<market>/<symbol>/data-coverage`；`ai/analyze`、证据链、个股详情/分析响应附带 `data_coverage`；信任分随覆盖不足降权。
- **前端**：`ai_analysis.html` / `stock_detail.html` 覆盖度警示条。

**验证**：`pytest tests/test_phase56_data_coverage.py -q`。

## 2026-05-23（阶段 55 / UI-OPT：全局焦点路由）

- **`FocusContextService`** + **`GET /api/v1/focus/context`**：规范化 symbol/market 与跨页 `share_links`（个股/AI/操盘台/回测/归因）。
- **`focus_context.js` 增强**：localStorage + URL 双向同步、`qa:focus-change` 事件、全站焦点栏快捷链接、`data-qa-focus-link` 装饰。
- **前端**：`base.html` 全局焦点栏；研究链路/AI 诊股/个股详情/操盘台与焦点联动。

**验证**：`pytest tests/test_phase55_focus_context.py -q`。

## 2026-05-23（阶段 54 / UI-OPT：数据事实化 + 结论追踪）

- **`market_fact`**（`app/domain/shared/market_fact.py`）：`close_fact` / `ma20_deviation_pct` / `trace_ref`；K 线与报价事实化标签。
- **API**：`stock_history` 每 bar 附带事实字段；`GET /stocks/...` 返回 `quote_fact`；假设证据项含 `trace_ref`。
- **前端**：`static/js/trace_link.js`（`QCTraceLink`）；`stock_detail.html` 价格区 MA 偏离展示；`ai_analysis.html` 假设证据「追踪」按钮。

**验证**：`pytest tests/test_phase54_market_fact_trace.py -q`。

## 2026-05-23（阶段 53 / UI-OPT：假设验证分析）

- **`HypothesisEvaluationService`** + **`HypothesisEvaluationDTO`**：基于指标/行情对预设或自定义交易假设给出佐证/反驳证据与 `verdict`/`confidence`。
- **API**：`POST /api/v1/ai/analyze` 支持 `hypothesis_id` / `user_hypothesis`；`GET /api/v1/ai/hypotheses` 返回假设目录；`GET /stocks/.../analysis` 与 `GET /ai/evidence` 同步支持假设参数。
- **前端**：`ai_analysis.html` 假设选择器 + 「假设验证」结果面板。

**验证**：`pytest tests/test_phase53_hypothesis_analysis.py -q`。

## 2026-05-23（阶段 52 / UI-OPT：对齐层 + K 线智能采样）

- **`DateAligner`**（`app/domain/shared/market_time_aligner.py`）：事件时间戳对齐到统一 `market_time_slot`（日级、市场、规范 symbol）；A 股盘前映射至上一交易日。
- **`bar_sampler`**（LTTB）：`GET /stocks/<market>/<symbol>/history` 支持 `max_points` / `width` 查询参数；响应 meta 含 `sampled` / `point_count` / `original_point_count`。
- **快讯对齐**：`HeadlineSignalEnrichmentService.enrich_headlines` 输出附带 `market_time_slot`（CN 使用 SSE 交易日历）。
- **前端**：`stock_detail.html` 初始 K 线请求携带 `max_points`（按图表容器宽度）；加载更早历史时不采样。

**验证**：`pytest tests/test_phase52_alignment_sampling.py -q`。

## 2026-05-23（阶段 51 / UI-OPT：异步任务反馈）

- **`TaskProgressStore`**（`instance/task_progress/`）+ **`TaskFeedbackService`**：步骤/进度/消息聚合 Celery 状态与 task messages。
- **API**：`GET /api/v1/system/tasks/<task_id>/feedback`；`/tasks/run` 异步模式返回 `estimated_steps` 并初始化进度。
- **Worker**：`task_wiring.report_task_progress` / `finalize_task_progress`；Celery prerun/postrun/failure 钩子更新进度。
- **前端**：`task_feedback.js`（`QCTaskFeedback.watch`）；任务中心异步执行展示步骤条与轮询。

**验证**：`pytest tests/test_phase51_task_feedback.py -q`。

## 2026-05-23（阶段 50 / UI-OPT：因子对标 + 交易预检）

- **`AttributionCompareService`** + **`GET /api/v1/attribution/compare`**：双标的因子贡献差分（`AttributionCompareDTO`）。
- **`PreTradePreflightService`** + **`POST /api/v1/trading/preflight`** / **`GET /strategy/copilot/preflight`**：结构化风控评分与阻断项。
- **前端**：`ai_analysis.html` 因子对标面板；`stock_detail.html` 对标区 + 策略 Copilot「交易预检」弹窗。

**验证**：`pytest tests/test_phase50_compare_preflight.py -q`。

## 2026-05-23（阶段 47–48 / UI-OPT：可操作错误 + 全局健康指示）

- **可操作错误**：`actionable_error_catalog.py` 为常见 error code 附加 `hints`（标题/说明/修复链接）；`error_handlers` 统一 `enrich_error_payload`；前端 `api_error_banner.js`（`QCApiError.renderBanner`）。
- **全局健康防御 UI**：`SystemHealthBannerService` 抽取工作台健康条逻辑；`GET /api/v1/system/health-banner`；导航栏健康指示灯 + 页面顶栏 `system_health_indicator.js`（60s 轮询）。
- **操盘台**：加载失败时优先渲染 API 返回的可操作 hints。

**验证**：`pytest tests/test_phase47_48_ui_opt.py tests/test_phase45_ui_opt_workbench.py -q`。

## 2026-05-23（阶段 45 / UI-OPT：Decision Dashboard 升级今日操盘台）

- **Focus 上下文**：`static/js/focus_context.js`；工作台 API 支持 `?symbol=`；快照 `focus_context`。
- **决策证据 + 晨会模式**：`WorkbenchDecisionDTO` 扩展 `confidence` / `evidence`；`morning_call` 三栏（风险/机会/系统）；`health_banner` 聚合 AlertCenter + 集成栈。
- **信号标注 Celery + 缓存**：`HeadlineSignalCache`（`instance/headline_signals/`）、`HeadlineSignalEnrichmentService`、任务 `enrich_market_headlines`；Beat 开关 `HEADLINE_SIGNAL_CELERY_BEAT`；快讯 DTO 增加 `signal_tag` / `sentiment_score` / `affected_symbols`。
- **前端**：`daily_workbench.html` 焦点栏、健康条、晨会轮播、快讯气泡标签。

**验证**：`pytest tests/test_phase45_ui_opt_workbench.py -q`。

## 2026-05-23（阶段 44 / UX E2E：API 冒烟 + SDK 快速上手）

- **`tests/test_phase44_ux_smoke.py`**：登录后会话下 attribution / alerts / snapshots API 与三看板页面 200 冒烟。
- **`docs/sdk-ux-quickstart.md`**：SDK 与四项 UX 能力用法、环境变量、测试命令。

**验证**：`pytest tests/test_phase44_ux_smoke.py -q`。

## 2026-05-19 — 阶段 8a：行情缓存 / 龙虎榜入库 / Eastmoney 解析

- 纯逻辑下沉 domain：`eastmoney_parser.EastmoneyParser`
- 新增 Port：`QuoteCachePort`、`LonghuMappingPort`、`DataQualityPort`、`ConfigLoaderPort`
- application helpers：`quote_cache_access`、`longhu_mapping_access`、`data_quality_access`、`config_loader_access`、`market_data_ingestor_access`
- 涉及：`market_service`、`events/handlers`、`basic_market_data_service`、`ingest_handler`
- `tests/test_layer_boundaries.py` 扩展上述 infra 路径门禁

**验证**：`pytest tests/test_layer_boundaries.py ... -q`；`create_app()`。

## 2026-05-19 — 阶段 7d：剩余 `infrastructure.providers.*` 收敛

- 纯函数下沉 domain：`sector_board_metrics`（`rise_ratio` / `aggregate_member_stats`）
- 新增 Port：`CnFundamentalsPort`、`CnSectorBoardPort`；infrastructure 适配器 + bootstrap 绑定
- application helpers：`cn_fundamentals_access`、`cn_sector_board_access`、`news_provider_access`、`async_market_access`、`strategy_providers_access`、`backtest_engine_access`
- 涉及：`hot_sector_service`、`tdx_block_stats_service`、`basic_market_data_service`、`tool_facade_service`、`strategy_service`、`qlib_service`、`market_service`、`enhanced_market_service`、`engine.py`
- `tests/test_layer_boundaries.py` 禁止 application import `infrastructure.providers`（含子模块）

**验证**：`pytest tests/test_layer_boundaries.py ... -q`；`create_app()`。

## 2026-05-19 — 阶段 7c：`tdx_local` / `pytdx` Port 化

- 新增 Port：`TdxLocalFilePort`、`PytdxMarketPort`；infrastructure 适配器 + bootstrap 绑定
- 纯逻辑下沉 domain：`tdx_paths`、`pytdx_quote_mapper`、`pytdx_symbols`
- application helpers：`tdx_local_access`、`pytdx_access`
- 涉及：`tdx_base_data_service`、`tdx_dayk_sync_service`、`basic_market_data_service`、`data_router_service`、`pytdx_market_data_service`、`pytdx_api_service`、`cn_realtime_quote_service`
- `tests/test_layer_boundaries.py` 禁止 application import `infrastructure.tdx_local` / `infrastructure.pytdx` / `tdx_file_adapter`

**验证**：`pytest tests/test_layer_boundaries.py ... -q`；`create_app()`。

## 2026-05-19 — 阶段 7b：`MarketDataProvider` 注入收敛

- 新增 `app/application/services/helpers/market_data_provider.py`（`bind_market_data_provider` / `get_market_data_provider`）
- bootstrap `services.py` 启动时绑定；`providers.create_market_data_provider()` 返回 `MultiSourceMarketProvider`
- 纯函数下沉 domain：`market_history_utils.filter_sort_history`、`quote_factory.quote_to_dict`
- application 层移除对 `infrastructure.providers.market_data` 直连（含 lazy import / `MultiSourceMarketProvider()` fallback）
- 涉及：`market_service`、`cn_realtime_quote_service`、`cn_quote_snapshot`、`portfolio_trade_service`、`stock_service`、`tool_facade_service`、`bot_engine`
- `service_wiring.py` 统一改用 `get_market_data_provider()`
- `tests/test_layer_boundaries.py` 禁止 application import `infrastructure.providers.market_data`

**验证**：`pytest tests/test_layer_boundaries.py ... -q`；`create_app()`。

## 2026-05-19 — 阶段 7a：`SymbolNormalizer` 下沉 domain

- 实现迁至 `app/domain/shared/symbol_normalizer.py`
- `infrastructure/mappers/symbol_normalizer.py` 改为 re-export（兼容旧 import）
- application 层 11 个文件改从 `app.domain.shared.symbol_normalizer` 导入
- `tests/test_layer_boundaries.py` 禁止 application import `infrastructure.mappers.symbol_normalizer`

**验证**：`pytest tests/test_layer_boundaries.py ... -q`；`create_app()`。

## 2026-05-19 — 阶段 6 收尾：移除 qlib_pipeline_service → deps 重导出

- 删除 `qlib_pipeline_service.create_default_qlib_pipeline_service()`（application 层不再 import `infrastructure.repositories.deps`）
- Celery / bootstrap / container / rdagent / scripts 改直接从 `deps.create_default_qlib_pipeline_service` 装配
- `tests/test_layer_boundaries.py` 禁止 application import `infrastructure.repositories.deps`
- `tests/test_qlib_gate_benchmark.py` mock 路径同步

**验证**：`pytest tests/test_layer_boundaries.py tests/test_user_repository_port.py tests/test_settings_provider.py tests/test_api_error_handlers.py tests/test_qlib_gate_benchmark.py -q`；`create_app()`。

**阶段 6 完成**：application 层 `infrastructure.repositories.*` / `infrastructure.database.*` 直连已清零（providers/adapters 等待下一阶段）。

## 2026-05-19 — 阶段 6（续）：InvestmentManager / Moments / AnalysisReport / SignalObservation Port

- 新增 Port：`InvestmentManagerRepository`+`ManagerRow`、`MomentsRepository`、`AnalysisReportRepository`、`SignalObservationRepository`、`PriceAlertRepository`（含 `NullPriceAlertRepository`）
- infrastructure 门面实现 Port；`deps.create_*_repository` 工厂补齐
- application 移除对 `investment_manager_repository`、`moments_repository`、`analysis_report_repository`、`mysql_signal_observation_repository` 直连
- `workflows` 改走 `NullPriceAlertRepository`（原 `JsonPriceAlertRepository` 不存在）
- `service_wiring` 注入 signal observation / investment / moments 仓库
- `tests/test_layer_boundaries.py` 扩展门禁

**验证**：`pytest tests/test_layer_boundaries.py ... -q`；`create_app()`。

## 2026-05-19 — 阶段 6（续）：BasicMarketData / NewsArchive / SignalFlagPool Port

- 扩展 `IBasicMarketDataRepository` 覆盖龙虎榜/研报/财报快照全量读写方法
- 新增 `NewsArchiveRepository`、`SignalFlagPoolRepository` Port（`domain/ports/`）
- infrastructure 门面类实现对应 Port；`deps.create_*_repository` 统一返回 Port 实现
- application 移除对 `basic_market_data_repository`、`news_archive_repository`、`signal_flag_pool_repository` 直连
- 涉及：`basic_market_data_service`、`tool_facade_service`、`research_report_rag_service`、`signal_flag_service`、`investment_manager_service`（SignalFlag 部分）
- bootstrap `services.py` 改用 `create_basic_market_data_repository` / `create_signal_flag_pool_repository`
- `service_wiring.news_archive_repository` 改走 deps 工厂
- 修复 `agent_telemetry_service` 模块级 import 触发的循环依赖
- 修复 MySQL `list_longhu_latest_dates` raw cursor 行访问（`row[0]`）
- `tests/test_layer_boundaries.py` 扩展上述三仓库门禁

**验证**：`pytest tests/test_layer_boundaries.py tests/test_user_repository_port.py tests/test_settings_provider.py tests/test_api_error_handlers.py -q`；`create_app()`。

## 2026-05-19 — 阶段 6（续）：TdxGpcwRepository Port

- 新增 `TdxGpcwRepository` Port（`domain/ports/tdx_gpcw_port.py`）
- `MySQLTdxGpcwRepository` 实现 Port；新增 `NullTdxGpcwRepository`
- `deps.create_tdx_gpcw_repository(settings)`；bootstrap `bind_tdx_gpcw_repository`
- `gpcw_service` 移除 infrastructure 直连，改为 Port 委托；`gpcw_data_service` 合并为别名
- `routes_v1_data_infrastructure.tdx_gpcw_stats` 改走 `get_gpcw_service()`
- `tests/test_layer_boundaries.py` 禁止 application import `mysql_tdx_gpcw_repository`

**验证**：`pytest tests/test_layer_boundaries.py tests/test_user_repository_port.py tests/test_settings_provider.py tests/test_api_error_handlers.py -q`；`create_app()`。

## 2026-05-19 — 阶段 6（续）：MySQLConnectionPort + mappers 解耦

- 新增 `MySQLConnectionPort`（`domain/ports/mysql_connection_port.py`）、`MySQLConnectionAdapter` / `NullMySQLConnectionPort`
- `application/services/data/mysql_access.py` — bootstrap 绑定后提供 `mysql_connect()` / `ensure_mysql_schema()`
- `deps.create_mysql_connection_port(settings)`；`bootstrap_components/services.py` 启动时 `bind_mysql_connection_port`
- application 层 9 处 `mysql_client` 直连改为 `mysql_access`（含 `qlib_pipeline_service`、TDX 入库、热点板块、integration stack 等）
- `domain/dto/bar_data_factory.py` — `history_rows_to_bar_data_list`；`stock_service.get_bars_between` 不再 import `StockHistoryMapper`
- `gpcw_data_service` 修正 `MySQLTdxGpcwRepository(conn)` 误用，改为无参构造（仓库内部解析 settings）
- `tests/test_layer_boundaries.py` 扩展禁止 `mysql_client` 与 `database.mappers`
- `docs/refactor/layer-boundaries.md` 同步

**验证**：`pytest tests/test_layer_boundaries.py tests/test_user_repository_port.py tests/test_settings_provider.py tests/test_api_error_handlers.py -q`；`create_app()`。

## 2026-05-19 — 阶段 6：StockCache / StockMetadata Port + application 层解耦

**改动**：
- 新增 `StockCachePort`、`StockMetadataRepository` Port；`mysql_stock_metadata_repository.py`
- `deps.create_stock_cache()` / `create_stock_metadata_repository()` / `create_default_qlib_pipeline_service()` 收敛基础设施工厂
- application 移除对 `stock_cache_db`、`db_manager` 直连；改为 bootstrap 注入
- 涉及：`market_service`、`stock_service`、`signal_flag_service`、`scanner_service`、`admin_stock_service`、`investment_manager_service`、`workflows`
- `tests/test_layer_boundaries.py` 扩展门禁（models + db_manager + stock_cache_db）
- `docs/refactor/layer-boundaries.md` 更新；注明项目使用 SVN

**验证**：`pytest tests/test_layer_boundaries.py tests/test_user_repository_port.py -q`；`create_app()`。

## 2026-05-19 — 阶段 4 收尾：分层边界 CI 门禁

**改动**：
- `tests/test_layer_boundaries.py` — AST 扫描 `app/application/**`，禁止 import `infrastructure.database.models`
- `docs/refactor/layer-boundaries.md` — 规则说明与后续收敛项
- `docs/refactor/structural-debt-roadmap.md` — 阶段 0–5 全部标记完成

**验证**：`pytest tests/test_layer_boundaries.py tests/test_user_repository_port.py -q`；当前 application 层零违规；修复 `application/facades/__init__.py` UTF-16 编码损坏。

## 2026-05-19 — 阶段 4：UserRepository Port 与 MySQL/SQLite 实现对齐

**改动**：
- `repository_ports.py` — `list_all` 返回 `list[UserAccount]`；`create` 契约明确为 `UserAccount`
- 新增 `user_mapper.py` — ORM/行 → `UserAccount` 映射
- `mysql_repositories.MySQLUserRepository` — `_map_user`；`create(UserAccount)` 不再接受 ORM；`list_all` 返回 domain 类型
- `mysql_user_repository.py` — 改为 re-export  canonical 实现，消除重复类
- `sqlite_repositories` / `json_repositories` — 补全 Port 抽象方法 `create/update/delete/list_all`
- `async_mysql_repositories` — `get_by_id` / `create` / `list_all` 对齐 `UserAccount`
- `tests/test_user_repository_port.py` — Port 合规与 JSON CRUD 回归

**验证**：`pytest tests/test_user_repository_port.py tests/test_settings_provider.py -q`；`SQLiteUserRepository(':memory:')` 可实例化。

## 2026-05-19 — 阶段 3（续）：routes.py 路由外迁 + 个股端点 bug 修复

**改动**：
- 新增 `routes_v1_stock.py` — `/stocks/*`、`/quotes`（含 longhu-band / research-reports / news-archive）
- 新增 `routes_v1_market_aux.py` — longhu / yanbao / pulse / basic-data refresh
- 新增 `routes_v1_task_ops.py` — task-messages / celery inspect / factor-ic-check
- 新增 `routes_v1_strategy_copilot.py` — `/strategy/recommend`、`/strategy/copilot`
- `routes.py` 由 ~760 行减至 ~130 行，仅保留注册与 `create_api_blueprint`
- **Bug 修复**：`stock_research_reports` 补 `require_ctx_service(ctx, "fundamental_access")`；`stock_news_archive` 补 `require_ctx_service(ctx, "news_archive")`

**验证**：`pytest tests/test_settings_provider.py tests/test_api_error_handlers.py -q`；`create_app()`。

## 2026-05-19 — 结构性技术债：阶段 0–5（配置 / DI / 路由 / Port / 插件）

**改动**：
- **阶段 0**：`docs/refactor/structural-debt-roadmap.md`、`config-call-sites.md`；`tests/test_settings_provider.py`
- **阶段 1**：`app/config/` 包（`settings.py`、`slices.py`、`settings_provider.py`）；删除根 `app/config.py`；`AppSettings` 增加 `data_backend` / `qmt` / `ths` 切片属性；`app/` 内业务代码全部改为 `get_settings()`（仅 `settings_provider.py` 保留 `from_env()`）
- **阶段 2**：`service_wiring.wire_trading_execution()`；`container.py` 标注 deprecated、QMT 经 `_build_qmt_executor`；`app/tasks/*` 使用 `get_settings()`
- **阶段 3（部分）**：新增 `routes_v1_market_core.py`（panorama/quotes/pool/movements/sentiment/headlines）；`routes.py` 注册并删除对应内联 handler
- **阶段 4（试点）**：`domain/ports/repository_ports.py` — `UserRepository` 部分方法返回 `UserAccount`
- **阶段 5**：`app/core/plugins.py` — `PluginLoadReport`、`PLUGINS_ENABLED`、`PLUGINS_ALLOWLIST`；`bootstrap` 顺序 logging → settings → plugins
- **事故修复**：PowerShell 批量替换损坏 `app/tasks/*.py` UTF-8；已修复 `signal_flag_tasks`、`investment_manager_tasks`、`moments_tasks` 等未闭合字符串

**验证**：`pytest tests/test_settings_provider.py tests/test_api_error_handlers.py -q`；`python -c "from app.bootstrap import create_app; create_app()"`；`rg "AppSettings\.from_env\(\)" app` 仅 `settings_provider.py`。

## 2026-05-19 — 热点板块 / 同花顺 Provider：超时与空列表修复

**改动**：
- `cn_ths_sectors` — 榜单 AJAX 改回 `index/field/additional`；无表格时链接回退解析；`detail` URL 作回退；四类板块并行抓取；region/csrc 不再强依赖 akshare
- `hot_sector_service` — 多源 `ThreadPoolExecutor` + `HOT_SECTOR_LIVE_BUDGET_SEC`（默认 22s）预算
- `hot_sector_storage_service` — `_load_live_sectors` 返回 `warnings`；ingest 修复 tuple 解包
- `routes_v1_hot_sectors` — 入库失败 → `ExternalServiceError`
- `hot_sectors.html` — AJAX 45s 超时、展示 `warnings`、空列表提示
- `tests/test_cn_ths_sectors_fetch.py` — URL/别名单测

**验证**：`pytest tests/test_cn_ths_sectors_fetch.py -m "not integration" -q`；live `kind=em` ~2s、`kind=all` ~13s 有数据。

## 2026-05-19 — 阶段 21：附属 API `ok_response` + 403 结构化

**改动**：
- `routes_v1_attribution`、`routes_v1_challenges`、`routes_market_sentiment`、`routes_v1_nl`、`routes_i18n` — 成功体改为 `ok_response`
- `routes_v1_portfolio_users`、`routes_v1_admin_stocks` — `abort(403)` → `AuthorizationError`
- 前端：`attribution_dashboard`、`market_panorama`、`investment_managers`、`index`（Jarvis NL）兼容 `status: success` + `data`
- `tests/test_api_error_handlers.py` — `AuthorizationError` 映射

**验证**：`pytest tests/test_api_error_handlers.py -q`；`create_app()`。

## 2026-05-19 — 阶段 20：Agent Swarm 成功体统一 + moments / 投资经理

**改动**：
- `routes_v1_agent_swarm` — 成功响应由 `ResponseEnvelope` 改为 `ok_response`（`status: success` + `data`）；`/runs` 返回 `data.runs`
- `swarm_dashboard.html`、`agent_lab.html`、`expert_teams.html` — 兼容 `json.data` 与旧 envelope
- `routes_v1_moments` — `abort(400)` → `ValidationError`
- `routes_v1_investment_managers` — 经理不存在 → `NotFoundError`
- `docs/architecture_bootstrap.md` — Agent Swarm 成功契约说明更新

**验证**：`pytest tests/test_api_error_handlers.py -q`；`create_app()`。

## 2026-05-19 — 阶段 19：`routes_v1_portfolio_users` 业务失败统一抛异常

**改动**：
- `routes_v1_portfolio_users` — 自选股/分组/用户/密码等 `(success, message)` 失败路径改为 `_require_ok` → `ValidationError`；导出失败、空 symbol、移动分组失败同步；`add_group_stock` 未预期异常 → `ExternalServiceError`
- `tests/test_api_error_handlers.py` — 补充 `NotFoundError` / `ExternalServiceError` 映射用例

**验证**：`pytest tests/test_api_error_handlers.py tests/test_route_deps*.py -q`；`create_app()`。

## 2026-05-22 — 阶段 18：Agent Swarm 错误契约 + API 文档

**改动**：
- `routes_v1_agent_swarm` — 错误路径改为 `ValidationError` / `NotFoundError` / `ExternalServiceError`；成功仍 `ResponseEnvelope.success`
- `docs/architecture_bootstrap.md` — 新增「API 错误契约」小节（错误 JSON 形态、异常对照表、检查清单）

**验证**：`create_app()`。

## 2026-05-22 — 阶段 17：market 模块 / challenges / attribution / 横切装饰器

**改动**：
- `modules/market_routes` — UseCase 失败 → `ValidationError`（`_require_success`）
- `routes_v1_challenges`、`routes_v1_attribution`、`routes_market_sentiment` — 异常 → `ExternalServiceError`
- `decorators.wrap_api_errors` — `ApplicationError` 交全局 handler（不再 `jsonify ok:false`）
- `dto_validation.validate_request` — Pydantic 失败 → `AppValidationError`

**验证**：`create_app()`。

## 2026-05-22 — 阶段 16：experiments / routes 内联 / portfolio_users / nl / i18n

**改动**：
- `routes_v1_experiments` — `NotFoundError`；补 `from __future__ import annotations`
- `routes.py` `/system/celery/inspect` — Celery 未启用时 `ExternalServiceError`（不再 200 + `ok:false`）
- `routes_v1_portfolio_users` 头像上传失败 → `ValidationError`
- `routes_v1_nl`、`routes_i18n`、`agent_swarm/routes` — 错误体统一

**验证**：`create_app()`。

## 2026-05-22 — 阶段 15：arch / ten_kings / ai_hedge_fund / global_market 错误体

**改动**：
- `routes_v1_arch` — 7 处 `jsonify({"error"})` → `NotFoundError` / `ValidationError`（经全局 error handler）
- `routes_v1_ten_kings`、`routes_v1_ai_hedge_fund`、`routes_v1_global_market` — 同步统一

**验证**：`create_app()`；`rg 'jsonify\\(\\{\"error' app/presentation/api/routes_v1_*.py` 应仅剩 arch 内 contract 演示端点的 `valid:false` 体。

## 2026-05-22 — 阶段 14：`routes_v1_data_optimizer` 契约统一

**改动**：
- `DataOptimizerRouteDeps` + `build_data_optimizer_route_deps`
- `routes_v1_data_optimizer` — `symbols`/`TDX` 错误改为 `ValidationError` / `ExternalServiceError`；抽取 `_resolve_tdx_root` / `_scenario_service` 去重

**验证**：`tests/test_route_deps_data_optimizer.py`；`rg 'data=\\{\"error' app/presentation/api/routes_v1_*.py` 应为空。

## 2026-05-22 — 阶段 13：data_infra / memory / task_pipeline + PortfolioTrade

**改动**：
- `MemoryRouteDeps` / `TaskPipelineRouteDeps` / `DataInfrastructureRouteDeps` — 对应路由启动期绑定服务
- `routes_v1_memory`、`routes_v1_task_pipeline`、`routes_v1_data_infrastructure` — 参数/资源错误改为 `ValidationError` / `NotFoundError` / `ExternalServiceError`
- `wire_portfolio_trade_service` — 交易记录服务迁入 bootstrap；`PortfolioRouteDeps` + `routes_v1_portfolio` 不再 handler 内 `new`

**验证**：`tests/test_route_deps_infra_memory.py`；`create_app()` 后 `portfolio_trade_service` 非空。

## 2026-05-22 — 阶段 12：FinGPT / 推荐链装配 + 路由 Deps

**改动**：
- `wire_analytics_feature_services` — `fingpt`、`trade_plan`、`selection_source`、`ai_evidence`、`recommendation` 依次装配；`wire_ai_research` 前确保 FinGPT
- `FinGptRouteDeps` / `RecommendationRouteDeps` — `routes_v1_fingpt`、`routes_v1_recommendations` 启动期绑定；推荐不可用不再 200 空列表
- `routes_v1_risk` — 参数校验改为 `ValidationError`

**验证**：`tests/test_route_deps_fingpt_recommendation.py`；`create_app()` 检查 `fingpt_application_service` / `recommendation_service`。

**修复（装配链）**：
- `wire_ten_kings` / `_fingpt_persistence` — 使用 `db_manager.get_session` 替代 `mysql.get_session`（避免中断 `wire_extended`）
- `wire_selection_source_service` — 从 `qlib_pipeline_service` 导入 `create_default_qlib_pipeline_service`；`ModelPredictLabService(market_provider=...)`
- `selection_source_service.py` — 补 `ValidationError` / `PredictionApplicationService` 导入

## 2026-05-22 — 阶段 11：Portfolio 路由契约 + Bootstrap 装配

**改动**：
- `service_wiring.wire_portfolio_service` — `PortfolioApplicationService` 迁入 bootstrap（不再在路由内 `new`）
- `route_deps.PortfolioRouteDeps` — `routes_v1_portfolio` 启动期绑定 `portfolio_service` / `watchlist` / `market`
- `routes_v1_portfolio` — 参数/鉴权/导入错误由 `ok_response(data={error})` 改为 `ValidationError`（400 统一 JSON）
- `portfolio_detail` — 修复 `market_service` 变量遮蔽；移除未使用的 `StockApplicationService` 临时构造

**验证**：`tests/test_route_deps_portfolio_routes.py`；`create_app()` 后 `portfolio_service` 非空。

## 2026-05-22 — 阶段 10：Celery 任务 + PortfolioUser Deps + Ten Kings

**改动**：
- `tasks/analysis_tasks.py`、`tasks/sniper_tasks.py` — `asyncio.run` → `run_async`
- `route_deps.PortfolioUserRouteDeps` — `routes_v1_portfolio_users` 启动期绑定 watchlist/stock_group（REQUIRED）
- `routes_v1_ten_kings` — `require_ctx_service` + `run_async`；路由经 `TenKingsSniperService.list_active_holdings` / `get_selection_detail`
- `service_wiring.wire_ten_kings_sniper_service` — MySQL `session_factory` 可用时装配；`routes.py` 注册 `/ten-kings/*`
- `v1_context.create_api_v1_context` — 透传 `ten_kings_sniper_service`
- `ten_kings_sniper_service.run_daily_scan` — 修复未定义变量 `regime` → `regime_enum`
- `mysql_sniper_repository` — `sqlalchemy.Decimal` 改为 `Numeric`（修复装配 ImportError）

**验证**：`tests/test_route_deps_portfolio.py`；`rg asyncio\\.run app/tasks` 应为空；无 MySQL 时 ten_kings 为可选（API 400）。

## 2026-05-22 — 阶段 9 续：应用层 `async_task` 与 Service 内 `asyncio.run`

**改动**：
- `application/services/base.py` — `async_task` 装饰器委托 `run_async`
- `basic_market_data_service.ingest_longhu_em` — 使用 `run_async`
- `events/event_bus.py` — 同步上下文中 async handler 使用 `run_async`

## 2026-05-22 — 阶段 9：`request_executor.run_async` 统一异步编排

**改动**：
- `app/application/request_executor.py` — `run_async()`：WSGI 路由内执行协程（无运行中 loop 时用 `asyncio.run`，否则线程池）
- `routes_v1_arch.py` — 移除 17 处 `get_event_loop` / `run_until_complete` 样板
- `routes_v1_quant_ai.py` — `ai/research`、`ai/chat` 改用 `run_async`

**验证**：`tests/test_request_executor.py`；`rg 'run_until_complete|asyncio\\.run' app/presentation/api` 应为空。

## 2026-05-22 — 阶段 8：清理 `getattr(ctx)` 动态探测

**改动**：
- 扩展 `route_deps`：`MarketRouteDeps`、`AiRouteDeps`、`WorkbenchRouteDeps` + `require_swarm_service`
- 迁移：`daily_workbench`、`signal_flag`（移除路由内 lazy init）、`quant_ai`、`agent_swarm`、`global_market`、`system`、`investment_committee`、`ai_hedge_fund`、`ai_committee_selection`
- `presentation/api` 路由层 `getattr(ctx` 仅保留 `common.ensure_service` 实现

**验证**：`rg 'getattr\\(ctx' app/presentation/api` 应仅剩 `common.py`；`pytest tests/test_route_deps.py`。

## 2026-05-22 — 阶段 6–7：服务就绪契约 + 路由 Deps 试点

**阶段 6**：
- `service_readiness.py` — REQUIRED/OPTIONAL/FEATURE_FLAG + `validate_service_readiness`（`STRICT_BOOTSTRAP=1` 严格模式）
- `wire_presentation_layer_services` — 原 `routes.py` 内 stock/watchlist/integration_stack 补丁迁入 bootstrap
- `routes.py` `create_api_blueprint` — 零服务构造；内联端点改 `require_ctx_service(ctx, ...)`
- `v1_context.py` — 移除 `__getattr__` 与工厂内 strategy_optimization 补丁

**阶段 7 试点**：
- `route_deps.py` — `RiskRouteDeps` / `SocialRouteDeps` + `build_*` / `require_*`
- `routes_v1_risk` / `routes_v1_moments` / `routes_v1_investment_managers` 改窄依赖注入
- `InvestmentManagerService.trade_stats_by_manager()` — 路由不再访问 `_repo`

**验证**：`tests/test_service_readiness.py`、`tests/test_route_deps.py`；`create_app()` 与 `rg '# Ensure' routes.py` 应为空。

## 2026-05-22 — 阶段 5 续：可选服务装配 + 剩余路由契约

**装配**（`service_wiring.wire_optional_application_services`）：
- `data_infrastructure_service`、`factor_*`、`research_report_rag_service`
- 用户域：`user_access_policy` / `audit` / `investment_profile` / `page_preference` → `user_lifecycle_service`（依赖 watchlist + stock_group）
- `news_archive_repository()` 固定 `instance/news_archive.db`，修复 `tool_facade` 的 `unable to open database file`

**路由**：`routes_v1_factor`、`routes_v1_ai_agent`、`integration_stack`、`portfolio_users`（登录后 stock-groups）、`ai_committee_selection` 统一 `require_ctx_service`。

## 2026-05-22 — 阶段 5：API 服务缺失统一为 ValidationError(400)

**契约**：可选服务未装配时，路由使用 `require_ctx_service`（`common.ensure_service`）抛出 `ValidationError`，由全局 error handler 返回一致 JSON；不再在 `ok_response` 的 `data.error` 中静默降级，也不再因 `if service is None: return` 导致整段路由 **404**。

**改动（presentation/api）**：
- `routes_v1_user_lifecycle`、`routes_v1_ai_evidence`、`routes_v1_industry_chain`、`routes_v1_system`（ai-committee）
- `routes_v1_data_infrastructure` — `/tasks` 始终注册；数据质量/WebSocket/血缘等依赖 `_infra_service()`
- `routes_v1_investment_managers` / `routes_v1_moments` — `_svc()` 解析 + 始终注册；聚合统计失败记 `logger.warning`
- `routes_v1_strategy_optimization`、`routes_v1_risk`、`routes_v1_task_pipeline`、`routes_v1_memory` — 移除注册期 early return

**验证**：`create_app()` 导入成功；缺服务端点应返回 400 而非 404。

## 2026-05-22 — 阶段 4：ResearchPort 与 Agent 边界

**改动**：
- `domain/ports/research_port.py` — `ResearchPort` 抽象。
- `infrastructure/adapters/trading_agents_research_adapter.py` — 延迟 import `TradingAgentsService`。
- `ai_research_service.py` — 依赖 `ResearchPort`；`get_ai_research_service()` 供 tools 使用。
- `trading_agents_service.py` — `FinGPTApplicationService` 改为 `TYPE_CHECKING`，去掉 agents 模块级对 application 的硬依赖。
- `wire_ai_research_service` — bootstrap 装配 `AiResearchService`。
- `routes_v1_quant_ai` — `_require_ai_research_service()` 明确 422 而非 500。

## 2026-05-22 — 阶段 3：ApiV1Context 分组 + 扩展服务装配

**改动**：
- `v1_context_groups.py` — `MarketCtx` / `UserCtx` / `AiCtx` / `SocialCtx` / `SystemCtx` + `attach_context_groups`。
- `v1_context.py` — 保留扁平字段，工厂末尾挂载分组；`strategy_optimization` 迁至 `service_wiring`。
- `service_wiring.wire_extended_services` — `signal_observation`、`review_tracking`、`kronos`（需 `session_factory`）、`strategy_optimization`。
- 投资经理/朋友圈路由可从 `ctx.social.*` 回退解析服务。

## 2026-05-22 — 修复 investment-managers / moments API 404

**根因**：`register_investment_manager_routes` / `register_moments_routes` 在 `ctx.*_service is None` 时直接 `return`，路由未挂载；`InvestmentManagerService` 在 `container` 中无参 Singleton 无法构造。

**改动**：
- `service_wiring.wire_feature_services` — 按 MySQL/session_factory/SQLite 装配 `InvestmentManagerRepository` + `MomentsRepository` 及对应 Application Service。
- `create_services()` 调用 `wire_feature_services`；`container` 移除无效 `InvestmentManagerService` Singleton。

**验证**：`/api/v1/investment-managers/leaderboard`、`/api/v1/moments/feed` 已出现在 url_map。

## 2026-05-22 — 阶段 1–2：单轨引导 + 拆除 Service Locator

**阶段 1（单轨 DI）**：
- `routes_v1_ai_hedge_fund` / `routes_v1_agent_swarm` / `routes_v1_monitoring` 改为 `ctx` 或 `app.extensions`，移除 presentation 层 `Container()` 直调。
- `plugins.py` 移除未使用的 `container` 导入。
- `pipeline/executor.py` 改为从 `service_bundle` 解析服务。
- `auto_alpha_tasks` 使用模块级 `container` 单例。

**阶段 2（Service Locator）**：
- 移除 11 处 `@service` 装饰器；`bootstrap` 不再调用 `register_services()`。
- 新增 `bootstrap_components/service_wiring.py`：显式装配 strategy/gpcw/tool_facade + `wire_container_singletons`。
- `create_services()` 删除全部 `_try_get` 扫描逻辑。
- `service_locator.register_services/get_service` 标记 deprecated。
- 文档：`docs/architecture_bootstrap.md`。

**验证**：`create_app()`、`tests/test_auth_login_flow.py` 通过。

## 2026-05-22 — 方案 A：从参考目录手术式还原引导层

**参考基线**：`E:\project\myrepo\quant-atlas`（`bootstrap.py` + `bootstrap_components/` + `routes.py` + `v1_context.py`）。

**备份**：工作区四文件已存 `_restore_backup/2026-05-22/`。

**还原**：
- 自参考复制 `bootstrap.py`、`bootstrap_components/`、`routes.py`、`v1_context.py`。
- `container.py`：参考副本为破损 `SimpleContainer`（无 `container` 单例），已从备份恢复 `DeclarativeContainer` + `container = Container()`。
- `v1_context.py`：保留 `__getattr__`、`ten_kings_sniper_service` 字段。
- `bootstrap_components/presentation.py`：`session_protection=basic`、`get_by_id`/`list_users` 回退、`enable_celery` 等传入 `create_api_blueprint`。
- 修复 `mysql_watchlist_repository` / `mysql_news_archive_repository` 中错误的 `...mappers` 导入路径。

**验证**：`create_app()` 成功；`tests/test_auth_login_flow.py` 通过。

## 2026-05-22 — 恢复 Flask-Login 初始化（login_manager 缺失）

**问题**：访问 `@login_required` 路由时报 `'Flask' object has no attribute 'login_manager'`；`bootstrap.py` 仅 import 了 `setup_flask_login_errors`，未创建 `LoginManager` 与 `user_loader`。

**改动**：
- `bootstrap.py` — `_setup_flask_login`：`LoginManager.init_app`、`login_view=auth.login`、`session_protection=basic`；`user_loader` 经 `get_by_id`（回退 `list_users`）加载 `SessionUser.from_entity`；调用 `setup_flask_login_errors`；`SESSION_COOKIE_SAMESITE` / `REMEMBER_COOKIE_SAMESITE` 默认 `Lax`；`create_auth_blueprint` 为 `None` 时不注册蓝图。
- `bootstrap.py` — `_register_template_i18n`：向 Jinja 注入 `_` / `t`（`app.core.i18n.t`），修复登录后 `daily_workbench.html` 等模板 `UndefinedError: '_' is undefined`。

## 2026-05-22 — 修复 ApiV1Context 缺失字段导致应用无法启动

**问题**：`create_app()` 在注册 `register_strategy_optimization_routes` 时访问 `ctx.strategy_optimization_service` 抛 `AttributeError`（`ApiV1Context` 被精简后未声明可选服务字段）。

**改动**：
- `v1_context.py` — 补全各路由可选 `*_service` 字段（默认 `None`）；`__getattr__` 对未知 `*_service` 返回 `None`；`create_api_v1_context` 从 container 注入 task/memory/industry/strategy_optimization 等。
- `routes_v1_strategy_optimization.py` — 使用 `getattr` 守卫。

## 2026-05-19 — A 股代码统一为 sh600519（移除 CN: 前缀）

**契约**：库表 / API / 内部逻辑 A 股 canonical 为 ``sh|sz|bj`` + 6 位；``MarketCode.CN`` 仍通过 URL/参数表达，不再写入 ``CN:`` 到 code 字段。

**改动**：
- `symbol_normalizer.py` — ``_strip_legacy_uid``；``to_db_code`` / ``parse_input`` 输出 ``sh600519``；补齐 ``from_db_code`` 等别名。
- `stock_repository` — 读写均 ``to_db_code``，不再拼接 ``CN:``。
- `tdx_base_data_service`、`routes_v1_tdx_base`（板块反向查询）、`signal_flag_service`、`stock_detail.html` 解析路由。
- `scripts/migrations/strip_cn_prefix_stock_codes.py` — MySQL 历史 ``CN:*`` 迁移脚本。
- `tests/test_symbol_normalizer.py` — 对齐新契约。

## 2026-05-19 — 同花顺四类板块入库与热点板块集成

**需求**：抓取 [概念](https://q.10jqka.com.cn/gn/)、[地域](https://q.10jqka.com.cn/dy/)、[同花顺行业](https://q.10jqka.com.cn/thshy/)、[证监会行业](https://q.10jqka.com.cn/zjhhy/) 板块与成分股，写入 MySQL，并在热点板块页筛选/入库。

**改动**：
- `cn_ths_sectors.py` — 四类板块统一抓取（会话预热 + ajax，失败回退首页表格）；成分股支持字母证监会代码；`fetch_ths_all_boards`。
- `hot_sector_service.py` — `get_ths_regions` / `get_ths_csrc_industries` / `get_ths_all_boards`；`vendor=ths` 含四类；成分股按 `normalize_ths_board_kind` 分流。
- `hot_sector_storage_service.py` — `ingest_ths_snapshot`、`_ingest_sectors` 重构；`kind=region/csrc/ths` 查询与 live 加载。
- `routes_v1_hot_sectors.py` — `POST /hot-sectors/ingest-ths`。
- `hot_sectors.html` — 「入库同花顺」按钮与筛选项。

## 2026-05-19 — 通达信板块成分股前端 `$box` 未定义

**问题**：点击板块后接口有数据，成分股不渲染；控制台 `Uncaught ReferenceError: $box is not defined` at `renderMembers`。

**改动**：
- `tdx_blocks.html` — `renderMembers` 内改为 `$('#membersBox').html(html)`（`$box` 仅在 `showMembers` 作用域内）；移除错误的 `apiIsSuccess` 占位逻辑。

## 2026-05-19 — 通达信板块 MySQL / 首屏再优化

**问题**：仍慢——相关子查询 COUNT、60 路 OR 拉成分股、首屏自动再请求 members；快照未命中仍触发 Pytdx。

**改动**：
- `tdx_block_membership_cache.py` — 按 `block_kind` 一次 SQL 加载成分股并内存缓存 5 分钟。
- `tdx_block_stats_service` — 板块 meta 改 `JOIN+GROUP BY`；行情**仅快照**，`prefer_tdx=False`。
- `tdx_blocks.html` — 首屏**不再自动加载**成分股，点击板块再加载。
- 入库后 `invalidate()` 成分股缓存；启动预热 `gn` 成分索引。

## 2026-05-19 — A 股行情快照与市场全景共享（通达信板块加速）

**问题**：通达信板块仍慢；市场全景 `/market-panorama` 快因其一次读取 `stock_cache` 全市场。

**改动**：
- `cn_quote_snapshot.py` — 进程内全市场索引（45s TTL），与 `list_quotes(CN)` / `/markets/CN/quotes` 同源。
- `market_service._list_cn_quotes` — 无 symbols 时**优先 SQLite 缓存**（与全景一致），再 AkShare。
- `routes.py` `market_quotes` — 全市场响应写入快照；板块/成分股从快照命中，仅补缺走 Pytdx/腾讯。
- `bootstrap` — 启动后台预热快照。

## 2026-05-19 — 通达信板块成分股行情改走 Pytdx 实时

**问题**：成分股加载仍慢，此前批量走腾讯 HTTP。

**改动**：
- `cn_realtime_quote_service.py` — A 股行情优先 `get_security_quotes`（Pytdx/TDX），未命中再回退腾讯。
- `pytdx/hq_api.py` — 每批最多 80 只自动分批（修复 >80 只只返回 80 条的问题）。
- `pytdx/quote_mapper.py` — Pytdx 行数据映射为统一 quote dict。
- `tdx_block_stats_service.py` — 汇总与成分股共用 `CnRealtimeQuoteService`。

## 2026-05-19 — 通达信板块加载性能与展示增强

**问题**：`/tdx-blocks` 加载极慢；板块/成分股信息字段过少。

**根因**：`TdxBlockStatsService.list_block_summaries` 对每个板块串行 `block_summary()`（N 次 MySQL + N 次腾讯行情）；成分股在前端再请求 `/markets/CN/quotes` 二次拉行情。

**改动**：
- `tdx_block_stats_service.py` — 批量 SQL 拉成分股、按 80 只一批 `get_realtime_quotes`；新增 `list_members_with_quotes`；板块表增加成分数、涨/跌家数、成交额、龙头代码。
- `routes_v1_tdx_base.py` — `members?with_quotes=1` 服务端一次返回行情。
- `tdx_blocks.html` — 单接口加载成分股；板块/成分股表格扩展列；显示加载耗时。

## 2026-05-19 — 个股详情 / 自选股实时行情修复

**问题**：详情页标题区与行情卡片无名称/价格/行业；自选股缺现价与涨跌幅。

**根因**：
- `StockApplicationService.get_stock_detail` 用严格 `domain.dto.QuoteData` 组装 `realtime`，字段不匹配导致校验失败（有行情时也落回空缓存）。
- `MarketApplicationService._list_cn_quotes` 仅查本地缓存，未命中时不调 `get_quotes` 拉实时。
- 自选股 `by_code` 仅用原始 code 索引，与 6 位代码不一致时对不上。
- **自选股（续）**：`WatchlistAgentService` 注入 `stock_service`；`list_quotes` 返回 `StockQuote` dataclass，而 `_to_dict` 无法解析 dataclass，生成 `{"value": ...}` 导致 `code`/`price` 全空。

**改动**：
- `app/application/services/market_data/stock_service.py` — `_quote_to_realtime`、规范 market/symbol、补全 `profile.name`/`industry`；`list_quotes` 返回按 6 位代码索引的 dict 列表。
- `app/application/services/market_data/market_service.py` — CN 列表缓存未命中时 provider 回填；`get_quotes` 按 6 位 code 索引。
- `app/application/services/market/watchlist_agent_service.py` — `_to_dict` 支持 dataclass；行情按 6 位代码匹配。
- `app/bootstrap_components/services.py` — `WatchlistAgentService` 改用 `MarketApplicationService`。
- `app/presentation/web/templates/stock_detail.html` — API URL 编码、兼容 `response.stock` 结构。

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

## 2026-05-11（API P0/P1 与因子仓 MySQL）

- **NL Parser**：`routes_v1_nl` 子蓝图 `url_prefix` 由 `/api/v1/nl-parser` 改为 `/nl-parser`，避免挂在 `api_v1`（`/api/v1`）下出现重复前缀；解析器改为 `app.application.services.ai.nl_parser.AdvancedNLParser`，成功响应使用 `dataclasses.asdict` 序列化；请求体统一 `request.get_json(silent=True)`。对外路径由错误的 `/api/v1/api/v1/nl-parser/...` 修正为 **`/api/v1/nl-parser/...`**。
- **Agent Swarm**：`routes_v1_agent_swarm` 的请求体校验改为 `app.domain.schemas.agent_schemas.SwarmRunRequest`（与 `SwarmAgentService` 一致，支持 `context`）；`POST /swarm/run` 使用 `get_json(silent=True)`。兼容实验列表/详情由误注册的 **`/api/v1/api/v1/experiments`** 修正为 **`/api/v1/experiments`**（主蓝图前缀 + `/experiments`）。
- **MySQL Factor Vault**：`mysql_factor_vault` 移除不存在的 `app.core.db.get_mysql_session`；改为 `AppSettings.from_env()` + `app.infrastructure.database.db_manager.get_session`；SQL 使用 `sqlalchemy.text` 与命名参数；`LIMIT` 做上下界钳制；读写路径在 `finally` 中关闭会话；DDL 在同一会话内 `_ensure_table` 执行，避免与 scoped session 生命周期冲突。

## 2026-05-11（以用户为中心的界面优化 · 第一批）

- **环境人话提示**：`pages._ux_env_hints` 根据 MySQL / TDX_ROOT_PATH / 大模型常见配置生成非阻断提示；`/`（今日操盘台）与 `/self-stocks` 模板顶部展示，并链到集成中枢或能力总览。
- **今日操盘台**：三步上手卡片、决策区与卡片头增加「自选 / 全景 / 观察单 / 龙虎榜」等主路径按钮；各区块骨架屏、空状态附「下一步」操作；接口失败时顶部错误条 + **重试**；兼容 `ok_response` 包裹的 JSON 结构。
- **自选股中心**：同构三步引导 + 空列表/无分组时的「建议下一步」清单；加载失败时 **重试** 与集成入口。
- **个股详情**：顶部增加与全站一致的 **研究链路式**「本页快捷跳转」条（操盘台、概览、买卖计划、诊股报告、证据链、观察单、AI 分析）；原误用 `id="trade-plan"` 的标题区改为 `stock-detail-hero`，买卖计划区块挂载 **`section-trade-plan`** 便于锚点。
- **全站页脚**：`base.html` 增加简短免责声明与数据来源说明；样式见 `static/css/common.css`（`.qc-ux-*`、`.qc-site-footer` 等，与现有 CSS 变量一致）。

## 2026-05-11（以用户为中心的界面优化 · 第二批）

- **页面路由与提示对齐**：`pages.py` 为 `/market-panorama`、`/market-panorama/<market>`、`/signal-observations` 传入 `ux_env_hints`，与操盘台、自选页一致展示环境类非阻断横幅。
- **今日操盘台**：新增「卡片显隐 + 自选条数」布局条；`localStorage` 键 `qc_wb_layout_v1` 持久化四张 cockpit 卡片开关与 `watchlist_limit`（6/12/18/24/36）；`GET /api/v1/daily-workbench` 请求附带 `watchlist_limit`；各 cockpit `section` 增加 `data-wb-card` 供显隐控制。
- **市场全景**：模板顶部增加与第一批同构的环境横幅 + 两步引导（操盘台 / 自选与观察单），强化「先看环境再翻列表」路径。
- **模拟观察单**：同构环境横幅与两步引导；`trigger_status` 展示对齐后端（含 `watching` →「跟踪中」及未知状态的简短文案）；列表加载失败时顶部错误条 + **重试**，空列表附信号旗/操盘台/自选入口；卡片「买卖计划」锚点统一为 **`#section-trade-plan`**（与个股详情一致）。
- **每日推荐链接**：`RecommendationService` 返回的 `links.trade_plan` 由 `#trade-plan` 改为 **`#section-trade-plan`**，与个股详情锚点一致。

## 2026-05-11（以用户为中心的界面优化 · 第三批）

- **`pages.py`**：`/signal-flag`、`/longhu-bang`、`/retail-assistant`、`/ai-analysis`、`/stock/<symbol>` 传入 `ux_env_hints`，与前几批页面一致。
- **信号旗**：顶部环境横幅 + 两步引导（观察单 / 操盘台与市场全景）；股票池 `GET` 失败时 **`#sfGlobalError`** 与表格区 **重试**；空池文案指向消息中心与再扫流程。
- **龙虎榜**：同构横幅与引导；**`#lhbGlobalError`** + 列表区重试；无数据空态附操盘台、消息中心入口。
- **散户 AI 助手**：横幅与引导（信号旗→观察单、集成中枢）；**`#raGlobalError`**；助手模块与权限摘要接口失败时 **重试** + 集成链接。
- **AI 诊股**：横幅与两步引导；**`#aiGlobalError`**；`analyze` 非 2xx、JSON 解析异常或 `fetch` 异常时展示可读错误并支持 **重试**。
- **个股详情**：在研究链路条下方增加环境横幅（不重复三步大卡片，避免挤压行情区）。

## 2026-05-11（以用户为中心的界面优化 · 第四批）

- **`pages.py`**：为 `/ai-chat`、`/yanbao-hub`、`/message-center` 传入 `ux_env_hints`，统一展示环境类非阻断提示。
- **消息中心**：顶部环境横幅 + 两步引导（信号旗/研报、集成中枢）；新增 **`#mcGlobalError`**；消息流、Worker 状态、任务反查失败时展示可读错误与 **重试**。
- **研报中心**：顶部环境横幅 + 两步引导（操盘台/全景、消息中心）；新增 **`#ybGlobalError`**；分类列表加载失败时错误条 + **重试**；空态提示同步与定时任务路径。
- **AI Chat**：顶部环境横幅 + 两步引导；新增 **`#aichatGlobalError`**；发送失败/历史加载失败时给出可读错误并引导到集成中枢自检。

## 2026-05-11（以用户为中心的界面优化 · 第五批）

- **`pages.py`**：为 `/capabilities`、`/integration-hub`、`/backtest`、`/tdx-blocks`、`/profile` 传入 `ux_env_hints`，让“配置/能力/回测/离线数据/个人中心”页面也能展示同构环境提示。
- **能力总览**：模板顶部增加环境横幅 + 两步引导（操盘台/自选起步；集成中枢排查能力缺失）。
- **集成中枢**：模板顶部增加同构横幅 + 两步引导（先排查为何不可用；再回业务页面验证恢复）。
- **策略回测**：模板顶部增加横幅 + 两步引导（先跑最小样例；失败去集成中枢/消息中心）。
- **通达信板块**：模板顶部增加横幅 + 两步引导（确认 `TDX_ROOT_PATH` 与入库路径；板块发现后回操盘台/自选沉淀）。
- **个人中心**：模板顶部增加横幅 + 两步引导（画像与权益影响推荐；异常去集成中枢/消息中心自检）。

## 2026-05-11（以用户为中心的界面优化 · 第六批）

- **`pages.py`**：为 `/global-radar`、`/ai-committee`、`/observability`、`/long-term-select`、`/stock-selector` 传入 `ux_env_hints`，补齐“全局发现 / 决策辩论 / 排障观测 / 选股”类页面的一致环境提示。
- **全球雷达**：模板顶部增加环境横幅 + 两步引导（回操盘台/观察单沉淀；异常去集成中枢）。
- **投委会**：模板顶部增加环境横幅 + 两步引导（观点落到买卖计划与观察单；异常去集成中枢/消息中心）。
- **观测台**：模板顶部增加环境横幅 + 两步引导（从消息中心获取 Trace/Task ID；异常回集成中枢排查）。
- **选股中心/中长线选股**：模板顶部增加环境横幅 + 两步引导（先跑最小样例与白盒理解；再用回测/观察单验证；异常去集成/消息中心）。

## 2026-05-11（页面链路打通与真实数据修复）

- **观测台接口对齐**：补齐 `GET /api/v1/system/health`（别名）与 `GET /api/v1/system/trace/<trace_id>`，使 `observability.html` 的健康检查与 Trace 查询指向真实后端实现（不再 404）。
- **Trace 查询落地**：`TraceQueryService` 改为优先读取 `instance/app.log`（不存在则回退 `logs/app.log`），并解析 `[SQL_TRACE]` 结构化行；用于页面化排障与任务链路回溯。
- **全球雷达去“假数据”**：`global_radar.html` 的“全球联动快手/舆情过滤/冲击波”从随机/硬编码演示改为依赖真实接口：联动读取 `/api/v1/global/quote`、舆情读取 `/api/v1/markets/CN/headlines`、冲击波读取 `/api/v1/watchlist/quotes`（仍为启发式估算，但输入为真实行情/快讯/自选标签）。

- **观测台依赖状态真实化**：`observability.html` 的「外部依赖与熔断」区块改为读取 `GET /api/v1/integration/stack-status` 的真实集成栈摘要并动态渲染卡片（失败可重试并跳转集成中枢）。
- **AI Chat / 投委会错误可诊断**：`ai_chat.html` 在发送失败时展示后端返回的 `error.message/message`；`ai_investment_committee.html` 对非 2xx 与异常返回结构给出可读错误并提供集成中枢/消息中心跳转。

- **任务闭环落消息中心**：为回测、选股、选股报告与投委会辩论在同步执行场景下写入 `task_message_store`（`/api/v1/system/task-messages` 可见），便于从页面直接跳转到消息中心与观测台排障。
- **Trace ID 闭环**：同步任务写入 `meta.trace_id`（形如 `trace-xxxxxxxxxxxx`）；消息中心展示 Trace 并提供“打开观测台”按钮（`/observability?trace=...` 自动回填并触发查询）。

## 2026-05-11（模拟观察单 `/signal-observations` 链路修复）

- **根因**：`create_api_blueprint`（`app/presentation/api/routes.py`）在补救创建 `SignalObservationService` 时只赋给了局部变量，未写回 `api_bundle.services.signal_observation_service`，`create_api_v1_context` 仍为 `None`，`ensure_service` 抛 `ValidationError` → 前端 `GET /api/v1/signal-observations*` 表现为 **400** 与「加载失败」。
- **修复**：补救逻辑成功后执行 `s.signal_observation_service = ...`；去掉「必须已有 `market_service`」才补救的限制（服务内部对行情缺失已降级）。
- **MySQL 持久化**：`bootstrap_components/services.py` 创建 `SignalObservationService` 时传入 `session_factory`，与仓库懒加载路径一致，启用库表时走 DB。
- **杂项**：`app/presentation/api/common.py` 移除 `ensure_service` 中重复的 `return`。

## 2026-05-11（今日操盘台聚合增强与卡片可定制）

- **`DailyWorkbenchService`**：单次 `GET /api/v1/daily-workbench` 聚合宏观指数、可解释决策（分数+立场+行动句+依据列表）、开放观察单、信号旗当日池摘要、任务消息摘要、集成栈异常摘要、`RecommendationService.daily_top`（top_n=1）、`ReviewTrackingService` 日/周复盘条、快讯列表、首只自选买卖计划摘要、涨停/龙虎；`limit_up_stats` 与观察单卡片对齐前端。
- **`routes_v1_daily_workbench.py`**：每请求组装完整依赖（含 `news_provider`、`task_message_store`、`integration_stack_service`、`recommendation`、`review`、`trade_plan`、观察单与信号旗）；懒初始化 `signal_flag_service`（与信号旗路由等价），避免注册顺序导致池为空。
- **`ReviewTrackingService` / `routes_v1_reviews.py`**：`daily_review` / `weekly_review` / `_rows` 支持 `user_id`，与观察单按用户隔离一致。
- **`daily_workbench.html`**：新增任务与消息、信号旗、复盘、推荐、快讯、买卖计划、集成健康等卡片；布局条支持「顶部决策区」开关、全部卡片显隐、`localStorage` 键 **`qc_wb_layout_v2`**（含 `card_order` 与 `preset`：默认/交易优先/研究优先）；宏观行优先渲染后端 `macro_indices`，否则回退上证 quote；市场切换按钮作用域收窄至 `#wbHeroShell`。

## 2026-05-14（启动与 API 健壮性修复）

- **Flask `test_client` / Werkzeug**：部分环境 Werkzeug 3.x 无 `__version__` 属性导致 `Client` 构造失败；在 `create_app()` 入口通过 `importlib.metadata` 补全 `werkzeug.__version__`。
- **信号旗**：`GET /signal-flag/pool` 后误并入的不可达代码已拆出为 **`POST /signal-flag/scan`**（与 `signal_flag.html` 的 `runScan` 一致）；扫描与历史回填路径对 **`task_dispatcher` / `task_message_store` 为空** 做了防护。
- **模拟观察单 API**：合并重复的 `_optional_float` 为 **`_optional_float_param`**（空值返回 `None`，非法数字走 `parse_float_param`）。
- **蓝图注册**：`routes_v1_arch` 依赖缺失的 `app.domain.models` 时原会导致 **`create_app` 整站失败**；`bootstrap_components/presentation.py` 对 `api_new_arch_bp` **try/except** 跳过并记录 warning；去除重复的 `create_auth_blueprint` import。

## 2026-05-15（Dashboard/全站样式错乱）

- **根因**：`base.html` 通过 `media="print" onload="this.media='all'"` 异步加载 Bootstrap（jsdelivr）与 Google Fonts；CDN 慢或不可达时 **Bootstrap 与 common.css 布局未生效**，页面呈无样式「乱版」。
- **修复**：将 Bootstrap 4.5.2 落盘至 `static/css/vendor/bootstrap-4.5.2.min.css` 并由 `base.html` **同步**引用；去掉 print/onload 懒加载；`common.css` 增加系统中文字体回退；`login.html` / `register.html` 同步字体加载方式。

## 2026-05-15（从 E:\\project\\myrepo\\quant-atlas 恢复启动与登录关键文件）

- **背景**：当前分支 `login.html`、`mysql_repositories.py`、`bootstrap.py` 被简化/空桩化，导致全站 500 或 admin 无法登录。
- **恢复**：自可运行旧版复制 `app/bootstrap.py`（完整工厂：i18n、安全头、错误处理、后台任务、warm_runtime_extensions）、`app/infrastructure/repositories/mysql_repositories.py`（含 `MySQLRepositoryBase` 与种子用户）、`app/presentation/web/templates/login.html`（独立登录页 + i18n）；`base.py` 改回从 `mysql_repositories` 导入 `MySQLRepositoryBase`；`presentation.register_blueprints` 增加可选 `services` 参数以兼容旧 bootstrap 签名；`create_app` 保留 `werkzeug.__version__` 补丁。
- **验证**：`GET /login` 200；`admin`/`admin123` POST 302 → `/dashboard`。

## 2026-05-15（admin/admin123 无法登录）

- **根因**：`app/infrastructure/repositories/mysql_repositories.py` 曾被替换为 **空桩**（`get_by_username` 恒返回 `None`），`AuthService.authenticate` 永远失败；`MySQLRepositoryBase` 亦未正确定义。
- **修复**：`mysql_repositories.py` 改为导出 `mysql_user_repository` / `mysql_watchlist_repository` / `mysql_stockgroup_repository` 的真实实现；`base.py` 内联 `MySQLRepositoryBase`；`bootstrap.py` 通过 `deps.create_*_repository` 按 `AppSettings` 选择 SQLite/MySQL，MySQL 空库时 `auth_seed.ensure_demo_users` 种子账号（含 admin/admin123）。

## 2026-05-15（全站 500：登录页模板损坏）

- **根因**：`app/presentation/web/templates/login.html` 被误写为单行非法 Jinja（`{% extends \"base.html\" %}` + `` `n ``），`GET /login` 触发 `TemplateSyntaxError` → **500**；未登录访问任意 `@login_required` 页面会重定向到 `/login`，表现为「所有页面都 500」。
- **修复**：从 `scripts/templates/login.html` 恢复完整登录页，并保留「记住我」、微信扫码（`wechat_login_available`）、注册链接；`app/bootstrap.py` 在 `create_app()` 入口补全 `werkzeug.__version__`（与 2026-05-14 说明一致，避免部分环境测试客户端失败）。

## 2026-05-15（static CSS/JS 加载失败 / MIME 错乱）

- **根因**：缺失的 `/static/*` 资源触发全局 `@app.errorhandler(404)`，API 层返回 **JSON**、Web 层返回 **HTML 错误页**，浏览器将样式表/脚本按 `text/css`/`application/javascript` 解析时报 MIME 类型错误；另缺 `favicon.ico`、`js/vendor/marked.min.js`；`asset_versioning` 用相对路径 `Path("static")` 在非项目根 cwd 下哈希失败。
- **修复**：`app/presentation/http_static.py` + API/Web 错误处理器对 `/static/` 走 `HTTPException.get_response()`；`asset_versioning` 改为 `BASE_DIR/static` 或 `current_app.static_folder`；从旧版复制 `favicon.ico`/`favicon.png`，落盘 `marked.min.js`；`base.html` 去掉 Google Fonts 的 print/onload 双标签。

## 2026-05-15（Pytdx 全量接口封装）

- **`app/infrastructure/pytdx/`**：按 [Pytdx 文档](https://pytdx-docs.readthedocs.io/zh-cn/latest/) 封装 `hq` / `exhq` / `reader` / `finance` / `trade` / `pool`；`PytdxFacade` + 方法白名单 + JSON 序列化。
- **`TdxConnectionManager`**：兼容别名指向 `TdxHqConnection`（原 `tdx_manager.py` 保留导入路径）。
- **API**：`GET /api/v1/pytdx/catalog|status`；`POST /api/v1/pytdx/invoke`、`/pytdx/<module>/invoke`；`POST /api/v1/pytdx/hq/quotes`。
- **`PytdxApiService`**：应用层统一 `invoke` / `hq_quotes` / `market_snapshot`。
- **`PytdxMarketDataService`**：业务便捷方法 `get_quotes` / `get_daily_bars` / `get_finance_info` / `read_local_daily`。
- **API 便捷**：`POST /api/v1/pytdx/market/snapshot`；`GET /api/v1/pytdx/market/daily-bars/<symbol>`；`GET /api/v1/pytdx/market/finance/<symbol>`。
- **测试**：`tests/infrastructure/pytdx/` 含目录白名单 + 联网冒烟（4 passed）。

## 2026-05-15（开盘啦 / 选股通 / 板块增强字段）

- **`cn_kpl_sectors.py`**：开盘啦概念(ZSType=7)/地区(5)/行业(4)榜单与成分股（`apphq.longhuvip.com`）。
- **`cn_xgt_sectors.py`**：选股通概念 via `flash-api.xuangubao.cn`（rank + plate_set）。
- **`sector_board_metrics.py`**：涨股比、龙头汇总工具。
- **`HotSectorService`**：东财 clist 扩展 f104/f105/f128/f136；合并 kpl/xgt；`provider` 分流成分股。
- **`TdxBlockStatsService`** + `GET /api/v1/tdx/blocks/summaries`：通达信板块涨幅/涨股比/龙头（成分股行情汇总）。
- **页面**：`hot_sectors.html` 增列涨股比/龙头；`/tdx-blocks` 恢复通达信页并展示汇总列。

## 2026-05-15（同花顺概念/行业板块 + 成分股）

- **`app/infrastructure/providers/cn_ths_sectors.py`**：抓取同花顺概念/行业涨幅榜（`q.10jqka.com.cn`）及成分股；AkShare `stock_board_concept_cons_ths` 兜底。
- **`HotSectorService`**：合并东财与同花顺榜单；成分股按 `BK*`（东财）/ 数字代码（同花顺）分流。
- **入库/页面**：筛选支持 `ths` / `em`；入库时按板块 `kind`+`name` 拉取同花顺成分股；MySQL 查询 `source LIKE '同花顺%'`。

## 2026-05-15（热点板块 MySQL 入库）

- **表**：`em_hot_sector_snapshots`（批次）、`em_hot_sectors`（榜单行）、`em_hot_sector_members`（Top 板块成分股）；ORM 见 `market.py`；DDL：`migrations/20260518_em_hot_sectors.sql`。
- **服务**：`HotSectorStorageService.ingest_snapshot` 拉东财写入板块 + Top25 成分股（`ingest_members=true` 默认）；默认保留 30 天（`HOT_SECTOR_SNAPSHOT_RETENTION_DAYS`）。
- **API**：`POST /api/v1/hot-sectors/ingest`；`GET /hot-sectors?snapshot_at=&source=auto|mysql|live`；`GET /hot-sectors/snapshots`。
- **页面**：热点板块页增加「入库 MySQL」、数据源与历史快照选择。

## 2026-05-15（热点板块页替换通达信板块导航）

- **需求**：参考 [如何用 Python 监控热点板块](https://mp.weixin.qq.com/s/Dj3PtSGccRYbTMlUgq_apQ)，以涨幅榜监控概念/行业热点，替换原「通达信板块」入口。
- **实现**：`HotSectorService` 拉取东财概念/行业 clist；`routes_v1_hot_sectors` 提供 `GET /api/v1/hot-sectors`、`/hot-sectors/<code>/members`（兼容 `/api/v1/data/hot-sectors`）；`hot_sectors.html` 双栏榜单+成分股（对齐 `tdx_blocks` 布局）；`/tdx-blocks` 302 → `/hot-sectors`；导航移至「市场」菜单。

## 2026-05-23（repositories 目录整理 + TimescaleDB 支持）

- **目录结构**：`common/`（factory、deps、register、facades、bases）、`mysql/`（`mysql_*` 与 auth 仓储）、`sqlite/`（`sqlite_*`）、`postgres/`（TimescaleDB 时序仓储）；根目录保留兼容 shim 重导出。
- **TimescaleDB**：`postgres_settings` / `postgres_client` / `postgres_connection_adapter`；`postgres/postgres_timescale_bar_repository.py`（`market_bars` hypertable）；`deps.create_timescale_bar_repository` / `create_postgres_connection_port`。
- **配置**：`AppSettings.postgres`、`use_timescaledb`、`timescaledb_uri`；`.env` / `.env.example` 增加 `TIMESCALEDB_*` 与 `USE_TIMESCALEDB`。
- **文档**：`docs/refactor/repositories-layout.md`、`docs/DATABASE_GUIDE.md`、`docs/refactor/layer-boundaries.md`、`docs/refactor/structural-debt-roadmap.md`（阶段 10）、`docs/QUANT_ATLAS_GUIDE.md`、`docs/PRODUCTION_OPERATIONS_MANUAL.md`、`app/README.md`、`docs/architecture_bootstrap.md`。

## 2026-05-23（阶段 9d：Tasks 禁止 adapters/tracing 直连，阶段 9 收尾）

- **`bootstrap_components/providers.py`**：新增 `create_ollama_prompt_adapter()`。
- **`tasks/task_wiring.py`**：扩展 `generate_ollama_text()`、`init_opentelemetry()`、`get_current_trace_id()`。
- **Tasks 改动**：`moments_agent_reply_tasks`（Ollama 生成）、`tracing_tasks`（OpenTelemetry 初始化/上下文）。
- **门禁**：`tests/test_task_layer_boundaries.py` 禁止 tasks import `infrastructure.adapters` / `infrastructure.tracing`（`task_wiring.py` 豁免）。

## 2026-05-23（阶段 9c：Tasks 禁止 database/messaging/rdagent/非 deps repositories 直连）

- **`infrastructure/repositories/deps.py`**：新增 `create_sqlalchemy_session_factory`、`create_factor_repository`、`create_execution_feedback_repository`、`create_slippage_analysis_service`。
- **`tasks/task_wiring.py`**：扩展 `get_stock_cache`、`create_tdx_gpcw_task_repository`、`ensure_tdx_gpcw_audit_table`、RD-Agent 编排函数。
- **Tasks 改动**：`moments_tasks`、`investment_manager_tasks`、`moments_agent_reply_tasks`、`market_history_tasks`、`tdx_gpcw_tasks`、`rdagent_tasks`、`execution_feedback_tasks`、`factor_lifecycle_tasks`。
- **`celery_app.py`**：`_push_safe` 改经 `task_wiring.get_task_message_store()`。
- **门禁**：`tests/test_task_layer_boundaries.py` 扩展 database / messaging / rdagent / 非 deps repositories 禁止项。

## 2026-05-23（阶段 9b：Tasks 禁止 infrastructure.providers 直连）

- **`bootstrap_components/providers.py`**：新增 `create_ta_indicator_provider()`、`create_cn_tdx_gpcw_provider()`。
- **`tasks/task_wiring.py`**：扩展 `get_market_data_provider()`、`get_news_provider()`、`create_ta_indicator_provider()`、`create_stock_application_service()`、`create_cn_tdx_gpcw_provider()`；market history fetch 函数 re-export。
- **Tasks 改动**：`scanner_tasks`、`signal_flag_tasks`（含 message store / stock cache）、`news_backfill_tasks`、`tdx_gpcw_tasks`、`market_history_tasks` 改经 task_wiring。
- **门禁**：`tests/test_task_layer_boundaries.py` 禁止 tasks import `infrastructure.providers`。

## 2026-05-23（阶段 9a：Celery Tasks 共享绑定与试点迁移）

- **`bootstrap_components/infrastructure_binding.py`**：抽取 Flask/Celery 共用的 helper 绑定（幂等）；`services.py` 改调用此模块。
- **`tasks/task_wiring.py`**：`ensure_task_bindings()`、`create_basic_market_data_service()`、`get_task_message_store()`。
- **Tasks 改动**：`market_tasks`（longhu 经 helper）、`data_backfill_tasks`（domain `qlib_symbol_map` + task_wiring）、`qlib_data_update`（domain `SymbolNormalizer`）、`factor_ic_alerts`（task_wiring 消息 store）。
- **门禁**：`tests/test_task_layer_boundaries.py` 禁止 tasks import `infrastructure.mappers.symbol_normalizer`、`qlib.symbol_map`、`adapters.market_ingestion.longhu_adapter`。

## 2026-05-19（阶段 8e：系统/组合/策略/数据/AI 模块 Port 化）

- **Domain Port**：`AiAnalysisPort`、`DataLineagePort`。
- **Application helpers**：`task_pipeline_access`、`memory_access`、`strategy_access`、`portfolio_access`、`data_infrastructure_access`、`ai_adapter_access`、`research_access`。
- **Infrastructure adapters**：`ai_analysis_port_adapter`（Ollama 默认）、`data_lineage_port_adapter`。
- **Application 改动**：`task_pipeline_service`（合并重复类 + helper）、`memory_optimization_service`、`strategy_optimization_service`、`portfolio_service`、`data_infrastructure_service`、`ai_analysis_service`、`ai_research_service`。
- **门禁**：禁止 application import `task_pipeline`、`memory`、`portfolio`、`strategy`、`data_quality`、`adapters`。

## 2026-05-19（阶段 8d：Agent / Events / Messaging lazy fallback Port 化）

- **Application helpers**：`events_access`、`task_message_access`、`agent_access`；bootstrap 绑定 event store、integration events、task message store、swarm orchestrator、expert skill、experiment repo、swarm runtime 工厂。
- **Application 改动**：`event_publisher`、`agent_telemetry_service`、`factor_performance_engine`、`immune_service`、`forward_testing_service`、`strategy_scanner` 改经 helper；`create_default_swarm_runtime` 修正为 `SwarmStore` + `SwarmRuntime` 正确构造。
- **门禁**：禁止 application import `infrastructure.agent`、`infrastructure.events`、`infrastructure.messaging`。

## 2026-05-19（阶段 8c：执行驱动 / DI / TDX 财务 / Tracing Port 化）

- **Domain**：`domain/execution/driver_protocol.py`（`TradeRequest`、`ExecutionGateway` 等）；`TdxFinancePort` + `TdxFinanceSnapshot`。
- **Infrastructure**：`execution/driver/protocol.py` 改 re-export domain；`tdx_finance_port_adapter`。
- **Application helpers**：`service_resolver_access`、`tdx_finance_access`、`tracing_access`；bootstrap 绑定 `resolve_optional_service`、`TdxFinancePortAdapter`、`create_span`。
- **Application 改动**：`bot_engine`、`trading_bot_service` 改从 domain 导入执行类型；`tdx_base_data_service` 经 `tdx_finance_access`；9 处 `di.container` lazy resolve 改经 `service_resolver_access`。
- **门禁**：禁止 application import `infrastructure.di.container`、`external.tdx_finance`、`execution`、`tracing`。

## 2026-05-19（阶段 8b：Qlib / RD-Agent / 交易风控 Port 化）

- **Domain / Port**：`qlib_symbol_map`；`QlibBinDumperPort`、`RDAgent*Port`、`PreTradeValidationPort`。
- **Infrastructure adapters**：`qlib_bin_dumper_port_adapter`、`rdagent_port_adapters`、`pre_trade_validation_port_adapter`。
- **Application helpers**：`qlib_access`、`rdagent_access`、`trading_risk_access`；bootstrap 在 `services.py` 绑定。
- **Application 改动**：`qlib_pipeline_service`、`alpha_factory_orchestrator`、`factor_catalog_service`、`research_pipeline_snapshot`、`risk_service`、`signal_dispatcher` 改经 helper/Port；**恢复** `RDAgentRunService` 完整契约（`get_artifacts`、`execution_mode`、`get_run` 返回 `None`）。
- **Bootstrap**：新增 `wire_rdagent_run_service`；移除 `rdagent_run_service` 误映射到 `swarm_service`；`wire_trading_execution` 经 `create_pre_trade_validator()`；补全 `services.py` 缺失的 `bind_quote_cache_port` import（修复 `create_app` NameError）。
- **门禁**：`tests/test_layer_boundaries.py` 禁止 application import `infrastructure.qlib`、`infrastructure.rdagent`、`pre_trade_validator`、`risk_gateway`。

## 2026-05-15（/static/css/common.css 404）

- **根因**：`Flask(__name__)` 在 `app/bootstrap.py` 中 `import_name=app.bootstrap`，`root_path` 默认为 `app/`；若 `static_folder` 为相对路径 `static`，实际目录为 **`app/static/`**（不存在），`/static/css/common.css` 恒 404 且 Web 错误页返回 `text/html`。
- **修复**：`create_app` 显式 `root_path=BASE_DIR`、`static_folder="static"`；`app/presentation/static_files.configure_static_files` 用绝对 `STATIC_ROOT` 覆盖 `static` 视图，确保从仓库根 `static/` 发文件。
