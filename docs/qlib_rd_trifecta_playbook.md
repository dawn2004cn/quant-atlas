# Qlib · RD-Agent · 六分析师：高性价比三件落地

本文档固化「如何在本平台发挥 Qlib、RD-Agent、TradingAgents 式六分析师」的结论，并对应**已实现的三个落地项**与运维开关。

## 战略摘要

- **Qlib**：作为 **A 股日频结构化数据的统一出口**（CSV → `qlib_bin` → 可选 pyqlib 读数），与平台既有 `metrics` 字段对齐；用显式字段 `backtest_engine` 区分 **pyqlib 路径** 与 **pandas 行情适配器** 回退路径。
- **RD-Agent**：因子实验产物通过注册表可查询；注册成功后自动跑 **Qlib 门禁**（参考标的上的统一买入持有），结果写入 `runs/{id}.json` 的 `qlib_gate`，避免「有因子、无数据管道」的静默失败。
- **六分析师（LangGraph）**：在工具层显式挂载 `get_research_pipeline_status`、`run_qlib_unified_backtest`，并与原有 `get_qlib_factor_snapshot`、`run_backtest` 并列，保证辩论与 Supervisor 能引用 **evidence / confidence** 对齐的闭环状态。

## 三件落地（已实现）

### 1. 统一 Qlib 回测出口

- **服务**：`QlibPipelineService.unified_buy_hold_backtest` — CN 且已安装 pyqlib、`qlib_bin` 就绪时走 `D.features`；否则回退 `simple_backtest`。
- **API**：`POST /api/v1/qlib/backtest` 已改为调用 unified；响应中带 `backtest_engine`（如 `pyqlib_bin_buy_hold` / `pandas_adapter_buy_hold`）。
- **工具**：`run_qlib_unified_backtest`（`ENABLE_QLIB=1`）。

### 2. RD 注册后 Qlib 门禁

- **触发**：`rdagent_tasks._run_with_job_store` 在 `register_from_result` 成功后调用 `execute_rdagent_qlib_gate`。
- **逻辑**：从 `qlib_pipeline_meta` 或磁盘 CSV 茎名取参考标的，跑 unified 买入持有；无标的时 `skipped: true`，**不抛异常**。
- **存储**：`RDAgentArtifactRegistry.merge_qlib_gate` 写入 bundle 并补丁 `registry_index.json` 中的 `qlib_gate_ok` / `qlib_gate_skipped`。

### 3. Agent 工具 + 前端闭环页

- **工具**：`get_research_pipeline_status` 与 API 同源快照；技术分析师增加 `get_qlib_factor_snapshot`；回测优化师须对照 `run_qlib_unified_backtest`。
- **前端**：导航 **研究闭环** → `/research-pipeline`，轮询 `GET /api/v1/research/pipeline-status`（需登录），步骤条 + Mermaid 流程图 + 最近 RD run 与 `qlib_gate` 列。

## 环境开关

| 变量 | 作用 |
|------|------|
| `ENABLE_QLIB` | 打开 Qlib 管道 API、相关工具与门禁中的 unified 回测 |
| `ENABLE_RD_AGENT` | 打开 RD 提交与索引；快照中 RD 步骤才视为可用 |
| `ENABLE_CELERY` | RD 默认异步 worker；无 broker 时退化为线程（既有行为） |

## 相关代码路径（便于审计）

- `app/application/services/qlib_pipeline_service.py` — `unified_buy_hold_backtest`
- `app/infrastructure/rdagent/qlib_gate.py` — `execute_rdagent_qlib_gate`
- `app/infrastructure/rdagent/artifact_registry.py` — `merge_qlib_gate`
- `app/application/services/research_pipeline_snapshot.py` — `build_research_pipeline_snapshot`
- `app/presentation/api/routes.py` — `/research/pipeline-status`、`/qlib/backtest`
- `app/tools/quant_tools.py` — 新工具与 `QuantToolRuntime` 注入
- `app/agents/research/graph.py` — 各节点工具列表与系统提示
- `app/presentation/web/templates/research_pipeline.html` — 流程展示页

更完整的路线图背景见 `docs/roadmap_qlib_rd_agent.md`。
