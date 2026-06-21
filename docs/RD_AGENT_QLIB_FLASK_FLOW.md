# RD-Agent → Qlib 验证 → Flask 展示：当前流程说明

本文描述仓库内**已实现**的链路：RD-Agent 自动产生实验想法与产物、Qlib 侧门禁校验、Flask 用户可见状态与决策辅助（非自动下单）。

---

## 1. 总览

```mermaid
flowchart LR
  subgraph ingest [数据与 Qlib 底座]
    D[行情 ingest] --> C[qlib CSV / bin]
  end
  subgraph rd [RD-Agent]
    API[POST /api/v1/rd-agent/runs] --> W[Celery 或后台线程]
    W --> Loop[因子挖掘循环]
    Loop --> Res[结果 JSON：轮次/产物等]
  end
  subgraph post [成功后后置步骤]
    Res --> Reg[Artifact 注册 bundle]
    Reg --> Cat[因子目录导出 / 任务追加]
    Reg --> Gate[Qlib 门禁 execute_rdagent_qlib_gate]
  end
  subgraph qlib [Qlib 严谨验证]
    Gate --> BH[统一买入持有回测]
    Gate --> FE[因子表达式门禁 factor_expression_gate]
    BH --> QG[合并写入 bundle.qlib_gate]
    FE --> QG
  end
  subgraph flask [Flask 用户可见]
    QG --> Snap[/api/v1/research/pipeline-status]
    Cat --> Lab[量化实验室 因子列表/IC 巡检等]
    API --> Poll[GET runs / artifacts]
  end
```

研究闭环页（`/research-pipeline`）由 **`GET /api/v1/research/pipeline-status`** 聚合步骤状态；快照在 `app/application/services/research_pipeline_snapshot.py` 的 `build_research_pipeline_snapshot` 中构建，步骤语义为：**数据 → qlib_bin → RD run → qlib_gate → 六分析师/回测**。

---

## 2. RD-Agent：自动产生「新想法」与代码侧产物

1. **入口**：已登录且具备研究写权限的用户调用 **`POST /api/v1/rd-agent/runs`**（需环境 **`ENABLE_RD_AGENT`**）。路由定义见 `app/presentation/api/routes_v1_qlib_rd.py`。
2. **`RDAgentRunService.submit_run`**（`app/application/services/rdagent_run_service.py`）：
   - 先执行 **`validate_rd_factor_submission`**（`app/infrastructure/rdagent/submission_validate.py`）；
   - 创建 job，将参数交给异步执行：若启用 Celery 则 **`run_rdagent_factor_generation.delay`**，否则 **后台线程** 执行同一任务（`app/tasks/rdagent_tasks.py`）。
3. **任务成功且 `result.ok`** 时（`_run_with_job_store`）：
   - 更新 job 为 completed；
   - **`RDAgentArtifactRegistry.register_from_result`**：注册本次 run 的 **bundle**（`app/infrastructure/rdagent/artifact_registry.py`）；
   - **`append_factor_tasks_from_bundle`**：将 bundle 中的因子任务接入因子目录/导出（`app/infrastructure/rdagent/factor_catalog_export.py`）；
   - 调用 **`execute_rdagent_qlib_gate(job_id, base_dir=...)`**；
   - 可选 webhook；向消息中心推送 **`task_succeeded`** 等事件。

「想法/代码」主要体现在 **每轮因子实验结果、artifacts（含 `factor_task`、`factor_formulation` 等）** 写入注册表与目录，而非在 Flask 模板中直接改写业务源码。

---

## 3. Qlib：严谨验证与「信号」在本项目中的含义

注册成功后由 **`execute_rdagent_qlib_gate`**（`app/infrastructure/rdagent/qlib_gate.py`）执行，结果合并进 **`bundle.qlib_gate`**：

### 3.1 参考标的上的 Qlib 回测门禁

- 使用 **`QlibPipelineService.unified_buy_hold_backtest`**，在 bundle 的 **benchmark**（或元数据/磁盘标的等回退逻辑）上跑 **买入持有** 窗口；
- 根据 **`metrics`**（如 `total_return`、`max_drawdown`、`sharpe_ratio`）与 **`error`** 是否为空，得到门禁是否通过。

