# Celery Worker 部署（含 Qlib 增量 / ingest / dump_bin）

本文说明如何单独（或与 Web 同机）部署 **Celery Worker**，以执行 **`qlib_incremental_pipeline`**（通达信等多源 → `qlib_export` CSV → `qlib_bin`）、**`qlib_full_backfill_if_empty`** 等任务；并说明 **Beat**、环境变量与触发方式。数据路径与 Qlib 配置见 **[QLIB_DEPLOY.md](QLIB_DEPLOY.md)**。  
**Web + Worker + Beat 与 Qlib/RD 开关的对照表**：**[RUN_STACK_DEPLOY.md](RUN_STACK_DEPLOY.md)**。

---

## 1. Worker 与 Web 的关系

| 组件 | 职责 |
|------|------|
| **Flask（`run.py`）** | HTTP API；`POST /api/v1/qlib/ingest`、`/qlib/update_all` 等可在 **`ENABLE_CELERY=1`** 时将长任务 **投递到 Redis**，由 Worker 执行。 |
| **Celery Worker** | 消费 broker 队列，执行 `app.tasks.*` 中注册的任务（含 `qlib_incremental_pipeline`）。 |
| **Celery Beat**（可选） | 按 crontab 投递定时任务；Qlib 夜间增量需 **`QLIB_CELERY_BEAT=1`**。 |

Worker 与 Web **必须**使用：

- **同一套代码与虚拟环境**（或等价镜像），保证 `app`、`config/`、`instance/` 路径一致。
- **相同的 `CELERY_BROKER_URL`（及建议相同的 `CELERY_RESULT_BACKEND`）**。
- **相同的项目根目录作为工作目录**（或保证 `BASE_DIR`/`instance` 解析到同一磁盘上的数据），否则 ingest 写到别处，Web 读不到。

---

## 2. 前置条件

1. **Redis**（或兼容 broker）已启动，且网络可达。  
2. 已安装依赖：

```bash
pip install -r requirements.txt
pip install -r requirements-qlib.txt   # 需要 dump_bin / qlib_bin 时必装
```

3. 若管线要合并通达信：**在 Worker 进程环境中设置 `TDX_ROOT_PATH`**（与 Web 一致）。  
4. Qlib 元数据里已有标的列表：**至少成功过一次 `POST /api/v1/qlib/ingest`**，使 `config/qlib_pipeline_meta.json` 带有 `instruments`；否则 `update_all_data` 会因无标的返回 `no_symbols`（见 `app/tasks/qlib_data_update.py`）。

---

## 3. 环境变量（Worker 侧）

Worker 进程需能读到与业务一致的环境（ systemd `EnvironmentFile`、Docker `env_file`、`.env` 等）。

| 变量 | 说明                                                     |
|------|--------------------------------------------------------|
| `CELERY_BROKER_URL` | 必填，例：`redis://192.168.8.103:6380/0`                              |
| `CELERY_RESULT_BACKEND` | 建议与 broker 一致或独立 Redis DB，例：`redis://192.168.8.103:6380/1`                              |
| `ENABLE_QLIB=1` | 若任务内部或下游逻辑依赖该开关，与 Web 对齐。                              |
| `TDX_ROOT_PATH` | 可选；增量 ingest 合并本地日线时使用。                                |
| `TASK_MESSAGE_REDIS_URL` | 可选；与 Web 一致时，任务事件写入同一 Redis 列表，消息中心可展示。                |

**仅当希望从浏览器「异步触发」`POST /api/v1/qlib/update_all` 时**，Web 侧还需：

| 变量 | 说明 |
|------|------|
| `ENABLE_CELERY=1` | API 默认走 `qlib_incremental_pipeline.delay(...)`；否则在 Web 进程内 **同步** 执行 `update_all_data`（见 `routes_v1_qlib_rd.py`）。 |

**定时跑 Qlib 增量（Beat）**：

| 变量 | 说明 |
|------|------|
| `QLIB_CELERY_BEAT=1` | 在 **运行 Beat 的进程** 所在环境开启；调度名 `qlib-tdx-incremental-nightly`（默认约每日 **02:40**，上海时区），见 `app/celery_app.py`。 |

**定时跑 A 股 TDX 日 K 入库（Beat，生产推荐）**：

