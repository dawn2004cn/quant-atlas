# Phase 2 重构总结（Registry · DecisionContext · 弹性网格 · ContextModule）

> 日期：2026-06-08 · Sprint 0–8 落地快照

## 目标回顾

| 维度 | 目标 | 状态 |
|------|------|------|
| Registry 全覆盖 | `@register_service` / `@register_routes` / `@register_module` + `register_factory` | 路由 + 16 服务 + 4 factory（gpcw/industry/data_infra/tdx_base） |
| AI 决策实体化 | `DecisionContext` / DTO + trace | AI 分析、投委会选股已落地 |
| 弹性网格 | 熔断 + 多源降级 + `X-System-Degraded` | OpenBB/Ollama/FinGPT/CCXT/Tencent + 行情 L2/yfinance |
| ContextModule | 领域模块化物理包 | collaboration、portfolio_risk |
| ContextVar | `user_id` / `request_id` 自动注入 | Flask 中间件 + 路由 `_uid()` 已全覆盖 |

## 架构示意

```mermaid
flowchart TB
    subgraph bootstrap [Bootstrap]
        preload[preload_route_modules]
        discover[discover_routes]
        wire_mod[wire_context_modules]
        wire_legacy[wire_legacy_container_services]
    end
    subgraph registry [app/core/registry.py]
        routes[@register_routes]
        services[@register_service]
        modules[@register_module]
    end
    subgraph resilience [弹性网格]
        cb[CircuitBreakerRegistry]
        degraded[degraded_context ContextVar]
        hdr[X-System-Degraded 响应头]
    end
    preload --> discover
    routes --> discover
    modules --> wire_mod
    cb --> degraded --> hdr
```

## 关键模块

### 1. 声明式 Registry

- **路由**：`app/presentation/api/route_loader.py` 在 `discover_routes()` 前扫描 `routes_v1_*`
- **注册**：`app/presentation/api/routes.py` → preload → auto-discover → legacy 空壳（仅 `admin_stock_cache` 特殊签名在 `create_api_blueprint` 单独处理）
- **服务**：`configure_service_registry(config)` + 各 ContextModule `wire()`

### 2. ContextModule（物理包）

| 模块 | 路径 | 配置开关 | 职责 |
|------|------|----------|------|
| collaboration | `app/modules/collaboration/` | `ENABLE_COLLABORATION` | 租户/团队/协作 OS |
| portfolio_risk | `app/modules/portfolio_risk/` | — | portfolio/risk/watchlist wire |

`context_modules.py` 中其余 12+ 逻辑 Context 仍待物理化。

### 3. AI DecisionContext

- **Domain**：`DecisionContext` 实体 + `DecisionContextDTO`
- **服务**：`AiAnalysisService.analyze()`、`AICommitteeSelectionService.run_selection()` 返回 `decision_id` + `decision`
- **Trace**：`DecisionTraceService` → Redis `quant:decision:trace:{id}`（7 天 TTL，内存回退）
- **API**：`GET /api/v1/decision/trace/<decision_id>`

### 4. 弹性网格（熔断 + 降级）

| 组件 | 熔断键 | OPEN 行为 |
|------|--------|-----------|
| OpenBB | `openbb_*` | 空 quotes/history/profile |
| Ollama | `ollama_generate` | `degraded: true` |
| FinGPT | `fingpt_sentiment` | 降级 sentiment |
| CCXT | `ccxt_{exchange_id}` | OHLCV 空列表；下单抛错 + degraded |
| Tencent | `tencent_quotes` | 空 quotes text + degraded |
| TDX Legacy | `tdx_legacy` | `execute` 返回 None + degraded |
| 行情 MultiSource | 内置 CB + L2 | `mark_system_degraded(reason)` |

**响应头**（`app/core/middleware/degraded_context.py`）：

- `X-System-Degraded: true`
- `X-System-Degraded-Reason: <reason>`

### 5. ContextVar 注入

- `app/core/middleware/request_context.py`：`request_id`、`user_id`
- 响应头：`X-Request-ID`
- 路由迁移：`require_authenticated_user_id()` / `_uid()`（collaboration、portfolio_users、ai_committee_selection 等）

## Bootstrap 装配顺序

```
wire_feature_services
→ wire_extended_services
→ wire_context_modules          # collaboration + portfolio_risk
→ wire_legacy_container_services
→ wire_optional_application_services
→ wire_presentation_layer_services
```

## 运维备忘

- **Redis**：见 [redis.md](./redis.md) — Decision trace、Mesh、Celery
- **降级观测**：检查响应头 `X-System-Degraded`；日志搜 `mark_system_degraded`
- **熔断状态**：`CircuitBreakerRegistry` 进程内；重启清零

## 后续建议

1. 将其余 procedural `wire_*` 逐步改 `register_factory`（`ai_analysis`、`diagnosis_report` 等依赖链）
2. 物理 ContextModule 包扩展（market_data、strategy 等）
3. Phase 2 收尾文档与运维 runbook 合并进平台手册

## 相关测试

```bash
pytest tests/bootstrap/test_service_loader.py
pytest tests/core/test_modules_shim.py
pytest tests/core/test_context_module_manifest.py
pytest tests/application/test_evidence_graph_service.py
pytest tests/infrastructure/test_legacy_tdx_adapter.py
pytest tests/core/test_degraded_context.py
```
