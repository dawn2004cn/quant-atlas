# Qlib + RD-Agent 引入路线图（quant-atlas）

**文档版本：v4**（2026-04-11：阶段 3 预测/选股数据源切换；`get_qlib_factor_snapshot` 工具；全局 `ValidationError` 处理。）  
**横向对照**：与《完整规划方案》逐条对照见 `docs/ROADMAP_FROM_CASE.md`（2026-04-12）。  
**发挥不足时的补短**：见 **[QLIB_RD_AGENT_ENHANCEMENT.md](QLIB_RD_AGENT_ENHANCEMENT.md)**（根因、分层清单、P0–P3、`qlib_gate` 演进）。  
**部署与启用**：见 **[QLIB_DEPLOY.md](QLIB_DEPLOY.md)**（依赖、配置、ingest/dump、验收清单）；**Celery Worker/Beat** 见 **[CELERY_WORKER_DEPLOY.md](CELERY_WORKER_DEPLOY.md)**。  
**Web + Worker + Beat 一键对照（发挥 Qlib/RD）**：**[RUN_STACK_DEPLOY.md](RUN_STACK_DEPLOY.md)**（其中 **§2** 为 `ENABLE_CELERY` / `ENABLE_QLIB` / `ENABLE_RD_AGENT` **均为 `1`** 时的进程与边界说明）。

> **目标**：在**不破坏**现有 Flask 量化平台的前提下，逐步接入 **Qlib**（高性能因子与回测）与 **RD-Agent**（自动因子/模型研发），形成「数据统一 → 因子挖掘 → 模型预测 → 增强回测/选股」闭环。  
> **约束**：Flask 仍为后端核心；前端策略为复用 **TradingAgents-CN** 已有界面（主页、全景、自选股、回测、中长线选股、AI 研究报告、用户管理），与当前 Jinja 页面**分区共存**。  
> **推进方式**：按下方阶段顺序实施；每阶段完成后勾选「验收」并在文末「进度记录」登记日期与备注。

---

## 一、原则与边界

| 原则 | 说明 |
|------|------|
| 默认关闭 | 新能力由环境变量（如 `ENABLE_QLIB`、`ENABLE_RD_AGENT`）控制，未开启时代码路径与现网一致。 |
| 适配器优先 | Qlib/RD-Agent **不直接**绑死 TDX/SQLite；统一经「数据契约 + 适配层」从现有 `MarketDataAccess` / 历史 API 取数。 |
| 双轨回测 | 保留现有 `/api/v1/backtest` 与策略桥；Qlib 回测以**新路由**或 `source=qlib` 参数并行，结果字段尽量对齐便于前端复用图表。 |
| 长任务异步 | RD-Agent、大批量 ingest、训练等走 **worker**（线程池 / RQ / Celery / 独立容器），避免阻塞 Flask WSGI。 |
| 安全 | 内网或管理员接口触发 ingest；生产环境 API Key、模型产物路径权限最小化。 |

---

## 二、数据契约（内部标准，阶段 0 定稿）

与 Qlib 日频对齐的**最小字段**（可扩展）：

| 字段 | 说明 |
|------|------|
| `symbol` | 平台统一代码（与现有 `MarketCode` + 代码规则一致，映射表单独维护） |
| `date` | 交易日 `YYYY-MM-DD` |
| `open, high, low, close, volume` | 与现 K 线接口一致 |
| `adj_factor` | 可选；无则 Qlib 侧注明为不复权或后续补全 |

**映射**：在代码中单一模块维护「平台 symbol ↔ Qlib instrument」转换（如 `SH600519` / `600519` 等），避免散落。

---

## 三、阶段划分与任务清单

### 阶段 0：基线与开关（本仓库优先落地）

