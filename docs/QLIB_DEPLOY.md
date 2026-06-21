# Qlib 部署与启用指南（Quant Atlas）

本文描述在本仓库中 **安装依赖、配置、准备数据、验证与 Celery 定时** 的步骤，与 [roadmap_qlib_rd_agent.md](roadmap_qlib_rd_agent.md)、[DATA_FLOW.md](DATA_FLOW.md) 一致。  
**与 Web、Worker、Beat 一起怎么开**：优先阅读 **[RUN_STACK_DEPLOY.md](RUN_STACK_DEPLOY.md)**。

---

## 1. 运行环境与建议

| 项 | 建议 |
|----|------|
| 操作系统 | **Linux**、**WSL2** 或 **Docker**；纯 Windows 上 pyqlib 安装/运行易踩坑，重计算尽量放在 Linux 子环境或独立 Worker 节点。 |
| Python | 与主项目 `requirements.txt` 一致（建议 3.10+）。 |
| 机器 | **不必须**单独机器；CPU/IO 压力大时，可将 **Celery Worker** 与 Web 分机部署，共用同一 `CELERY_BROKER_URL`。 |

---

## 2. 安装依赖

```bash
cd /path/to/quant-atlas
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate   # Linux / macOS

pip install -U pip
pip install -r requirements.txt
```

**可选：pyqlib（CSV → `qlib_bin`、读 bin 回测等）**

```bash
pip install -r requirements-qlib.txt
```

说明（详见仓库根目录 `requirements-qlib.txt`）：

- **ingest 写 `instance/qlib_export/*.csv`、示例因子、部分回测路径**：可不装 pyqlib，仅设 `ENABLE_QLIB=1` 即可使用部分能力。
- **`dump_to_qlib_bin`、`qlib_bin_ready`、RD-Agent 默认 `provider_uri`**：需要安装 **pyqlib**。

---

## 3. 配置文件

| 文件 | 作用 |
|------|------|
| `config/qlib_config.yaml` | 默认：`provider_uri: instance/qlib_bin`，`region: cn`，扩展块 `quant_atlas.benchmark` 等。 |
| `config/qlib_config.local.yaml` | 本机覆盖（勿提交密钥）；与默认文件合并加载顺序见 `qlib_config.yaml` 文件头注释。 |
| `TDX_ROOT_PATH`（环境变量） | 可选；ingest 时可与 AkShare 合并通达信本地日线。 |

元数据与导出目录（运行时生成/更新）：

- `instance/qlib_export/*.csv` — ingest 输出。
- `instance/qlib_bin/` — `dump_to_qlib_bin` 后的 Qlib 二进制数据目录（与 `provider_uri` 对齐）。
- `config/qlib_pipeline_meta.json` — 标的列表等管线元数据（ingest 写入）。

---

## 4. 环境变量（最小集）

| 变量 | 说明 |
|------|------|
| `ENABLE_QLIB=1` | 打开 Qlib 相关 HTTP API（ingest、factors、统一回测等）。 |
| `FLASK_SECRET_KEY` | 生产必填；调用需登录的 API 前先完成登录。 |
| `CELERY_BROKER_URL` | 使用 Celery 跑 `qlib_incremental_pipeline` 等任务时配置（如 `redis://localhost:6379/0`）。 |

**可选（定时）**

- `QLIB_CELERY_BEAT=1`：每日约 **02:40** 跑 `qlib_incremental_pipeline`（见 `app/celery_app.py` 注释）。
- `DATA_BACKFILL_BEAT=1`：与空库种子 K 线等回填任务联动（见 [DATA_FLOW.md](DATA_FLOW.md)）。

---

## 5. 启动 Web（Qlib 预热）

```bash
# Linux / macOS
export ENABLE_QLIB=1
python run.py
```