| 变量 | 说明 |
|------|------|
| `TDX_DAYK_CELERY_BEAT=1` | 启用收盘后主链：默认 **16:05** `scheduled_cn_history_daily`（TDX → **Timescale + CSV → qlib_bin**）。 |
| `TDX_USE_SCHEDULED_DAILY_CHAIN` | 默认 `1`：一键日更；`0` 时拆成增量 + `csv_to_qlib_incremental_sync`。 |
| `TDX_DAYK_BEAT_HOUR` / `TDX_DAYK_BEAT_MINUTE` | 默认 `16` / `5`。 |
| `TDX_DAYK_QLIB_BIN_BEAT_MINUTE` | 默认 `25`（仅拆分链：CSV→bin 时刻，应晚于增量）。 |
| `TDX_SYNC_ENABLE_MYSQL` | 默认 `0`：历史入库不写 MySQL。 |
| `TDX_SYNC_ENABLE_TIMESCALE` | 默认 `1`：写 Timescale。 |
| `TIMESCALE_TDX_SYNC_BEAT` | 仅当 **未** 开 `TDX_DAYK_CELERY_BEAT` 时注册独立 Timescale Beat。 |

与 `QLIB_CELERY_BEAT=1` 同时开启时：若已开 TDX 日更，Beat **不再**注册 16:10 的重复 CSV→bin（由日更主链承担）；夜间仍有 `qlib-tdx-incremental-nightly`（02:40）。

QuestDB / ClickHouse **入库 Beat 已下线**（`QUESTDB_SYNC_BEAT` 无效）。

---

## 4. 启动 Worker

在项目根目录执行（与 `run.py` 同级）：

**Linux / macOS**

```bash
export CELERY_BROKER_URL=redis://192.168.8.103:6380/0
export CELERY_RESULT_BACKEND=redis://192.168.8.103:6380/1
cd /path/to/quant-atlas
celery -A app.celery_app:celery worker -l info
```

**Windows**（单进程避免多进程问题，常用）：

```powershell
$env:CELERY_BROKER_URL = "redis://192.168.8.103:6380/0"
$env:CELERY_RESULT_BACKEND = "redis://192.168.8.103:6380/1"
cd E:\path\to\quant-atlas
celery -A app.celery_app:celery worker -l info -P solo
```

说明：

- `-A app.celery_app:celery` 与仓库入口一致。  
- 模块加载时会 `import` 各 `app.tasks.*`（含 `qlib_data_update`、`rdagent_tasks` 等），任务名与 **消息中心** `task_label` 映射一致。  
- 生产可增加 **并发数**、**专用队列**（若你后续在任务上绑定了 `queue=`，需 `worker -Q` 对应队列；当前默认队列为 `celery`）。

---

## 5. 启动 Beat（可选，定时 Qlib）

在 **另一终端或另一台机器**（仅一台 Beat 实例，避免重复调度）：

```bash
export CELERY_BROKER_URL=redis://192.168.8.103:6380/0
export QLIB_CELERY_BEAT=1
cd /path/to/quant-atlas
celery -A app.celery_app:celery beat -l info
```

`QLIB_CELERY_BEAT=0`（默认）时，Beat 配置里 **不包含** `qlib_incremental_pipeline` 条目。

其他常见 Beat 开关（同一 `celery_app.py`）：`SCANNER_CELERY_BEAT`、`DATA_BACKFILL_BEAT`、`FACTOR_IC_CELERY_BEAT` 等，按需在同一 Beat 进程中开启。

---

## 6. 与历史 K 线 / Qlib 相关的已注册任务

| 任务名 | 模块 | 作用 |
|--------|------|------|
| `app.tasks.data_backfill_tasks.scheduled_cn_history_daily` | `data_backfill_tasks` | **【推荐日更】** TDX → Timescale + CSV → qlib_bin。 |
| `app.tasks.data_backfill_tasks.sync_incremental_tdx` | `data_backfill_tasks` | 增量 TDX → Timescale/CSV（可选 dump bin）。 |
| `app.tasks.data_backfill_tasks.backfill_all_history_tdx` | `data_backfill_tasks` | 全量 TDX → Timescale/CSV/bin。 |
| `app.tasks.qlib_data_update.csv_to_qlib_incremental_sync` | `qlib_data_update` | CSV → qlib_bin；拆分链 Beat 使用。 |
| `app.tasks.qlib_data_update.mysql_to_qlib_incremental_sync` | `qlib_data_update` | **兼容 shim** → 同上 CSV→bin（勿再当 MySQL 路径）。 |
| `app.tasks.qlib_data_update.qlib_incremental_pipeline` | `qlib_data_update` | **ingest（merge）+ `dump_to_qlib_bin`**，多源；夜间 02:40。 |
| `app.tasks.qlib_data_update.qlib_full_backfill_if_empty` | `qlib_data_update` | 无 CSV 时全量种子 K 线 + bin；已有 CSV 则跳过。 |
| `app.tasks.data_backfill_tasks.backfill_qlib_kline_if_empty` | `data_backfill_tasks` | 与上类似链路的一部分（见 `DATA_BACKFILL_BEAT`）。 |
| `app.tasks.tdx_timescale_sync_tasks.tdx_timescale_sync_tick` | `tdx_timescale_sync_tasks` | 仅 Timescale（无 TDX 日更主链时）。 |
| `app.tasks.tdx_dayk_tasks.tdx_dayk_*` | `tdx_dayk_tasks` | **兼容别名**；新调度请用上表 `data_backfill_tasks`。 |

