# 页面数据加载失败修复 — 重构计划

> **优先级：** P0 — 用户可见的 401/404/500 与空白面板  
> **工作者技能：** `executing-plans` / `subagent-driven-development` + `verification-before-completion`  
> **关联：** `route_contract.py`、CSO 审计 `scripts/audit_api_routes.py`、架构计划 `2026-06-28-architecture-refactor-plan.md`

**目标：** 恢复全站页面 AJAX 数据加载；建立「前端契约路径 ↔ Flask url_map」防回归机制；与大规模架构重构解耦，先止血再演进。

**非目标（本计划不做）：** 删除 `app/services/`、拆分 God Class、SPA 全量迁移。

---

## 根因摘要

| 类别 | 现象 | 根因 |
|------|------|------|
| **路由漂移** | `/api/v1/jarvis/proactive` 等 404 | Phase-2 将 context 路由挂到错误子蓝图前缀（`/api/v1/ai-agent/...`） |
| **契约不一致** | `index.html` NL 查询失败 | 前端 `/api/v1/nl-parser/query`，后端 `/api/v1/nl/query` |
| **启动静默失败** | 部分环境仍无 `/api/v1/*` | `presentation.py` 蓝图注册异常仅 WARNING，进程继续 |
| **认证未挂载** | 页面 401 或 `/login` 404 | `service_wiring` 未预加载 factory 侧效 → `auth_service` 为 None |
| **模板错误** | `/integration-hub` 500 | Jinja `spa_switcher` 块未闭合（部分环境） |
| **部署滞后** | 代码已修仍 404 | 未完全重启 / Docker 未 rebuild / worktree 旧路径 |

---

## 阶段 A — 立即止血（1–2 天）

**成功标准：** 首页、集成中枢、可观测性、Jarvis 面板、回测入口在登录后 AJAX 返回 200/401（非 404）。

### A.1 部署与启动验证

- [ ] 停止旧进程；`python run.py` 或 `docker compose up --build`
- [ ] 启动日志必须出现：`API v1 canonical route contract OK`
- [ ] 若出现 `API v1 contract missing` → 不要继续测页面，先修 `routes.py` / `route_contract.py`

```bash
python -c "from app.bootstrap import create_app; a=create_app(); print(len(a.url_map._rules))"
python scripts/audit_api_routes.py
```

### A.2 已落地修复 — 确认合并（勿重复造轮子）

| 文件 | 要点 |
|------|------|
| `app/presentation/api/routes.py` | 所有 `@register_routes` 统一挂主 `/api/v1` 蓝图 |
| `app/presentation/api/route_contract.py` | 关键路径兜底 + 7 条旧前缀别名 |
| `app/bootstrap_components/presentation.py` | 注册后 `finalize_v1_route_contract` |
| `app/bootstrap_components/service_wiring.py` | `_preload_wiring_modules()` 恢复 auth factory |
| `app/presentation/api/error_handlers.py` | `auth.login` 不可用时回退 `/login?next=` |

### A.3 前后端路径对齐（高优先级缺口）

| 前端路径 | 后端现状 | 修复策略（二选一，推荐别名） |
|----------|----------|------------------------------|
| `/api/v1/nl-parser/query` | `/api/v1/nl/query` | `routes_v1_nl.py` 增加 `nl-parser` 子蓝图或 `LEGACY_PATH_ALIASES` |
| `/api/v1/phase18/zen/search` | `/api/v1/zen-mode/zen/search` | 别名或模板改路径 |
| `/api/v1/phase18/resonance/field` | 待查 `routes_v1_*` | 同上 |

**原则：** 能加别名就不改 80+ 模板；仅当后端路径更 canonical 时改前端。

### A.4 运行全量模板审计

```bash
python scripts/audit_api_routes.py
```

- [ ] 将 `MISSING` 列表写入本计划附录或 issue
- [ ] 按页面流量排序：P0 页面先修（`index`、`integration_hub`、`observability`、`capabilities`）

### A.5 关键页面手工冒烟

| 页面 | 关键 API |
|------|----------|
| `/` | `nl-parser/query` 或 `nl/query` |
| `/integration-hub` | `integration/stack-status`, `system/task-messages` |
| `/observability` | `system/health`, `data/timeseries-health` |
| 全局 Jarvis 面板 | `jarvis/proactive` |
| `/backtest` | `backtest` |

---

## 阶段 B — 契约硬化（2–3 天）

**成功标准：** CI 在蓝图缺失时失败；`tests/api/test_api_contract.py` 覆盖 Top-30 模板路径。

### B.1 扩展 `CRITICAL_ROUTE_MODULES`

在 `route_contract.py` 增加高频路径（建议）：

