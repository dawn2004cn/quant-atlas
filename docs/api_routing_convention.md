# API 路由命名规范

> 阶段一（R5）产出 · 2026-06-15

## 文件命名

| 模式 | 用途 | 示例 |
|------|------|------|
| `routes_v1_<domain>.py` | 稳定对外 API（默认） | `routes_v1_trade_plan.py` |
| `routes_v2_<domain>.py` | **禁止新增**；仅用于明确破坏性变更 | 当前无生产 v2 路由 |
| `routes_v1_<domain>.py` | domain 命名，替代 phase 命名 | `routes_v1_cognitive_mesh.py`、`routes_v1_historical_resonance.py`、`routes_v1_jarvis_feed.py`、`routes_v1_zen_mode.py` |
| `v1/<domain>/*.py` | **巨型路由拆分**：dispatcher + 子模块 | `v1/provenance/fingerprint_routes.py`、`v1/wisdom_mesh/strategy_routes.py` |

**新路由文件必须使用 domain 命名**，禁止新增 `routes_v*_phase*.py`。

### 巨型文件拆分模式

1. `routes_v1_<domain>.py` 保留 `@register_routes` dispatcher（≤30 行）。
2. 子模块导出 `register_<area>_routes(blueprint, ctx, **deps)`，**不**重复 `@register_routes`。
3. 共享解析/校验放入 `v1/<domain>/_helpers.py` 或 `runtime.py`（服务工厂）。

### 嵌套 Blueprint（lifecycle 等）

部分域使用子蓝图 `url_prefix="/<domain>"`，由 dispatcher `bp.register_blueprint(child_bp)` 挂到 v1 父蓝图：

```python
lifecycle_bp = Blueprint("lifecycle", __name__, url_prefix="/lifecycle")
register_lifecycle_data_routes(lifecycle_bp, ctx)
bp.register_blueprint(lifecycle_bp)  # → /api/v1/lifecycle/...
```

子模块的 `register_*_routes` 接收**子蓝图**，而非 v1 父蓝图。

## URL 前缀

| 层级 | 前缀 | 注册方式 |
|------|------|----------|
| v1 REST | `/api/v1` | `@register_routes` 或子 Blueprint `url_prefix`（**不再重复** `/api/v1`） |
| v2 REST | `/api/v2` | 仅保留给明确破坏性变更；当前无生产 v2 路由 |
| Web 页面 | 无 `/api` 前缀 | `presentation/web/pages_*.py` |

### 反模式（已修复案例）

- 子 Blueprint `url_prefix="/api/v1/truth"` 挂到已有 `/api/v1` 父蓝图 → 双重前缀 `/api/v1/api/v1/...`
- 正确：子蓝图前缀为 `/truth`，由父蓝图提供 `/api/v1`

## 端点命名

- 资源集合：`GET /api/v1/<domain>/<resource>`
- 单资源：`GET /api/v1/<domain>/<resource>/<id>`
- 动作：`POST /api/v1/<domain>/<resource>/<id>/<action>`（如 `approve`、`cancel`）

使用 **kebab-case** 路径段（`trade-plan` 优于 `trade_plan`）。

## 响应格式

| 版本 | 格式 |
|------|------|
| v1 | 历史兼容：多种格式并存，新端点优先 `{ "ok": true, "data": ... }` |
| v2 | 强制 `{ "ok": bool, "data": T, "meta": {...} }` |

错误响应统一经 `error_handlers.py`（阶段二 R8 将合并 `exception_handlers.py`）。

## v2 模块收敛计划

当前 v2 文件：

- `routes_v2_jarvis_neural.py` → 目标：`routes_v2_jarvis.py`
- `routes_v2_phase17.py` → 并入对应 domain 或 `routes_v2_user_tiers.py`
- `routes_v2_phase18.py` 已迁移为 `routes_v1_zen_mode.py`；旧 `/phase18` 合约如需保留，应通过 302/别名兼容一个版本周期

收敛时保持旧路径 302/别名至少一个版本周期。

## 注册检查清单

新增路由 PR 须确认：

1. 文件名符合 `routes_v1_<domain>.py`
2. 无双重 `/api/v1` 前缀
3. `pytest tests/test_route_smoke_critical.py` 或 boot smoke 通过
4. `REFACTORING_LOG.md` 记录对外契约变更
