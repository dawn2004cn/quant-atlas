# 阶段 E — 架构大改实施计划

> **前置条件：** 阶段 A–D（页面数据加载止血 + 契约硬化 + 安全 + 前端韧性）已完成。  
> **关联文档：** [2026-06-28-architecture-refactor-plan.md](./2026-06-28-architecture-refactor-plan.md)、[2026-06-24-page-data-load-refactor.md](./2026-06-24-page-data-load-refactor.md)  
> **工作者技能：** `executing-plans` / `subagent-driven-development` + `verification-before-completion`

**目标：** 在路由契约已稳定的前提下，消除重复层、God Class 与目录漂移，恢复可维护的四层垂直结构，且不回归页面 AJAX 404/401。

**非目标：** SPA 全量替换 Jinja、一次性删除所有 shim、无测试覆盖的大范围重命名。

---

## 为什么现在可以做阶段 E

| 已完成（A–D） | 对架构大改的意义 |
|---------------|------------------|
| `route_contract.py` + `boot_gate.py` | 路由搬迁后有 CI 硬门 |
| `audit_api_routes.py` + `audit_frontend_api_paths.py` | 模板 + SPA 双轨契约审计 |
| `presentation.py` fail-fast | 生产环境蓝图缺失即中止 |
| `QCApi` + 公开端点白名单 | 前端与安全边界清晰 |

**铁律：** 每个架构 PR 合并前必须：

```bash
python scripts/boot_gate.py
python scripts/audit_api_routes.py
python scripts/audit_frontend_api_paths.py
pytest tests/api/test_*_contract.py tests/architecture/ -q
```

---

## 阶段总览

```mermaid
flowchart LR
  E0[ E0 基线与分支 ] --> E1[ E1 删除废弃兼容层 ]
  E1 --> E2[ E2 Domain / Port 净化 ]
  E2 --> E3[ E3 God Class 拆分 ]
  E3 --> E4[ E4 Bootstrap / DI 收敛 ]
  E4 --> E5[ E5 文档与长期治理 ]
```

| 子阶段 | 周期 | 成功标准 |
|--------|------|----------|
| **E0** 基线 | 0.5 天 | 分支 + 基线测试报告 + 路由审计 0 missing |
| **E1** 兼容层清理 | 2–3 天 | `app/services/`、`application/facades/` 删除；测试无回归 |
| **E2** Domain 净化 | 3–5 天 | `domain/ports/` 合并；domain 无 infrastructure 导入 |
| **E3** God Class 拆分 | 5–8 天 | 3 个 >1000 行路由文件已拆分；system 模块子目录职责清晰 |
| **E4** Bootstrap 收敛 | 3–5 天 | wiring 工厂 ≤ 目标数；模块自注册无幽灵服务 |
| **E5** 文档治理 | 1–2 天 | `docs/API_ROUTE_CONTRACT.md` Top-50；架构图与 REFACTORING_LOG 同步 |

---

## E0 — 基线与隔离（必须先做）

- [x] 确认 `main` 上 A–D 已合并：`boot_gate`、双 audit、契约 pytest 全绿
- [x] 创建分支 `architecture/phase-e-v1`
- [x] 记录基线：`artifacts/phase-e-baseline-*.txt`
- [x] 导出 CRITICAL 路径清单（19 paths → `phase-e-baseline-critical_paths.txt`）

**退出条件：** 基线 artifacts 提交到分支或 CI artifact，后续每任务对比无新增 missing。

---

## E1 — 删除废弃兼容层

> 详细步骤见 [2026-06-28-architecture-refactor-plan.md](./2026-06-28-architecture-refactor-plan.md) 任务 1–2。

### E1.1 删除 `app/services/`

- [x] `grep -r "from app.services" app/ tests/` → 0 引用（目录本不存在）
- [x] 无需删除（已迁移至 `app/modules/*/services/`）

### E1.2 删除 `app/application/facades/`（复数目录）

- [x] `MarketDataFacade` 合并至 `app/application/facade/market_data_facade.py`
- [x] `application/facades/` 保留 1 文件 shim `__init__.py`
- [x] 测试改导入 `application.facade`

### E1.3 清理 `app/facade/` 为 shim

