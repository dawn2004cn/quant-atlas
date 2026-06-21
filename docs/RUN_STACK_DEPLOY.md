# Web + Celery Worker + Beat 运行栈部署（发挥 Qlib / RD-Agent）

本文说明如何**同时部署并启动**三条进程：**Flask Web**、**Celery Worker**、**Celery Beat**，使 **Qlib**（ingest / `qlib_bin` / 增量管线）与 **RD-Agent**（因子循环异步、产物、门禁、IC 巡检）在工程上衔接顺畅。若 **`ENABLE_CELERY`、`ENABLE_QLIB`、`ENABLE_RD_AGENT` 均为 `1`**，请先阅读 **§2**。细节拆分见 [QLIB_DEPLOY.md](QLIB_DEPLOY.md)、[CELERY_WORKER_DEPLOY.md](CELERY_WORKER_DEPLOY.md)；Beat 表以 `app/celery_app.py` 为准。

**配置来源**：与 Celery、行情历史、因子巡检等相关的**非敏感**开关与默认值可写在仓库根目录 `config/config.cfg` 的 `[app]` 段（UTF-8）；若某环境变量已设置且非空，则**覆盖**该键。`FLASK_SECRET_KEY`、`QUANT_DATABASE_URI`、`OPENAI_API_KEY`、`WECHAT_OPEN_APP_SECRET`、`LANGGRAPH_POSTGRES_URI` / `DATABASE_URL`、`RDAGENT_WEBHOOK_URL` 等仍仅从环境变量读取，逻辑见 `app/core/runtime_config.py`。

---

## 1. 三条进程各自做什么

| 进程 | 作用 |
|------|------|
| **Web（`python run.py`）** | HTTP API、页面、登录态；`ENABLE_QLIB=1` 时提供 ingest / factors / `update_all` 等；`ENABLE_RD_AGENT=1` 时提交 RD 任务到 broker；`configure_task_message_store` 读任务事件。 |
| **Celery Worker** | 执行队列中的长任务：`qlib_incremental_pipeline`（ingest+dump）、`rdagent.run_factor_generation`、`factor_ic_monitor_tick`、行情扫描、龙虎榜/研报等。 |
| **Celery Beat** | 按时间表 **投递**任务到 broker（自身不执行重计算）；需有至少一个 Worker 消费。 |

**最大效用的前提**：三者使用 **同一 Redis broker**、**同一项目目录与 `instance/` 数据**、**同一套虚拟环境与依赖**（含 `requirements-qlib.txt`、`rdagent` 若跑 RD）。

---

## 2. 当 `ENABLE_CELERY=1`、`ENABLE_QLIB=1`、`ENABLE_RD_AGENT=1` 时

三开关同时打开表示：**Web 侧开放 Qlib 与 RD-Agent 能力**，且**长任务与 RD-Agent 因子循环默认走 Celery 队列**（`RDAgentRunService.submit_run` 在已配置 broker 且安装 `celery` 时对 `run_rdagent_factor_generation` 使用 `delay()`）。请按下表部署进程。

| 组件 | 是否必须单独启动 | 说明 |
|------|------------------|------|
| **Redis** | **是** | 作为 Celery `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`；任务消息中心若启用，常与 broker 或 `TASK_MESSAGE_REDIS_URL` 一致。 |
| **Celery Worker** | **是** | 无 Worker 则队列任务（含 **`rdagent.run_factor_generation`**、`qlib_incremental_pipeline`、扫描、龙虎榜/研报等）**不会执行**；RD 提交会长期停留在已排队状态。 |
| **Flask Web（`python run.py`）** | **是** | HTTP API、页面、登录态与任务投递入口。 |
| **Celery Beat** | **否（按需）** | 仅当需要 **定时**（如 `QLIB_CELERY_BEAT`、`FACTOR_IC_CELERY_BEAT`、默认龙虎榜/研报、扫描等）时再启；不需要定时时可只靠 **API 手动触发** + Worker。 |
| **Qlib「服务」** | **否** | Qlib 为 **进程内 Python 库**，由 Web 或 Worker 在调用管线时加载；**无需**单独启动「qlib 守护进程」。仍需依赖 **`requirements-qlib.txt`**、`instance/qlib_bin` 与 `config/qlib_config*.yaml`（见 [QLIB_DEPLOY.md](QLIB_DEPLOY.md)）。 |

**最小可用组合（三开关均为 1）**：**Redis → Celery Worker → Flask Web**。需要无人值守定时时再增加 **Celery Beat**，并与下文 **§8** 及 `app/celery_app.py` 中的环境开关对齐。