- [x] 新增 `docs/roadmap_qlib_rd_agent.md`（本文档）并与团队对齐阅读路径。
- [x] 在 `app/config.py` / 环境变量中增加 `ENABLE_QLIB`（默认 `0`）、`ENABLE_RD_AGENT`（默认 `0`）。
- [x] 新增占位包 `app/infrastructure/qlib/`（`__init__.py` 说明职责），**不**在默认启动路径 import 重型依赖。
- [x] 可选：`requirements-qlib.txt` 与主 `requirements.txt` 分离（占位说明，具体版本待阶段 1 定稿）。
- [x] `GET /api/v1/qlib/health` 返回当前开关与路线图路径（不加载 Qlib）。
- [x] `GET /api/v1/qlib/status`：导出目录、磁盘 CSV 列表、`pyqlib_installed` 探测、最近一次 ingest 元数据（`ENABLE_QLIB` 可为 0，只读状态仍可用）。
- [x] **前端策略决议（摘要）**：当前生产以 **本仓库 Jinja（Quant Atlas）** 为主；`TradingAgents-CN-lastest/` 为**参考实现与子项目**，不并入同一路由树。若需 CN SPA：将 `frontend/dist` 挂到 Flask `static/cn-app/` 或独立端口 + 反向代理；登录优先 **同域 Session Cookie**（与现 `/login` 一致），跨域再议 JWT。**详细排期归入阶段 4。**

**验收**：`ENABLE_QLIB=0` 时全量现有测试与手工冒烟通过；`/api/v1/qlib/health` 可访问且 `qlib_enabled`/`rd_agent_enabled` 与 env 一致。

---

### 阶段 1：Qlib 基础设施

- [x] 实现 `QlibDataAdapter`（`app/infrastructure/qlib/data_adapter.py`）：从 `MarketDataAccess` 拉取 OHLCV，规范为 `date/open/high/low/close/volume`；符号映射 `app/infrastructure/qlib/symbol_map.py`（`SH600519` / `SZ000001`）。
- [x] `POST /api/v1/qlib/ingest`（`@login_required`，`ENABLE_QLIB=1`）：同步写入 `instance/qlib_export/{INSTRUMENT}.csv` + `config/qlib_pipeline_meta.json`（旧部署 `instance/qlib_pipeline_meta.json` 可自动复制）。**待增强**：角色校验、异步队列、增量字段 `adj_factor`。
- [x] `GET /api/v1/qlib/status`：见阶段 0 勾选（与 health 互补，带磁盘与 meta）。
- [x] `GET /api/v1/qlib/factors`（登录，`ENABLE_QLIB=1`）：示例因子 **MA5**、**RET1**（JSON）；优先读已导出 CSV，否则实时拉 K 线。
- [x] `POST /api/v1/qlib/backtest`（登录，`ENABLE_QLIB=1`）：**买入持有** 简易引擎，`metrics` 字段与平台 `final_value/total_return/annual_return/max_drawdown/sharpe_ratio` 对齐；**非** pyqlib 回测。**待增强**：接入 `qlib` 官方回测或 Alpha 因子表达式。
- [x] 单元测试：`tests/test_qlib_pipeline.py`（映射、ingest 写盘、简易回测）。
- [x] `ENABLE_QLIB=0` 时 `POST /api/v1/qlib/ingest` 返回 400 + `validation_error`（`tests/test_api_qlib_gate.py`）；Flask 已注册 `register_api_error_handlers`。

**验收（当前）**：`ENABLE_QLIB=1` 下完成一次 ingest + factors + backtest；数值为管道试算，与 pyqlib 正式回测对比留待安装 `requirements-qlib.txt` 后。

