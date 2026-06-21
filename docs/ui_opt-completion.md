# UI-OPT 完成清单

与 `docs/ui_opt.md`、`REFACTORING_LOG.md` 阶段 45–57 对应。

## 决策与连贯性

| 阶段 | 能力 | 关键入口 |
|------|------|----------|
| 45 | 操盘台晨会三栏 + 决策证据 + 快讯信号 | `/daily-workbench`、`morning_call` |
| 47–48 | 可操作错误 + 系统健康顶栏 | `QCApiError`、`/system/health-banner` |
| 50 | 因子对标 + 交易预检 | `/attribution/compare`、`/trading/preflight` |
| 55 | 全局焦点栏 + URL 上下文 | `focus_context.js`、`/focus/context` |

## 认知减负

| 阶段 | 能力 | 关键入口 |
|------|------|----------|
| 52 | 对齐层 + K 线 LTTB 采样 | `DateAligner`、`max_points` |
| 53 | 假设验证分析 | `/ai/hypotheses`、`user_hypothesis` |
| 54 | 数据事实化 + 结论追踪 | `QCTraceLink`、`close_fact` |
| 56 | 数据覆盖度 + 置信度降权 | `/data-coverage`、`coverageBanner` |

## 异步反馈

| 阶段 | 能力 | 关键入口 |
|------|------|----------|
| 51 | 任务进度步骤 + 轮询反馈 | `/system/tasks/<id>/feedback`、`QCTaskFeedback` |
| 57 | SSE 任务推送（替代高频轮询） | `/system/tasks/<id>/stream`、`TaskEventHub` |

## 回归测试

```powershell
python -m pytest tests/test_phase45_ui_opt_workbench.py tests/test_phase47_48_ui_opt.py tests/test_phase50_compare_preflight.py tests/test_phase51_task_feedback.py tests/test_phase52_alignment_sampling.py tests/test_phase53_hypothesis_analysis.py tests/test_phase54_market_fact_trace.py tests/test_phase55_focus_context.py tests/test_phase56_data_coverage.py tests/test_phase57_task_stream.py -q
```

## 后续可选

- Flask-SocketIO 与行情推流统一（`websocket_adapter` 尚未接入 bootstrap）
- 多 Worker 场景下 TaskEventHub 改 Redis Pub/Sub