**另须满足**（否则功能不可用或提交被拒）：Qlib 数据已 ingest / dump（`GET /api/v1/qlib/status` 可验）；RD-Agent 依赖与 LLM 等按官方说明配置；`POST /api/v1/rd-agent/runs` 需登录且具备研究写权限；`submission_validate` 要求 **`instance/qlib_bin`** 就绪时才能提交（详见 `app/infrastructure/rdagent/submission_validate.py`）。

---

## 3. 推荐启动顺序

1. **Redis** 先起。  
2. **Worker**（否则 Beat 投递的任务无人执行）。  
3. **Beat**（若需要定时；单机开发可暂时不启 Beat，改用手动 `delay` / API）。  
4. **Web**（依赖 Redis 时用于任务消息中心；纯页面可不连 broker，但 Qlib/RD 异步能力会受限）。

---

## 4. 环境变量：一套「研究全开」示例（Linux / bash）

下列为**示例**，生产请改密钥、Redis 地址，并按机器角色裁剪。

```bash
# --- 通用 ---
export FLASK_SECRET_KEY="your-secret"
export CELERY_BROKER_URL="redis://192.168.8.103:6380/0"
export CELERY_RESULT_BACKEND="redis://192.168.8.103:6380/0"
# 与 broker 一致即可让 Web 与 Worker 写入同一消息列表
export TASK_MESSAGE_REDIS_URL="redis://192.168.8.103:6380/0"

# --- Qlib ---
export ENABLE_QLIB=1
export TDX_ROOT_PATH="/path/to/tdx"   # 可选，合并本地日线

# --- RD-Agent ---
export ENABLE_RD_AGENT=1
# RD 依赖 LLM 等请按 rdagent 官方文档配置（此处不展开）

# --- Web：异步投递长任务（Qlib update_all、避免扫描占满 Web）---
export ENABLE_CELERY=1
export ENABLE_BACKGROUND_SCANNER=1
export SCANNER_FORCE_THREADS=0       # 与下述「避免重复」一致时：扫描走 Celery Beat

# --- 避免与 Celery Beat 重复拉基础数据 / 扫描 ---
export ENABLE_BASIC_DATA_SCHEDULER=0   # Beat 已跑龙虎榜/研报时建议关闭进程内调度
# 若坚持用进程内扫描线程：SCANNER_FORCE_THREADS=1 且 SCANNER_CELERY_BEAT=0

# --- Beat：按需开启（均为 0 则 Beat 仅保留默认龙虎榜+研报）---
export QLIB_CELERY_BEAT=1              # 每日 02:40 qlib_incremental_pipeline
export FACTOR_IC_CELERY_BEAT=1         # 每日 18:35 因子弱 IC 巡检（需 ENABLE_RD_AGENT）
export FACTOR_IC_AUTOPUBLISH_TAIL=80   # 可选：合并 autopublish.jsonl 尾部参与 IC 扫描
export DATA_BACKFILL_BEAT=0           # 按需：凌晨空库回填链
export FINANCIAL_DAILY_BEAT=0
export NEWS_ARCHIVE_BACKFILL_BEAT=0
# export SCANNER_CELERY_BEAT=0        # 若 SCANNER_FORCE_THREADS=1 时建议关 Beat 扫描
```

**Windows（PowerShell）**：用 `$env:NAME = "value"` 设置上述变量后，再分别开三个终端跑 Web / Worker / Beat。

---

## 5. 三条命令（项目根目录）

```bash
cd /path/to/quant-atlas
source .venv/bin/activate

# 终端 1 — Worker
celery -A app.celery_app:celery worker -l info

# 终端 2 — Beat（需上节 Beat 相关 export）
celery -A app.celery_app:celery beat -l info

# 终端 3 — Web
export ENABLE_QLIB=1
export ENABLE_RD_AGENT=1
export ENABLE_CELERY=1
python run.py
```

**Windows Worker** 建议：

```text
celery -A app.celery_app:celery worker -l info -P solo
```

---

## 6. 使 Qlib「尽量发挥作用」的检查清单

| 步骤 | 说明 |
|------|------|
| 依赖 | `pip install -r requirements.txt` 与 **`pip install -r requirements-qlib.txt`**（需要 `qlib_bin` / dump 时）。 |
| 配置 | `config/qlib_config.yaml` 或 `qlib_config.local.yaml` 中 `provider_uri` 指向 **`instance/qlib_bin`**。 |
| 首次标的 | 登录后 **`POST /api/v1/qlib/ingest`** 写入 `qlib_pipeline_meta.json` 与 CSV（否则增量任务 `no_symbols`）。 |
| 异步增量 | **`ENABLE_CELERY=1`** + Worker 常驻；用 **`POST /api/v1/qlib/update_all`** 或 **`QLIB_CELERY_BEAT=1`** 驱动 `qlib_incremental_pipeline`。 |
| 验证 | `GET /api/v1/qlib/status`：`csv_count`、`qlib_bin_ready`、`pyqlib_installed`；研究页 **`/api/v1/research/pipeline-status`**。 |