**API 速查（需登录的操作请带 Session Cookie）**：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/qlib/health` | 开关，无需登录 |
| GET | `/api/v1/qlib/status` | 导出目录与 meta，无需登录 |
| POST | `/api/v1/qlib/ingest` | JSON `{"symbols":["600519"],"market":"CN","period":"2y"}`，需 `ENABLE_QLIB=1` |
| GET | `/api/v1/qlib/factors?symbol=600519&market=CN` | 示例因子序列 |
| POST | `/api/v1/qlib/backtest` | JSON `{"symbol":"600519","start":"2023-01-01","end":"2024-12-31","market":"CN"}` |
| GET | `/api/v1/predict/models` | 已注册模型列表（登录） |
| POST | `/api/v1/predict/scores` | JSON `{"symbols":["600519","000001"],"market":"CN","model_id":"default_momentum","horizon_days":20}` |
| POST | `/api/v1/long-term-select` | 增 `data_source` / `model_id` / `horizon_days`（登录） |

---

### 阶段 2：RD-Agent 编排

- [x] RD-Agent 以 **worker 进程/容器**（Celery + broker，或 Flask **后台线程**）运行；Flask 仅提交任务与查询状态。
- [x] `POST /api/v1/rd-agent/runs`：提交实验配置（`data_scope` / `budget` / `search_space` 或扁平字段 `provider_uri` / `market` / `loop_n`）。
- [x] `GET /api/v1/rd-agent/runs`：最近运行索引（注册表摘要）。
- [x] `GET /api/v1/rd-agent/runs/<id>`：状态、进度、`log_summary`（末轮观察/评价摘要）、`error_message`。
- [x] `GET /api/v1/rd-agent/runs/<id>/artifacts`：产出列表（因子公式、代码预览、qlib 指标片段、`artifact_id` / `version`）。
- [x] 产物注册目录：`config/rdagent_registry/runs/{run_id}.json` + `registry_index.json`（阶段 3 可由选股/回测服务读取；旧路径 `instance/rdagent_registry` 首次启动整目录迁移）。
- [x] Webhook（可选）：环境变量 `RDAGENT_WEBHOOK_URL`，任务成功注册产物后 `POST` JSON；轮询仍用 `GET .../runs/<id>`。

**验收**：预发需 `ENABLE_RD_AGENT=1`、配置 RD-Agent/LLM 与 Qlib 数据路径；一次「提交 → 完成 → `artifacts` 非空」在具备依赖的环境跑通。（SQLite 元数据表留待与阶段 3 统一建模。）

**API 速查（`ENABLE_RD_AGENT=1` + 登录）**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/rd-agent/runs` | JSON 示例：`{"data_scope":{"provider_uri":"...","market":"csi300"},"budget":{"max_loops":7}}` |
| GET | `/api/v1/rd-agent/runs?limit=50` | 最近运行注册摘要 |
| GET | `/api/v1/rd-agent/runs/<id>` | 状态、进度、`result`、`log_summary` |
| GET | `/api/v1/rd-agent/runs/<id>/artifacts` | 因子/代码产物与指标上下文 |
| POST | `/api/rdagent/run` | 兼容旧路径（扁平字段），同服务实例 |

---

### 阶段 3：预测与增强选股

- [x] `PredictionApplicationService` + `config/model_registry.json`（默认种子；旧部署 `instance/model_registry.json` 可自动迁移）；`GET /api/v1/predict/models`、`POST /api/v1/predict/scores`（截面打分，底层复用动量启发式，可换模型 id）。
- [x] `SelectionSourceService`：`POST /api/v1/long-term-select` 与 `POST /api/v1/selector/run` 支持 `data_source`：`legacy` | `qlib_factors` | `model_score`（默认 `legacy`）；Jinja 页「中长线选股」「选股中心」已增加数据源下拉框。
- [x] `quant_tools.get_qlib_factor_snapshot`：`ENABLE_QLIB=1` 且注入管道时返回 MA5/RET1/close 序列尾；六分析师图中 **Fundamental / Backtest Optimizer** 工具列表已挂载。

**验收**：`legacy` 行为与改造前一致；`qlib_factors` 需 `ENABLE_QLIB=1` 且已 ingest CSV；`model_score` 不强制 Qlib，依赖 legacy 预筛 + 截面排序。

---

### 阶段 4：TradingAgents-CN 前端集成

- [ ] 配置 CN 前端 `API_BASE` 指向本 Flask `/api/v1`（或网关统一前缀）。
- [ ] 静态资源挂载：例如 Flask `static` 子路径或 `Blueprint` 托管 `frontend/dist`。
- [ ] 与现有 Jinja 导航：明确哪些 URL 仍走模板、哪些跳转到 SPA（避免重复实现同一功能）。
- [ ] 登录态与 CORS：同域优先；跨域则显式 CORS + 凭证策略。

**验收**：CN 侧核心页能登录并调用现有行情/自选股/回测 API（或与 Qlib 新 API 联调清单一致）。

---

## 四、建议代码落点（与当前仓库对齐）