应用工厂在 `warm_runtime_extensions` 中，若 `enable_qlib` 为真，会调用 `QlibService.init_qlib()` 读取上述 YAML。预热失败会写入 `RUNTIME_WARMUP["qlib_warmup"]`，**不阻塞**整站启动；请查看日志排查 pyqlib/路径问题。

---

## 6. 准备数据（推荐顺序）

### 6.1 Ingest → CSV

登录后调用：

- `POST /api/v1/qlib/ingest`  
  - JSON 示例见 [roadmap_qlib_rd_agent.md](roadmap_qlib_rd_agent.md) 阶段 1 API 速查（`symbols`、`market`、`period`、`merge_existing` 等）。

### 6.2 Dump → qlib_bin（需 pyqlib）

- 在 ingest 请求体中设置 `dump_bin: true`（及可选 `dump_bin_max_workers`），或调用管线中的 `dump_to_qlib_bin`（与 Celery 任务 `qlib_incremental_pipeline` 行为一致，详见 [DATA_FLOW.md](DATA_FLOW.md)）。

### 6.3 自检

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/qlib/health` | 开关探测，无需登录。 |
| GET | `/api/v1/qlib/status` | `csv_count`、`qlib_bin_ready`、`pyqlib_installed` 等。 |
| GET | `/api/v1/qlib/factors?symbol=600519&market=CN` | 需登录、`ENABLE_QLIB=1`。 |

---

## 7. Celery Worker / Beat（可选）

**完整步骤（环境变量、任务列表、手动 call、排错）见 [CELERY_WORKER_DEPLOY.md](CELERY_WORKER_DEPLOY.md)。**

最小示例：

```bash
export CELERY_BROKER_URL=redis://192.168.8.103:6380/0
export ENABLE_QLIB=1
export QLIB_CELERY_BEAT=1    # 仅在运行 Beat 的进程上开启

python -m celery -A app.celery_app:celery worker -l info -P solo   # Windows 常用 -P solo
python -m celery -A app.celery_app:celery beat -l info
```

Worker 可与 Web **同机或分机**，只要 broker 与 **`instance/` 数据路径** 一致即可。

---

## 8. 与 RD-Agent 的关系

- RD-Agent 因子循环默认 `provider_uri` 为 **`instance/qlib_bin`**（见 `app/infrastructure/rdagent/rdagent_factor_loop.py`）。
- 提交任务前平台会做 **数据目录校验**（`submission_validate`）：默认 bin 路径需存在有效 `calendars/day.txt` 等；详见 [QLIB_RD_AGENT_ENHANCEMENT.md](QLIB_RD_AGENT_ENHANCEMENT.md)。
- 另需：`ENABLE_RD_AGENT=1`、`pip install rdagent` 及 LLM 等上游配置（不在本文展开）。

---

## 9. 验收清单

- [ ] `GET /api/v1/qlib/status` 中 `csv_count > 0`（已完成 ingest）。
- [ ] 若已装 pyqlib 且 dump 成功：`qlib_bin_ready == true`。
- [ ] 登录后 `GET /api/v1/qlib/factors` 返回预期序列。
- [ ] （可选）`POST /api/v1/qlib/backtest` 或统一回测接口返回 metrics。
- [ ] （可选）Celery：`qlib_incremental_pipeline` 在 Worker 中执行成功。

---

## 10. 相关文档

- [CELERY_WORKER_DEPLOY.md](CELERY_WORKER_DEPLOY.md) — Celery Worker/Beat、`qlib_incremental_pipeline` 与触发方式。
- [roadmap_qlib_rd_agent.md](roadmap_qlib_rd_agent.md) — 阶段划分与 API 速查。
- [DATA_FLOW.md](DATA_FLOW.md) — 本地优先与 Qlib 数据流。
- [QLIB_RD_AGENT_ENHANCEMENT.md](QLIB_RD_AGENT_ENHANCEMENT.md) — 增强与门禁说明。

---

*维护：配置项或 API 变更时请同步更新本文与路线图。*