含义：**在当前 Qlib 数据与引擎下，该研究产物能否跑通、核心指标是否可读**；**不是**自动向券商发单。

### 3.2 因子表达式门禁（Gate v2）

- **`evaluate_factor_expression_gate`**（`app/infrastructure/rdagent/factor_expression_gate.py`）从 bundle 中取主 **`factor_task`**；
- 校验 **`factor_formulation` 非空、长度上限**；若 metrics 中含 **IC lag1**，则须为**有限浮点**；
- 与买入持有门禁 **逻辑与**：二者均通过时 **`qlib_gate.ok`** 为真（表达式未通过时会附带说明性 `message`）。

### 3.3 「信号」一词的边界

在本仓库中，更贴近的含义是：

- **研究侧信号**：`qlib_gate` 通过/未通过、指标摘要、因子目录与 **IC 巡检**（量化实验室 `/api/factor/monitor` 等）；
- **非**：默认的 **实盘下单信号**；交易决策仍由用户在平台侧完成。

---

## 4. Flask：用户如何看见并辅助决策

| 能力 | 说明 |
|------|------|
| 整条流水线与最近门禁 | 页面 **`/research-pipeline`**（`app/presentation/web/pages.py` + `research_pipeline.html`）轮询 **`GET /api/v1/research/pipeline-status`** |
| 功能开关 | **`GET /api/v1/qlib/health`**（`ENABLE_QLIB` / `ENABLE_RD_AGENT`） |
| Qlib 数据与管线状态 | **`GET /api/v1/qlib/status`**；ingest、dump bin 等同文件内路由 |
| 单次 RD 实验进度与产物 | **`GET /api/v1/rd-agent/runs`**、**`/runs/<id>`**、**`/runs/<id>/artifacts`**；提交响应中含 `poll_url`、`artifacts_url` |
| 因子与持续监控 | 量化实验室：**`/api/factor/list`**、**`/api/factor/monitor`**（与 autopublish / IC 巡检合并逻辑见 `FactorCatalogService`） |
| 任务通知 | 成功后 **`_push_task_message`**（`rdagent_tasks.py`），任务中心可见「RD-Agent 因子循环完成」等 |

六分析师（LangGraph）侧可通过 **`get_research_pipeline_status`**、**`run_qlib_unified_backtest`**、**`get_qlib_factor_snapshot`** 等工具与上述数据衔接；页面注释亦指向 **`docs/qlib_rd_trifecta_playbook.md`**。

---

## 5. 前置条件（链路易断点）

- **RD-Agent**：`ENABLE_RD_AGENT` + 研究写权限 + Worker 或后台线程实际执行成功；
- **Qlib 门禁有意义**：`ENABLE_QLIB` 且管线侧已有可用数据（ingest、必要时 dump qlib_bin）；否则门禁可能跳过或 `ok=False`；
- **部分 API/页面**：需 **登录**；写操作需 **`require_research_write_role`**。
- **`ENABLE_CELERY=1` 且三研究开关全开**：长任务与 RD 提交走队列，**必须**有 **Redis + Celery Worker**；Qlib 仍为库、**无**单独 qlib 进程；Beat 仅定时场景需要。详见 **[RUN_STACK_DEPLOY.md §2](RUN_STACK_DEPLOY.md)**。

---

## 6. 相关文档与代码索引

| 主题 | 路径 |
|------|------|
| 路线图 | `docs/roadmap_qlib_rd_agent.md` |
| Celery Worker | `docs/CELERY_WORKER_DEPLOY.md` |
| 全栈启动 | `docs/RUN_STACK_DEPLOY.md` |
| Qlib 部署 | `docs/QLIB_DEPLOY.md` |
| RD 提交校验 | `app/infrastructure/rdagent/submission_validate.py` |
| 任务与门禁串联 | `app/tasks/rdagent_tasks.py`、`app/infrastructure/rdagent/qlib_gate.py` |
| API 注册 | `app/presentation/api/routes_v1_qlib_rd.py` |
| 研究快照 | `app/application/services/research_pipeline_snapshot.py` |

---

*文档版本：与当前主分支实现一致；若接口或环境变量变更，请以代码与 `roadmap_qlib_rd_agent.md` 为准。*
