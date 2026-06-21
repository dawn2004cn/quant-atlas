# Phase 4 重构计划（极致解耦 · 主动智能）

> 日期：2026-06-08 · Sprint 0 落地快照

## 四大维度

| 维度 | 目标 | Sprint 0 状态 |
|------|------|---------------|
| 插件式服务 | Registry 拓扑排序 + ContextModule 自主 initialize | ✅ 初版 |
| 主动智能 | 降级感知 Jarvis + DecisionFeedback 闭环 | ✅ 初版 |
| 领域瘦身 | entities 按模块拆分 + shared VO | 📋 待办 |
| 流式推理 | AI analyze SSE trace | ✅ 原型 |

## 1. 去中心化启动（Sprint 0）

- **`topological_service_order()`**：`ServiceRegistry.wire_to` 按 `depends` 拓扑注入
- **`initialize_all_modules(session_factory=...)`**：支持 `initialize()` / `wire()` 双路径
- **Collaboration**：`CollaborationContextModule.wire` → `app/modules/collaboration/wire_module`，不再从 `services.py` 单独 `_try_init`
- **`services.py`**：恢复 `wire_optional` 等兜底链；模块初始化传入 `session_factory`

## 2. 主动智能（Sprint 0）

### Health-Aware Routing

- `app/core/middleware/health_aware.py`
- Jarvis `_nav_dto` / 空 query 返回时附加 `system_notice`
- 文案示例：「由于数据源降级（腾讯行情源），部分深度因子分析已替换为基础统计模型。」

### Decision Feedback Loop

- **Domain**：`DecisionFeedback` + `FeedbackRating`（`app/domain/decision_feedback.py`）
- **DTO**：`DecisionFeedbackDTO`
- **Service**：`DecisionFeedbackService` → 持久化 + `UserKnowledgeService.record_interaction`
- **API**：`POST /api/v1/decision/feedback`

```json
{
  "decision_id": "decision_abc123",
  "rating": "up",
  "reasoning_path_id": "0",
  "comment": "optional"
}
```

## 3. 流式推理 Trace（Sprint 0 原型）

- **`AiAnalysisService.analyze_stream()`**：yield `step` / `evidence` / `notice` / `complete`
- **API**：`GET /api/v1/ai/analyze/stream?symbol=600519&market=CN`
- **格式**：SSE `data: {json}\n\n`

事件类型：

| event | 含义 |
|-------|------|
| `step` | 阶段开始（market_data / llm） |
| `evidence` | 单条 EvidenceNote |
| `notice` | 降级提示 |
| `complete` | 最终 decision + analysis |

## 4. 后续 Sprint

1. 将 `_try_init_market_*` 迁入 `MarketDataContextModule.initialize`
2. `entities.py` 拆分到 `app/modules/*/domain/`
3. Shared VO：`Money`, `Ticker`, `StrategySignal`
4. DecisionFeedback → 微调 pipeline（非仅 UserKnowledge 计数）
5. SSE 与 DecisionTrace Redis 联动（增量写入）

## 测试

```bash
pytest tests/application/test_phase4_decision_feedback.py
pytest tests/core/test_context_module_manifest.py
pytest tests/bootstrap/test_service_loader.py
```