- [x] `market_facade` / `ai_facade` / `backtest_facade` → re-export shim
- [x] `app/facade/dto/*.py` → re-export shim（`__init__.py` 已是 shim）

**验证：** 与 E0 相同四门；`compileall` + `check_module_cross_imports.py` 通过。

---

## E2 — Domain / Port 净化

### E2.1 端口定义单点化

- [x] `app/domain/ports/` 包为 canonical 入口；`ports.py` 修正为 re-export shim（非反向废弃）
- [x] `port_registry.py` 与 bootstrap 注入点已对齐（维持现状）
- [x] domain 顶层无 `from app.infrastructure` / `from app.presentation`（lazy shim 除外）

### E2.2 领域服务回迁

- [x] Redis 订单持久化 → `infrastructure/trading/order_persistence_redis.py`
- [x] Cache 失效 Publisher/Subscriber → `infrastructure/events/`
- [x] `domain/` 保留 `__getattr__` deprecation shim
- [ ] `entities.py` 继续瘦身（后续）

### E2.3 跨模块循环依赖

- [x] `StrategyRegimeMismatchEvent` 提升至 `core/event_bus.py`，消除 system→strategy 一条边（9→8）
- [x] `strategy_scanner.py` 去除 ai_agent 直 import（1→0），改为构造注入
- [x] `check_module_cross_imports.py` 基线更新：strategy→ai_agent 0、system→strategy 0
- [x] system→strategy 剩余 8 条已清零（`importlib` 延迟加载 + `tool_facade` shim）

**验证：** 架构测试 + domain trading 测试通过。

---

## E3 — God Class 与 Presentation 拆分

### E3.1 巨型路由文件（已部分完成，继续）

| 原文件 | 目标 | 状态 |
|--------|------|------|
| `routes_v1_data_infrastructure.py` | 470→149 行 + 3 子模块 | ✅ 已拆分 |
| `routes_v1_investment_managers.py` | 390→55 行 + 3 子模块 | ✅ 已拆分 |
| `routes_v1_collaboration.py` | 375→58 行 + 5 子模块 | ✅ 已拆分 |
| `stock_analysis.py` | 4 个子路由模块 | ✅ 已拆分（shim + `routes_*`） |
| `stock_basic.py` | 4 个子路由模块 | ✅ 已拆分 |
| `stock_fundamental.py` | 4 个子路由模块 | ✅ 已拆分 |
| `routes.py` 注册逻辑 | 保持自动发现，不增大 God 函数 | 持续 |

- [x] 每个新路由文件 ≤ 300 行；共享逻辑进 `presentation/api/helpers/`（架构测试：≤800 行）
- [ ] 新路径加入 `CRITICAL_ROUTE_MODULES`（若模板/SPA 使用）

### E3.2 `modules/system` 瘦身

- [x] `data_optimizer_access` 迁至 `modules/data/services/helpers/`（system 保留 shim）
- [x] `notification_service` 迁至 `services/system/`（根目录保留 shim）
- [ ] helpers 目录（~82 文件）分批下沉评估（wiring/access 对保留在 bootstrap 边界）
- [ ] 根目录散落服务（meta_arbiter、sequence_chain 等）后续归入 `services/system/` 或业务模块

### E3.3 重复 Fallback 消除

- [x] `integration_stack` / `ten_kings` / `watchlist_agent` 改用 `@service_fallback`
- [x] 新增 `@deps_service_fallback`；`global_market` / `recommendations` / `strategy_shadow` / `user_knowledge` 已覆盖
- [x] `manifest_10` / `evolution_arbiter` 改用 `@service_fallback`
- [x] `routes_v1_risk.py` 四端点 `@deps_service_fallback`
- [x] 统一 `Service unavailable` 错误码 → `ErrorCode` 枚举（`self_healing_execution` 除外；v1 fallback 保持 HTTP 200）
- [x] Marketplace SPA 路径纳入 `CRITICAL_ROUTE_MODULES`

---

## E4 — Bootstrap / DI 收敛

### E4.1 TypedServiceRegistry 唯一入口

