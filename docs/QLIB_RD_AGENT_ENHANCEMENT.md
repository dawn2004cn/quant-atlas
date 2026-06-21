# Qlib + RD-Agent 增强方案（发挥不足时的补短）

**背景**：仓库已具备 Qlib 管线（ingest、CSV、可选 `qlib_bin`、简易/统一回测、因子快照 API）、RD-Agent（异步因子循环、产物注册表、`qlib_gate`）、选股侧 `data_source=qlib_factors|model_score` 与 `factor_ic` 巡检，但 **默认开关关闭**、**门禁过弱**、**RD 产物与日常研究链路衔接薄**，体感上「能力未发挥」。本文给出 **可验收的增强路径**，与 [roadmap_qlib_rd_agent.md](roadmap_qlib_rd_agent.md) 阶段 1b～4 互补。

---

## 一、根因归纳（为何显得「没用上」）

| 现象 | 技术原因 |
|------|-----------|
| 功能「看不见」 | `ENABLE_QLIB`、`ENABLE_RD_AGENT` 默认 `0`；未开时 API/工具直接拒绝或空摘要。 |
| 数据未就绪就跑 RD | `provider_uri` / `qlib_bin` 与 RD `factor_template` 不一致时，循环质量差或失败；缺少 **前置检查** 与 UI 引导。 |
| Qlib 仍偏「管道」而非「研究」 | 示例因子 **MA5/RET1**、回测多为 **买入持有**；与 pyqlib **Alpha 表达式 / Dataset / 官方回测器** 未完全打通（路线图阶段 1b）。 |
| RD 产物未回流业务 | `artifact_registry` 有清单，但 **未自动写入因子目录 / 未进 `factor_ic` 候选集 / 选股默认仍为 legacy**，价值断在最后一公里。 |
| `qlib_gate` 过弱 | 当前为 **单标的、买入持有、取 meta 第一只** 的烟测（`qlib_gate.py`），**不验证 RD 本轮因子表达式** 是否可算、IC 是否达标。 |
| 运行形态 | RD 强依赖 **Celery + LLM + rdagent 包**；开发机未起 worker 或未配模型时，提交后长期 `queued/running` 无感知，易被误判为「坏了」。 |

---

## 二、增强总目标（建议写进迭代 OKR）

1. **默认可演示路径**：在「研究环境」文档中约定一组 env，使 **ingest → dump_bin → 一次 RD 小循环 → research/pipeline-status 全绿（或可解释的黄）** 可在 < 1 小时内跑通。
2. **Qlib 从管道进研究**：至少 1 条路径走 **pyqlib 官方 workflow 或等价**（因子表 + 标签 + 回测指标与平台字段对齐）。
3. **RD 从实验进资产**：每轮成功 run 的 **可执行因子定义** 进入 **版本化因子库**（文件或 SQLite），并可选 **自动进入 IC 监控名单**。
4. **门禁可解释**：`qlib_gate` 输出 **与 RD 产物同口径** 的最小验证（表达式可 eval、无全 NaN、样本内 IC 或简单多空分层二选一）。

---

## 三、分层增强清单

### 3.1 运维与产品（低成本、优先做）

- **环境模板**：在 `docs/` 或 `.env.example` 中给出「研究全开」最小集合：`ENABLE_QLIB=1`、`ENABLE_RD_AGENT=1`、`QLIB_CELERY_BEAT` / Celery worker、`FACTOR_IC_CELERY_BEAT`（按需）、`CELERY_BROKER_URL`。
- **健康检查习惯化**：监控或值班脚本轮询 `GET /api/v1/qlib/health` + `GET /api/v1/qlib/status`（`csv_count`、`qlib_bin_ready`、`pyqlib_installed`）。
- **研究闭环页**：已有 `GET /api/v1/research/pipeline-status`；前端保证 **常驻入口**（导航 + 失败时展示 `steps[].detail` 可操作提示，例如「请先 ingest + dump_bin」）。

### 3.2 Qlib 深度（阶段 1b 对齐）

| 项 | 说明 | 建议落点 |
|----|------|-----------|
| pyqlib 安装路径 | Linux/WSL2/Docker 优先；与 roadmap「风险」一致。 | CI job、`requirements-qlib.txt` |
| `dump_bin` 默认策略 | ingest 后一键或夜间任务 **稳定写 `qlib_bin`**，RD `provider_uri` 与平台统一。 | `QlibPipelineService`、`qlib_data_update` |
| 回测 `source` | `stub`（现简易）与 `qlib`（官方或统一 Dataset）可切换，响应带来源字段。 | `routes_v1_qlib_rd.py`、`qlib_pipeline_service` |
| 因子扩展 | 在 MA5/RET1 基础上增加 **Alpha158 子集或 5～10 个表达式**，供选股与 Agent 工具消费。 | `qlib_pipeline_service`、因子 JSON/YAML |