| 能力 | 建议路径 |
|------|-----------|
| 环境开关 | `app/config.py` → `AppSettings` |
| Qlib 适配与导出 | `app/infrastructure/qlib/`（`data_adapter.py`、`symbol_map.py`） |
| 管道编排（ingest / factors / stub backtest） | `app/application/services/qlib_pipeline_service.py` |
| RD-Agent 任务表/状态 | `app/infrastructure/repositories/` + SQLite 或现有 DB |
| HTTP API | `app/presentation/api/routes.py`（`/qlib/*`、`/rd-agent/*`） |
| RD-Agent 编排 | `app/application/services/rdagent_run_service.py`；产物 `app/infrastructure/rdagent/artifact_registry.py` |
| 应用服务门面 | 当前为 `qlib_pipeline_service.py`；后续可拆 `qlib_ingest_service` |

（具体文件名可在阶段 1 PR 中微调，但**避免**把 Qlib import 放进 `bootstrap.py` 顶层。）

---

## 五、风险与缓解

| 风险 | 缓解 |
|------|------|
| Qlib 在 Windows 上安装/运行困难 | 官方推荐 Linux/Docker；本机 Windows 仅跑 Flask，Qlib 在容器或 WSL2。 |
| 依赖冲突 | 独立 requirements/extra；CI 分 job（无 Qlib / 有 Qlib）。 |
| RD-Agent 耗资源 | 队列、并发上限、仅内网提交。 |
| 存储膨胀 | 保留周期、标的白名单、冷热分层。 |

---

## 六、立即执行的下一步（阶段 1 → 2 过渡）

1. **阶段 1b（可选 pyqlib）**：在容器或 WSL2 安装 `requirements-qlib.txt`；增加 `qlib.init` 配置项；ingest 后调用官方 `dump_bin` 或直接使用 Qlib 数据源 URI；将 `POST /qlib/backtest` 切换为可配置的 `source=stub|qlib`。  
2. ~~**阶段 2**~~：`/api/v1/rd-agent/*` 与注册表已落地；生产请配 Celery + Redis 与 `RDAGENT_WEBHOOK_URL`（可选）。  
3. ~~**阶段 0 收尾**~~：前端策略摘要已写入阶段 0 勾选说明；完整 SPA 挂载见阶段 4。  
4. 每完成一步，更新下方「进度记录」。

---

## 七、进度记录（执行时填写）

| 日期 | 阶段 | 说明 |
|------|------|------|
| 2026-04-11 | 0 | 路线图落盘；`ENABLE_QLIB`/`ENABLE_RD_AGENT`、`AppSettings`、占位包 `app/infrastructure/qlib/`、`requirements-qlib.txt`、`GET /api/v1/qlib/health`。 |
| 2026-04-11 | 1 | `QlibDataAdapter`、`QlibPipelineService`、`GET/POST /api/v1/qlib/status|ingest|factors|backtest`（ingest/factors/backtest 需 `ENABLE_QLIB=1` + 登录）；导出 `instance/qlib_export/*.csv`；`tests/test_qlib_pipeline.py`。 |
| 2026-04-11 | 0 | 前端策略摘要：Jinja 为主、TA-CN 子目录参考；同域 Session 优先（见阶段 0 条目）。 |
| （待填） | 1b | pyqlib 安装与正式 dump / 回测切换 |
| 2026-04-11 | 2 | `RDAgentRunService`；`POST/GET /api/v1/rd-agent/runs`、`GET .../artifacts`；`config/rdagent_registry/*`；任务 JSON 在 `config/rdagent_jobs/*.json`；兼容 `/api/rdagent/run`；`RDAGENT_WEBHOOK_URL` 可选回调。 |
| 2026-04-11 | 3 | `predict/models`、`predict/scores`；`data_source` 切换；`QlibPipelineService.cross_section_factor_rank`；`get_qlib_factor_snapshot`；`register_api_error_handlers`。 |
| （待填） | 4 | |
| 2026-04-12 | 增强 | RD 提交校验、qlib_gate benchmark + ``factor_expression_gate``、autopublish.jsonl、``GET /api/factor/autopublish``、研究快照 ``recent_qlib_gate``、IC 巡检可选 ``FACTOR_IC_AUTOPUBLISH_TAIL`` / ``autopublish_tail`` 查询参数。 |

---

*变更摘要：v4 阶段 3 预测/选股数据源与 Qlib 因子工具；v3 阶段 2 RD-Agent；v2 阶段 1 管道；v1 初始。*
