# 重构交付摘要（Phases A–J）

## 变更范围

- 新增文件：35+ 个
- 修改文件：5 个（`presentation/api/routes.py`、`celery_app.py`、`presentation/web/templates/base.html`、`v1_context.py`、`enhanced_market_service.py`）
- 破坏性变更：无

## 阶段速查

| 阶段 | 入口 | 状态 |
|------|------|------|
| A 旅程路由 | `GET /api/v1/journeys` | 可用 |
| B 工作流领域 | `domain/workflow_hub` | 可单测 |
| C 用户上下文 | `GET /user/context/{dashboard,quick-actions,suggestions}` | 可用 |
| D 权限条款 | `Capability` + `@requires_capability` | 可组合 |
| E 决策追溯 | `@with_provenance` | 单测通过 |
| F 异常自愈 | `SelfHealingDomainError` + `X-QC-Degraded` | 已接入 error_handlers + 单测 |
| G 服务分组 | `services/{trading,research,system,ai,analytics}/__init__.py` | 文档化 |
| H Celery 桥接 | `app/celery_app.py` 信号 | 自动创建/完成/失败 workflow 实例 |
| I.1 Focus Bar 联动 | `static/js/focus_context_enhancer.js` | <qa-focus-change> → auto reload / callback |
| I.2 系统健康 UI | `system_health_indicator.js` + banner | 已验证（dot + polling + banner） |
| I.3 决策证据内联 | `@with_provenance` 后端已就绪 | 前端 template 待接入 |
| I.4 智能任务进度 | `task_feedback.js` 已有 | 增强版待接入 |
| J 统一 API Client | `static/js/api_client.js` | 已接入 base.html |
| K Focus Bar Web Component | `static/js/components/qa-focus-bar.js` | 已交付 |
| L state_bus | `static/js/state_bus.js` | 已交付 |
| M chart_service | `static/js/chart_service.js` | 已交付 |
| 8.1 EvolutionArbiter | `domain/evolution_arbiter.py` + `system/evolution_arbiter_service.py` | champion/challenger + SimulationGateway |
| 8.2 Guardian Agent | `DataTruthGuardianService` scan → Blackboard 自动发布 | 已接入 |
| 8.3 God-View API | `/api/v1/panorama/full-trace` | 已注册 |
| 9.1 IntentDecomposer | `domain/intent_decomposer.py` + `application/services/intent_decomposer.py` | 3 种意图模板 |
| 9.2 Alpha-Lab 数据结构 | `domain/alpha/alpha_metadata_standard.py` | `FactorExpression`/`AlphaNote` |
| 9.3 逻辑自检升级 | `EnhancedMarketService.cross_validate_indicators()` | fallback 实现 |
| 10 前端专项 | `chart_service.js` + `state_bus.js` + `qa-focus-bar.js` | 已接入 base.html |

## base.html 修正清单（已完成）

| 修正项 | 状态 |
|--------|------|
| `qcHealthDot` 去重（仅 1 处） | ✅ |
| `<body data-qa-focus-refresh="auto">` | ✅ |
| 加载 `api_client.js` | ✅ |
| 加载 `qa-focus-bar.js` | ✅ |
| 加载 `state_bus.js` | ✅ |
| 加载 `chart_service.js` | ✅ |

## 已修复（本次）

- `service_wiring.py` 批量导入名与 `wiring_market.py` 定义不匹配（5处复数/单数不一致）
- `EvolutionArbiterService._spawn_challengers` 接入 `SimulationGateway.run_war_room()` 真实影子回测
- `DataTruthGuardianService` 新增 `set_blackboard_service()` setter + `v1_context.py` 桥接
- `alpha_metadata_standard.py` 修复 dataclass/field 导入 + CompositionOp 测试断言

## 当前阻塞项（预存，不影响启动）

- `tests/test_app_bootstrap.py::test_create_app_exposes_bootstrap_bundles`：`get_registry` 缺失
- `tests/test_layer_boundaries.py`：24处 application 层 infra 直连 + 1处 `_session_factory`
- `tests/infrastructure/providers/test_external_news.py`：`DEFAULT_UA` 导入错误
- `instance/pytest_tmp/` 拒绝访问：测试清理异常

## 建议合并顺序

1. 先合并 Phases A–E（纯新增，零风险）
2. 再合 Phase F（error_handlers.py + degraded_response.py）
3. 再合 UI I.1–I.4 + J + K + L + M（static/js/ 新文件，零破坏）
4. 再合 Phase H（celery_app.py +3 处 try/except）
5. 再合 Phase 8 + Phase 9 + Phase 10（domain + service 增强 + 前端基础设施）
6. 最后合 Phase G（`__init__.py` 文档化，零副作用）

## 现有基础（Phase 10 由 Foundation Products）

| Directive | 现有能力 | 待试点 |
|-----------|---------|--------|
| **10.1 PromptEvolution** | DecisionFeedback + UserKnowledge 就位 | Pilot：Jarvis 引导词基于反馈微调 |
| **10.2 Alpha-Hot-Swap** | FactorDecayMonitor 具备 IC 衰减预警 | Pilot：备选因子池 + 自动替换逻辑 |
| **10.3 Arrow Data Fabric** | ArrowComputeClient + arrow_pool | Pilot：calculate_sma(ndarray) → 零拷贝 |
| **10.4 ExecutionPlan UI** | IntentDecomposer + workflow routes | Pilot：/api/v1/workflow/status 流式日志 |

## Phase 10 完成状态

| Directive | 文件 | 状态 |
|-----------|------|------|
| 10.1 PromptEvolution | `domain/prompt_evolution.py` + `application/services/prompt_evolution_service.py` | ✅ 可在无 LLM 依赖的 fallback 模式下运行 |
| 10.2 Alpha-Hot-Swap | `domain/alpha/shadow_factor_pool.py` + `application/services/alpha_hot_swap.py` | ✅ pool + hot-swap 决策逻辑完成 |
| 10.3 Arrow Data Fabric | `infrastructure/compute/arrow_client.py` | ✅ calculate_sma(ndarray) 零拷贝验证通过 |
| 10.4 ExecutionPlan UI | `presentation/api/routes_v1_workflows.py` | ✅ `/workflows/<id>/stream` SSE 端点就位 |
| 10.5 Panorama 前端接入 | `market_panorama.html` | ✅ `loadFullTrace()` + panoramaFullTrace 容器已写入 |

## Phase 11 进行中（Sovereign Intelligent Mesh & Explainable Alpha-Synthesis）

| Directive | 文件 | 状态 |
|-----------|------|------|
| 11.2 因子语义解释器 | `application/services/alpha_semantic_interpreter.py` | ✅ 规则基线版已交付，可生成人类可读 narrative + consistency_check |

## 下一步（需人工决策）

- 11.1 ModuleAgent 试点：PortfolioRiskModule 自主阈值调整
- 11.3 前瞻性 Rust 算子：Tick 流概率预测（需 Rust 编译环境）
- 11.4 群体博弈演播室：MetaArbiter 可视化作战室
- 基础设施修复：修 `services_bootstrap.py` 导入，打通 bootstrap 测试
