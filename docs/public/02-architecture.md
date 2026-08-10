# 02 · 架构说明

本文是对外精简版。完整工程说明见 [`app/README.md`](../../app/README.md)。

## 分层（依赖单向）

| 层级 | 路径 | 职责 |
|------|------|------|
| 表现层 | `app/presentation/` | HTTP、模板、JSON、路由 |
| 应用层 | `app/modules/*/services/` | 用例编排（canonical） |
| 领域层 | `app/domain/` | 实体、枚举、端口 Protocol |
| 基础设施 | `app/infrastructure/` | 仓储、外部 API、执行适配 |
| 横切 | `app/core/`、`app/config/` | 日志、Registry、事件总线、配置 |
| 组合根 | `app/bootstrap.py`、`bootstrap_components/` | 组装与启动 |

约束要点：

- 领域层不依赖基础设施 / 表现层  
- `app/application/services/*` 多为 re-export shim，业务实现在 `modules/`  
- 禁止 `from app.bootstrap_components.services import *`

## 上下文模块（14）

| 模块 | 摘要 |
|------|------|
| `system` | 健康、监控、任务、通知 |
| `market_data` | 行情、自选、TDX、实时 |
| `strategy` | 回测、因子、推荐、优化 |
| `ai_agent` | 分析、委员会、证据 |
| `execution` | 交易与执行管线 |
| `portfolio` / `portfolio_risk` | 组合与风险 |
| `data` | 数据湖、Qlib |
| `research` | 研究流水线 |
| `collaboration` | 团队协作 |
| `user` | 用户画像与知识 |
| `mesh` / `perception` | 分布式与感知实验能力 |
| `misc` | 投资经理、集成栈等 |

模块经 `@register_module` 注册，启动时 `initialize_all_modules()` 调用各模块 `wire()`。

## 依赖注入

```python
from app.bootstrap_components.services import create_services

services = create_services(registry_config=...)
```

- Factory 注册：`wiring_market` / `wiring_system` / `wiring_trading` / `wiring_ai`
- 就绪分级：`REQUIRED` / `OPTIONAL` / `FEATURE_FLAG`（见 `service_readiness.py`）

## API 表面

| 版本 | 前缀 | 说明 |
|------|------|------|
| v1 | `/api/v1/*` | 主路径；支持服务降级装饰器 |
| v2 | `/api/v2/*` | DTO 校验，响应形如 `{ok, data, meta}` |

契约与门禁：[API 文档](./04-api.md)、[`docs/API_ROUTE_CONTRACT.md`](../API_ROUTE_CONTRACT.md)

## 前端双轨

- **SPA**：`frontend/`，开发/生产挂载于 `/app`
- **经典页**：`app/presentation/web/templates/`（Jinja）

新功能优先落在 SPA；经典页保持兼容。

## 下一步

- [快速开始](./03-getting-started.md)
- [贡献指南](./07-contributing.md)
