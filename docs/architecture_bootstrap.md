# Bootstrap & DI 约定（2026-05-22）

## 单一启动路径

- 入口：`app.bootstrap.create_app()` → `bootstrap_components`（`repositories` / `providers` / `create_services` / `ApiBundle`）。
- **禁止**在 `app/presentation` 中 `from app.core.container import container` 取服务（Celery 任务等后台入口除外，且应收敛到 `container` 模块级单例）。

## 服务装配

- 生产路径：`bootstrap_components.create_services()` + `service_wiring.py` 显式装配。
- `app.application.service_locator` 已废弃，勿新增 `@service` 装饰器。
- `app.extensions["service_bundle"]` / `api_bundle` 为请求内获取服务的标准来源。

## 服务就绪契约（阶段 6）

- **REQUIRED**（缺则 `STRICT_BOOTSTRAP=1` 时启动失败）：`market_service`, `stock_service`, `watchlist_service`, `stock_group_service`, `auth_service`
- **OPTIONAL**：由路由 `require_ctx_service` → 400；见 `service_readiness.py`
- **FEATURE_FLAG**：qlib / rdagent / kronos 等，不阻塞启动
- 禁止在 `create_api_blueprint` 内构造服务；统一 `wire_presentation_layer_services` + `validate_service_readiness`

## API 上下文

- `create_api_v1_context(api_bundle)` 为唯一工厂；已移除 `__getattr__` 动态兜底。
- 新路由优先 `route_deps.py` 窄 Deps（`RiskRouteDeps` / `SocialRouteDeps` / `MarketRouteDeps` / `AiRouteDeps` / `WorkbenchRouteDeps` / `PortfolioUserRouteDeps` / `PortfolioRouteDeps` / `FinGptRouteDeps` / `RecommendationRouteDeps` / `MemoryRouteDeps` / `TaskPipelineRouteDeps` / `DataInfrastructureRouteDeps` / `DataOptimizerRouteDeps`），勿扩展扁平 `ApiV1Context` 字段。
- 路由模块禁止 `getattr(ctx, ...)`（`common.ensure_service` / `require_ctx_service` 除外）；禁止在路由内 lazy 构造 Service。

## 异步编排（阶段 9）

- 同步 Flask 路由调用 async Service 时统一使用 `app.application.request_executor.run_async(coro)`。
- 禁止在 `app/presentation/api/**` 内直接使用 `asyncio.run` / `get_event_loop` / `run_until_complete`。
- 应用层同步入口（`@async_task`、Service 同步包装 async 方法）同样委托 `run_async`。

## 仓储与数据库（2026-05-23）

- 仓储目录：`app/infrastructure/repositories/` → `common/` / `mysql/` / `sqlite/` / `postgres/`（详见 `docs/refactor/repositories-layout.md`）。
- 工厂入口：`infrastructure.repositories.deps`（bootstrap、tasks）；application 禁止直连 deps。
- TimescaleDB：`USE_TIMESCALEDB=1` + `TIMESCALEDB_*`；工厂 `create_timescale_bar_repository` / `create_postgres_connection_port`。

## 功能服务装配

- 投资经理、朋友圈等依赖 SQLite/MySQL 仓储的服务由 `wire_feature_services()` 装配；不可在 `container` 无参 Singleton 中声明。
- 若某 API 返回 404 且日志无异常，先检查对应 `register_*_routes` 是否因 `ctx.*_service is None` 跳过注册。

## API 上下文分组（阶段 3）

- 新路由优先使用 `ctx.market.*` / `ctx.social.*` / `ctx.ai.*`；扁平字段 `ctx.stock_service` 仍兼容旧代码。
- 工厂：`create_api_v1_context` 末尾调用 `attach_context_groups(ctx)`。

## API 错误契约（阶段 18，2026-05-22）

路由层应 **`raise`** 应用异常，由 `register_api_error_handlers` 统一序列化；禁止在业务路径返回 `ok_response(data={"error": ...})` 或手写 `jsonify({"error": ...})`。

### 错误响应体（`ApplicationError` 子类）

```json
{
  "status": "error",
  "error": {
    "code": "validation_error",
    "message": "symbols_required",
    "details": {}
  }
}
```

| 异常类 | HTTP | `error.code` | 典型 `message` |
|--------|------|----------------|----------------|
| `ValidationError` | 400 | `validation_error` | `symbol_required`, `*_service_unavailable` |
| `AuthorizationError` | 403 | `authorization_error` | 权限不足 |
| `NotFoundError` | 404 | `not_found` | `experiment_not_found`, `pipeline_not_found` |
| `ExternalServiceError` | 503 | `external_service_error` | `celery_disabled`, `tdx_not_configured` |

### 成功响应体

- 主流 v1 路由：`ok_response` / `ok_resource` / `ok_collection`（见 `presentation/api/common.py`）。
- Agent Swarm（`/api/v1/agent-swarm/*`）：成功与主流 v1 一致，使用 `ok_response`（`status: success`, `data`）；**错误**抛 `ValidationError` / `NotFoundError` / `ExternalServiceError`。前端取数优先 `json.data`，必要时兼容旧 `code/data/message` envelope。

### 路由开发检查清单

1. 缺参 / 缺服务 → `ValidationError`
2. 资源不存在 → `NotFoundError`
3. 外部依赖不可用（Celery、TDX、WebSocket）→ `ExternalServiceError`
4. 同步路由调 async → `run_async(coro)`

## Agent 研究边界（阶段 4）

- 应用层只依赖 `ResearchPort`；`TradingAgentsResearchAdapter` 在 infrastructure 内延迟加载 `app.agents`。
- **禁止**在 `app/agents/**` 顶层 `import app.application.services.*`（`TYPE_CHECKING` 除外）。