---

## 7. 使 RD-Agent「尽量发挥作用」的检查清单

| 步骤 | 说明 |
|------|------|
| 依赖 | `pip install rdagent` 及官方要求的 LLM / 环境变量。 |
| 开关 | **`ENABLE_RD_AGENT=1`**；提交接口需登录且具备研究写权限。 |
| 数据门禁 | **`instance/qlib_bin`** 已就绪（`calendars/day.txt` 等），否则 **`POST /api/v1/rd-agent/runs`** 会被校验拒绝（见 `submission_validate`）。 |
| 异步执行 | **Worker 必须运行**；`RDAgentRunService` 在配置了 broker 时对 `run_rdagent_factor_generation` 使用 **`delay()`**。 |
| 产物与监控 | 成功后注册表 + `qlib_gate` + **`autopublish.jsonl`**；可选 **`FACTOR_IC_CELERY_BEAT=1`** 与 **`FACTOR_IC_AUTOPUBLISH_TAIL`** 做弱 IC 告警。 |
| 回调 | 可选 **`RDAGENT_WEBHOOK_URL`** 接收完成通知。 |

---

## 8. Beat 开关与默认已注册任务（摘要）

| 环境变量 | 为 `1` 时的典型行为（上海时区） |
|----------|----------------------------------|
| （无） | Beat 仍包含 **龙虎榜 17:05**、**研报 06:05**（见 `celery_app.py`）。 |
| `SCANNER_CELERY_BEAT=1`（默认） | 核心池 **每 2 分钟**、全市场轮询 **每 15 分钟**。 |
| `QLIB_CELERY_BEAT=1` | 每日 **02:40** `qlib_incremental_pipeline`。 |
| `DATA_BACKFILL_BEAT=1` | 凌晨回填链（财报空表、龙虎榜空表、Qlib K 线空库等）。 |
| `FACTOR_IC_CELERY_BEAT=1` | 每日 **18:35** `factor_ic_monitor_tick`（需 `ENABLE_RD_AGENT=1`）。 |
| `FINANCIAL_DAILY_BEAT=1` | 每日 **07:30** 财报快照刷新。 |
| `NEWS_ARCHIVE_BACKFILL_BEAT=1` | 每周日 **03:10** 新闻归档批量刷新。 |

**避免重复打源站**：若 Beat 已跑龙虎榜/研报，请将 **`ENABLE_BASIC_DATA_SCHEDULER=0`**。若进程内 **`SCANNER_FORCE_THREADS=1`**，请将 **`SCANNER_CELERY_BEAT=0`**，避免与 Beat 扫描双开。

---

## 9. 分机部署时的注意点

- **Web** 与 **Worker** 挂载 **同一 `BASE_DIR`**（同一仓库克隆或共享存储上的 `instance/`、`config/`）。  
- 环境变量在三类进程中 **对齐**（至少 broker、`ENABLE_*`、`TDX_ROOT_PATH`）。  
- **Beat 只跑一份**（多实例会重复投递同一 crontab）。  
- 生产建议 **systemd / Docker Compose** 托管三条服务并设置 `Restart=always`。

---

## 10. 相关文档

| 文档 | 内容 |
|------|------|
| [QLIB_DEPLOY.md](QLIB_DEPLOY.md) | Qlib 依赖、`qlib.init`、ingest/dump、验收。 |
| [CELERY_WORKER_DEPLOY.md](CELERY_WORKER_DEPLOY.md) | Worker/Beat 命令、任务名、手动 `celery call`。 |
| [roadmap_qlib_rd_agent.md](roadmap_qlib_rd_agent.md) | API 速查与阶段路线。 |
| [DATA_FLOW.md](DATA_FLOW.md) | 数据本地优先与回填任务。 |
| [QLIB_RD_AGENT_ENHANCEMENT.md](QLIB_RD_AGENT_ENHANCEMENT.md) | 门禁、autopublish、IC 合并等增强说明。 |

---

*若你使用 Docker Compose，可将上述三个 `command` 写为三个 service 共用同一 `env_file` 与 `volumes` 挂载项目根目录。*
