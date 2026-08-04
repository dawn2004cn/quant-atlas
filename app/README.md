# `app` 包架构说明

本目录为 **Quant Atlas** 主程序代码根。目标：**分层清晰、依赖单向、命名可读**，并与经典 **SOLID** 原则对齐。

## 分层（自上而下依赖）

| 层级 | 路径 | 职责 | 允许依赖 |
|------|------|------|-----------|
| **表现层** | `presentation/web`、`presentation/api` | HTTP、模板、JSON、路由注册、Flask-Login | `application`（shim）、`domain`、`config`；不写业务规则 |
| **应用层** | `modules/*/services/`（canonical） | 用例编排、权限与校验入口 | `domain` 端口；经 registry 访问基础设施 |
| **领域层** | `domain/`、`domain/ports/` | 实体、枚举、端口协议、分析逻辑 | 仅标准库 / typing |
| **基础设施层** | `infrastructure/` | 仓储、外部 API、TDX、Qlib、适配器 | `domain` |
| **上下文模块** | `modules/<context>/` | 按 bounded context 聚合服务、路由元数据、`wire()` | `core.registry`、同层端口 |
| **横切** | `core/`、`config/` | 日志、事件总线、registry、配置 | 最小依赖 |
| **任务** | `tasks/` | Celery 任务组合 | 与 bootstrap 同级组合根 |
| **组合根** | `bootstrap.py`、`bootstrap_components/` | `create_services()`、蓝图、预热 | 各层 |

> **2026-07 阶段 E**：`application/services/*` 仅为 re-export shim；业务实现位于 `modules/*/services/`。

## 上下文模块（14 个）

| 模块 | 职责摘要 |
|------|----------|
| `system` | 健康、监控、告警、任务、通知 |
| `market_data` | 行情、自选股、TDX、实时 |
| `strategy` | 回测、因子、推荐、优化 |
| `ai_agent` | 分析、委员会、FinGPT、证据 |
| `execution` | 交易、预检、执行管线 |
| `portfolio` / `portfolio_risk` | 组合、风险 |
| `data` | 数据湖、Qlib、因子数据 |
| `research` | 研究流水线、Agent |
| `collaboration` | 团队、黑板、工作流 |
| `user` | 画像、生命周期、知识 |
| `mesh` | 分布式 mesh、感知 |
| `perception` | 10.0 manifest / resonance |
| `misc` | 投资经理、集成栈、诊断 |

模块通过 `@register_module` 注册，`module_wiring.initialize_all_modules()` 在启动时调用各模块 `wire()`。

## Bootstrap / DI

唯一服务容器入口：

```python
from app.bootstrap_components.services import create_services

services = create_services(registry_config=...)
```

- **TypedServiceRegistry**：`bootstrap_components/service_wiring.py` + `wiring_{market,system,trading,ai}.py` 注册 factory
- **后置装配**：`bootstrap_components/post_wire_hooks.py`（recommendation / optimization / strategy_sop）
- **就绪分级**：`service_readiness.py` — `REQUIRED` / `OPTIONAL` / `FEATURE_FLAG`
- **禁止**：`from app.bootstrap_components.services import *`（架构测试门禁）

`app/bootstrap_services.py` 为兼容 re-export，指向上述 canonical 路径。

## 统一工具门面 (ToolFacadeService)

Canonical：`app/modules/system/services/tools/tool_facade_service.py`

```python
from app.modules.system.services.tools.tool_facade_service import ToolFacadeService

facade = ToolFacadeService(market_provider=..., stock_service=..., ...)
bars, note = facade.fetch_bars("600519", MarketCode.CN)
```

`app/application/services/tool_facade_service.py` 为 re-export shim。

## API 版本化

| 版本 | 路径 | 特性 |
|------|------|------|
| v1 | `/api/v1/*` | 传统格式；`@service_fallback` / `@deps_service_fallback` 优雅降级 |
| v2 | `/api/v2/*` | DTO 验证，`{ok, data, meta}` |

路由契约与 CI 四门：见 `docs/API_ROUTE_CONTRACT.md`。

公开 GET（无需登录）：`app/presentation/api/public_api_paths.py`

## 目录结构（精简）

```
app/
├── modules/                    # Bounded contexts（业务实现）
│   ├── market_data/services/
│   ├── strategy/services/
│   ├── ai_agent/services/
│   ├── system/services/
│   │   ├── system/             # 基础设施型服务
│   │   ├── ui/                 # 页面/工作台 DTO 服务
│   │   ├── tools/              # ToolFacade 等
│   │   └── helpers/            # wiring access（逐步下沉）
│   └── .../module.py           # wire() + 路由元数据
├── domain/ports/               # 端口协议（canonical）
├── infrastructure/             # 端口实现
├── presentation/api/
│   ├── routes_v1_*.py          # 薄编排器
│   └── v1/<domain>/            # 子路由模块（>300 行拆分）
├── bootstrap_components/       # DI、post_wire、readiness
├── agents/research/            # LangGraph 多智能体研究
└── tasks/                      # Celery
```

## SOLID 对照

1. **S** — 模块 + 服务按上下文拆分；巨型路由拆至 `presentation/api/v1/`
2. **O** — 新能力通过 `register_factory` / `@register_capability` 扩展
3. **L** — 端口实现可替换
4. **I** — `domain/ports/` 按能力拆分
5. **D** — 应用代码依赖端口与 registry，不依赖具体适配器
6. **迪米特** — 表现层经 `ApiV1Context` / `route_deps` 取服务

## 相关文档

- 平台手册：`docs/QUANT_ATLAS_平台手册.md`
- API 路由契约：`docs/API_ROUTE_CONTRACT.md`
- 重构记录：`REFACTORING_LOG.md`
- Repositories：`docs/refactor/repositories-layout.md`
- 数据库：`docs/DATABASE_GUIDE.md`