读写全流程见 **[HISTORY_DATA_READ_WRITE_FLOW.md](HISTORY_DATA_READ_WRITE_FLOW.md)**。

**说明**：`POST /api/v1/qlib/ingest` 默认在 **Web 进程内同步**写 CSV；**一键增量 ingest+dump** 推荐通过 **`qlib_incremental_pipeline`**（Beat 或 `update_all` API）在 **Worker** 上跑，避免阻塞 WSGI。

---

## 7. 手动触发（不经过 Beat）

**方式 A：Celery CLI**

```bash
cd /path/to/quant-atlas
celery -A app.celery_app:celery call app.tasks.qlib_data_update.qlib_incremental_pipeline \
  --kwargs='{"period":"2y","max_workers":8}'
```

**方式 B：HTTP（需登录 + 研究写权限）**

- `POST /api/v1/qlib/update_all`  
  - `ENABLE_QLIB=1`、`ENABLE_CELERY=1` 时默认 **异步** 投递 `qlib_incremental_pipeline`；`?sync=1` 强制在 **Web 进程同步**执行。

---

## 8. 验证

1. Worker 日志出现 `ready`、已注册 `app.tasks.qlib_data_update.qlib_incremental_pipeline`。  
2. 投递任务后 Redis 队列消费完毕，无 traceback。  
3. `GET /api/v1/qlib/status`：`csv_count`、`qlib_bin_ready` 符合预期。  
4. 若配置了 `TASK_MESSAGE_REDIS_URL` / broker，消息中心可见 `task_started` / `task_succeeded` 等事件。

---

## 9. 常见问题

| 现象 | 处理 |
|------|------|
| `ModuleNotFoundError: No module named 'ta'` | Worker 需与 Web 同一套依赖：执行 **`pip install ta==0.11.0`**（已写在 `requirements.txt`）；建议直接 **`pip install -r requirements.txt`**。新闻归档任务运行时才强依赖 `ta`；若仍未装，仅该任务会在执行时报错。 |
| `ModuleNotFoundError: No module named 'rdagent'` | **Worker 进程可以正常启动**（`rdagent` 已改为按需导入）；若 **`ENABLE_RD_AGENT=1`** 并要跑 **`rdagent.run_factor_generation`**，须安装官方包：**`pip install rdagent`**（及 LLM 等环境）。未安装时提交 RD 任务会在执行阶段返回失败/明确错误，而非在 import Celery 时崩溃。 |
| `no_symbols` | 先对目标股票列表执行一次 `POST /api/v1/qlib/ingest` 写入 meta。 |
| `dump` 失败 | 确认 Worker 已安装 `requirements-qlib.txt`；磁盘空间充足。 |
| Windows Worker 崩溃 | 使用 `-P solo`；或改用 WSL2/Linux Worker。 |
| Beat 与线程调度重复拉行情 | 见 `celery_app.py` 文档：`ENABLE_BASIC_DATA_SCHEDULER=0` 等与扫描相关的环境约定。 |

---

## 10. 相关文档

- [QLIB_DEPLOY.md](QLIB_DEPLOY.md) — Qlib 依赖、配置、ingest/dump、验收。  
- [DATA_FLOW.md](DATA_FLOW.md) — 数据流与回填任务。  
- [roadmap_qlib_rd_agent.md](roadmap_qlib_rd_agent.md) — API 速查与阶段说明。  
- `app/celery_app.py` — Beat 表与环境变量注释（源码为准）。