- [x] `post_wire_hooks.py` 收敛 recommendation / optimization / strategy_sop 后置装配
- [x] `bootstrap_services.py` 改为 `create_services` re-export shim
- [x] 架构测试禁止 `from app.bootstrap_components.services import *`
- [ ] 模块 `wire()` 逐步吸收剩余 `wiring_*.py` 工厂（长期）
- [x] `manifest_service_10` / `perception_resonance_service` 实现 + factory 注册

### E4.2 可选服务分类

- [x] `OPTIONAL_SERVICE_ATTRS` 扩展并与 fallback 路由对齐
- [x] `/system/health` 返回 `deployment_status` + optional/required 缺口列表

### E4.3 任务与模块边界

- [x] `app/tasks/*` 仅组合 application service，不直接 import presentation（`test_phase_e_tasks_boundary`）
- [x] Celery 任务路径稳定（`task_dispatcher` + `tasks/registry` 契约测试）

---

## E5 — 文档与长期治理

- [x] 新建 `docs/API_ROUTE_CONTRACT.md`：Top 路径、公开/鉴权、别名表
- [x] 更新 `app/README.md` 四层图与模块列表
- [ ] `REFACTORING_LOG.md` 每个 E 子阶段一条
- [x] CI 增加（可选）：`audit_frontend_api_paths.py` 已在 integration job
- [x] Marketplace 等 SPA 页面路径纳入 `CRITICAL_ROUTE_MODULES`

---

## 风险与回滚

| 风险 | 缓解 |
|------|------|
| 路由搬迁导致 404 | 每 PR 跑双 audit + boot_gate；别名表 `LEGACY_PATH_ALIASES` |
| 删除 shim 破坏外部脚本 | shim 保留 1 个 release；DEPRECATION 日志 |
| 测试覆盖不足 | 先补契约测试再删目录；God 拆分伴随 presentation 测试 |
| 多人并行冲突 | 按 E1→E2→E3 顺序；同目录同时只允许一个活跃 PR |

**回滚策略：** 每个子阶段独立 commit；失败则 `git revert` 该 commit，不跨阶段 revert。

---

## 建议执行顺序（2–3 周）

```
Week 1
├── E0 基线 + E1.1 删除 app/services/
├── E1.2 facades 合并
└── 契约四门每日跑

Week 2
├── E2.1 ports 合并
├── E2.3 循环依赖第一批
└── E3.1 路由文件拆分（1 个 God 文件/天）

Week 3
├── E3.2 system 模块瘦身
├── E4.1 DI 收敛
└── E5 文档 + 全量回归
```

---

## 完成定义（阶段 E 整体）

- [x] `app/services/`、`application/facades/` 不存在（canonical：`app.application.facade`）
- [x] `domain/` 无 infrastructure 依赖（`test_layer_dependency_gate` enforced）
- [x] 无 >800 行的 presentation 路由文件（`test_phase_e_presentation_route_size`）
- [x] `boot_gate` + 双 audit + 契约 pytest CI 全绿（见 CI / 既有 E5 回归）
- [x] `REFACTORING_LOG.md` 含 E0–E5 记录
- [ ] 登录后 P0 五页无控制台 404（与 A 阶段标准一致；由 SPA UX / 演示数据线持续验收）

### 收尾补充（2026-08-13）

- [x] 任务注册对可选依赖稳健：`moments_tasks` matplotlib 懒加载；`scanner`/`signal_flag` 去掉顶层 `celery` 硬导入；`registry` 按模块 best-effort 注册
- [ ] `entities.py` 继续瘦身 / `modules/system` helpers 分批下沉 / wiring→`wire()`（长期，不阻塞阶段 E 关闭）

---

## 附录：关键文件

| 路径 | 阶段 E 职责 |
|------|-------------|
| `app/domain/ports.py` | 端口单点 |
| `app/bootstrap_components/module_wiring.py` | 模块发现 |
| `app/bootstrap_components/wiring_*.py` | 工厂注册 |
| `app/presentation/api/route_contract.py` | 搬迁后契约 |
| `scripts/boot_gate.py` | 启动门 |
| `tests/architecture/test_layer_dependency_gate.py` | 四层依赖 |
| `docs/superpowers/plans/2026-06-28-architecture-refactor-plan.md` | 任务级细步骤 |