- `/api/v1/integration/stack-status`
- `/api/v1/system/health`
- `/api/v1/nl/query` + `/api/v1/nl-parser/query`（别名）
- `/api/v1/realtime/status`
- `/api/v1/system/alerts/dispatch`

### B.2 CI Boot Gate

修改 `.github/workflows/ci.yml` boot 步骤：

```python
from app.presentation.api.route_contract import missing_canonical_paths, CRITICAL_ROUTE_MODULES
from app.bootstrap import create_app
app = create_app()
missing = missing_canonical_paths(app.url_map)
assert not missing, missing
```

### B.3 自动化契约测试

- [ ] 扩展 `scripts/audit_api_routes.py`：退出码非 0 当 `bad > 0`
- [ ] 新增 `tests/api/test_template_fetch_contract.py`：解析 templates 与 url_map 对比
- [ ] 复用 `tests/smoke/_check_endpoints.py` 列表，改为 assert 而非 print

### B.4 启动 Fail-Fast

`presentation.py`：

- `FLASK_ENV != development` 且 `finalize_v1_route_contract` 返回 missing → `raise RuntimeError`
- API 蓝图注册失败 → ERROR + 非 dev 环境 abort

---

## 阶段 C — 认证与安全（与数据加载并行，1 天）

**成功标准：** 匿名访问敏感任务 API 返回 401；公开 manifest 行为明确。

### C.1 任务消息端点

- [ ] `celery_routes.py`：`task-messages`、`active-jobs` 加 `@login_required`
- [ ] 更新 `tests/api/test_api_contract.py` 期望 401

### C.2 公开端点白名单

- [ ] `compliance/manifest`：文档化是否 intentionally public
- [ ] `error_handlers` / `before_request` 与公开列表一致

### C.3 密钥与启动

- [ ] `.env.example` 说明 `TUSHARE_TOKEN` 勿用样本值（避免 `UnsafeSecretError` 阻断启动）

---

## 阶段 D — 前端韧性（可选，3–5 天）

**成功标准：** API 404 时页面显示可读错误，而非无限 loading。

### D.1 统一 `api_client.js`

- [x] 封装 `fetchJson(path)`：404 → toast「接口未注册」+ 上报
- [x] P0 模板逐步改用 `QCApi` 而非裸 `fetch`（`integration_hub`、`observability`、`jarvis_proactive_panel`、`index`）

### D.2 React SPA 路径

- [x] `frontend/src/lib/api.ts` 404/401 专用错误文案
- [x] `scripts/audit_frontend_api_paths.py` 审计 SPA `/api/v1` 引用
- [ ] `Marketplace.tsx` 等已拆分页面纳入契约测试（后续）

---

## 阶段 E — 架构大改

**前置：** 阶段 A–D 已完成（路由契约 + 前端审计 + CI 门）。

详细实施计划见 **[2026-06-24-phase-e-architecture-refactor.md](./2026-06-24-phase-e-architecture-refactor.md)**。

原则（不变）：

1. 路由契约稳定后再动 `app/services/` 等大删改
2. 任何路由模块搬迁后必须跑 `audit_api_routes.py` + `audit_frontend_api_paths.py`
3. 每条行为变更写入 `REFACTORING_LOG.md`

---

## 任务分解（执行顺序）

```
Week 1
├── [A] 部署验证 + audit 脚本出清单
├── [A] nl-parser / phase18 别名
├── [B] CRITICAL_ROUTE_MODULES 扩展
├── [B] CI boot assert
└── [C] task-messages 鉴权

Week 2
├── [B] test_template_fetch_contract
├── [A] 按 audit 清单逐项修剩余 MISSING
├── [D] api_client 错误处理（可选）
└── 文档：docs/API_ROUTE_CONTRACT.md（Top-50 路径表）
```

---

## 验证清单（完成定义）

- [ ] `python scripts/audit_api_routes.py` → Template missing **0**
- [ ] `pytest tests/api/test_api_contract.py tests/smoke -q` 通过
- [ ] CI boot 步骤 assert canonical paths
- [ ] 登录后 P0 五页无控制台 404
- [ ] `REFACTORING_LOG.md` 已记录本计划落地项

---

## 附录：关键文件索引

| 路径 | 职责 |
|------|------|
| `app/presentation/api/routes.py` | 路由自动发现与注册 |
| `app/presentation/api/route_contract.py` | 契约、兜底、别名 |
| `app/bootstrap_components/presentation.py` | 蓝图挂载 |
| `app/bootstrap_components/service_wiring.py` | DI + auth |
| `app/presentation/api/routes_v1_nl.py` | NL 解析 |
| `app/presentation/api/v1/task_ops/celery_routes.py` | 任务消息 |
| `scripts/audit_api_routes.py` | 模板 vs url_map 审计 |
| `tests/api/test_api_contract.py` | API 契约测试 |