### 3.3 RD-Agent 编排（阶段 2 加深）

| 项 | 说明 | 建议落点 |
|----|------|-----------|
| 提交前校验 | `POST /rd-agent/runs` 前检查 `provider_uri` 存在、`qlib_bin_ready` 或 CSV 数量下限；不满足则 **400 + 明确文案**。 | `RDAgentRunService.submit_run`、`build_research_pipeline_snapshot` |
| 模板与数据契约 | 保持 `prepare_patched_factor_template` 与 **平台 `qlib_pipeline_meta.json` instruments** 同源说明写进 API 文档。 | `rdagent_factor_loop.py`、文档 |
| Webhook / 消息中心 | 成功/失败除 `RDAGENT_WEBHOOK_URL` 外，**推送 task_message_store**（与现有 Celery 信号一致），避免「任务跑完无人知」。 | `rdagent_tasks.py` 或 Celery 装饰器 |

### 3.4 产物回流与监控（阶段 3 延伸）

| 项 | 说明 | 建议落点 |
|----|------|-----------|
| 因子注册 | `register_from_result` 后解析表达式 → 写入 `config/factor_catalog` 或扩展 `factor_catalog_service` **带 `run_id` 溯源**。 | `artifact_registry`、`factor_catalog_service` |
| IC 名单 | 环境变量 **`FACTOR_IC_AUTOPUBLISH_TAIL=N`**（或 ``GET /api/factor/monitor?autopublish_tail=N``）把 ``autopublish.jsonl`` 尾部并入弱 IC 扫描，与 ``limit_runs`` 截断互补。 | `factor_catalog_service.monitor_summary`、`factor_ic_alerts` |
| 选股默认 | 内部环境可将 `long-term-select` 默认 `data_source` 设为 `qlib_factors`（仅当 CSV/bin 就绪），与 legacy 做 A/B。 | `SelectionSourceService`、前端默认 |

### 3.5 `qlib_gate` 升级（高价值小步）

**现状**：单标的 buy-hold 烟测。  
**建议演进（分步）**：

1. **Gate v1**（已落地）：buy-hold 标的优先 **bundle.benchmark**（如 `SH000300`），否则 meta 第一只。  
2. **Gate v2**（已落地·轻量）：对 bundle 中 **最新 round 的 factor_task** 校验 `factor_formulation` 非空与长度上限；若 metrics 含 `ic_lag_1` 则须为有限浮点；结果写入 `qlib_gate.factor_expression_gate`，并与 buy-hold 结果 **合取** `ok`。（Dataset 级非空率/正式 IC 计算留待后续 pyqlib 深化。）  
3. **Gate v3**：调用与 `POST /qlib/backtest` 相同的 **多空或 topK 简化策略**（若已实现 pyqlib 路径）。

落点：`app/infrastructure/rdagent/qlib_gate.py`、`app/infrastructure/rdagent/factor_expression_gate.py`；导出：`app/infrastructure/rdagent/factor_catalog_export.py`、`GET /api/factor/autopublish`。

---

## 四、优先级与工期建议

| 优先级 | 包 | 预期工期 | 验收 |
|--------|-----|-----------|------|
| **P0** | 运维模板 + 提交前校验 + 研究页提示 | 0.5～1 周 | 误提交 RD 明显减少；pipeline-status 可读可操作 |
| **P1** | pyqlib + dump_bin 稳定 + 回测 `source=qlib` | 2～4 周 | 与 stub 对比报告一份；CI 一条 qlib job |
| **P2** | 产物→因子目录 + IC 名单 + gate v2 | 2～3 周 | 新 run 后因子可被选股/IC 引用；gate 与因子相关 |
| **P3** | Webhook 同构消息中心 + TradingAgents 工具默认走 qlib | 与阶段 4 并行 | 分析师工具链默认命中 qlib 数据 |

---

## 五、与现有文档关系

- **阶段勾选**：仍以 [roadmap_qlib_rd_agent.md](roadmap_qlib_rd_agent.md) 为准；**阶段 1b** 与本文 **3.2** 对齐；**阶段 3～4** 与 **3.4～3.5** 对齐。  
- **闭环叙事**：[case.md](case.md) 中 Phase A/B。  
- **数据纪律**：[DATA_FLOW.md](DATA_FLOW.md)。

---

## 六、不建议的做法

- 在未稳定 **`provider_uri` + bin** 前盲目增大 `max_loops`（成本与失败率陡增）。  
- 把 pyqlib `import` 放进 `bootstrap.py` 顶层（拖慢全站启动、违背路线图原则）。  
- 用「单只股票 buy-hold 通过」作为 **因子质量** 的唯一标准（容易假阳性）。

---

*文档维护：随 `qlib_gate`、回测 `source`、因子目录实现进度更新验收列。*
