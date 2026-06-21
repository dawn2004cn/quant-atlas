# 部署指南

> 来源：DEPLOYMENT_MATRIX.md, QLIB_DEPLOY.md, RUN_STACK_DEPLOY.md

## 部署环境类型

### 1. 本地开发最小集
适用场景：开发页面、API、权限、基础服务；跑单元测试。
- 依赖：Python + `requirements.txt` + SQLite
- 开关：`ENABLE_CELERY=0`, `ENABLE_QLIB=0`, `ENABLE_RD_AGENT=0`

### 2. 单机演示环境
适用场景：演示平台页面与主要 API，小规模数据体验。
- 依赖：Python + SQLite + 可选 Redis
- 能力：页面与 API 开启；若需异步体验，可启用 Celery + Redis

### 3. 完整研究环境
适用场景：量化研究、AI 研究流程、Qlib 数据管线、收盘后任务调度。
- 依赖：Python + Redis + Celery Worker/Beat + SQLite/MySQL + Qlib + LLM 配置
- 开关：`ENABLE_CELERY=1`, `ENABLE_QLIB=1`, `ENABLE_RD_AGENT=1`

### 4. 稳定生产环境
适用场景：长期运行的页面/API 服务、定时扫描、归档、收盘任务。
- 依赖：Python + Redis + Celery Worker/Beat + MySQL + Nginx + 日志采集
- 原则：后台任务以 Celery 为主；线程调度仅作为开发兜底

## 安装与启动

### 安装依赖
```bash
cd <项目根目录>
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
# 可选 Qlib：
pip install -r requirements-qlib.txt
```

### 启动 Web
```bash
export FLASK_SECRET_KEY=your-long-random-secret
python run.py
```
默认监听 `0.0.0.0:5000`，`threaded=True`。

### 生产环境建议
- 使用 gunicorn/waitress/uwsgi 托管 `app:create_app()`，前置 Nginx 做 TLS
- 关闭调试：`FLASK_DEBUG=0`
- 配置反向代理超时，避免长耗时 AI 或回测被网关过早断开

### Redis
```bash
redis-server
```
默认 `redis://localhost:6379/0`，可通过 `CELERY_BROKER_URL` 等覆盖。

### Celery Worker 与 Beat
```bash
python -m celery -A app.celery_app:celery worker -l info -P solo
python -m celery -A app.celery_app:celery beat -l info
```

**与进程内调度并存时注意：**
- 使用 Beat 跑龙虎榜等时，建议 `ENABLE_BASIC_DATA_SCHEDULER=0`
- 使用 Celery 跑扫描时：`ENABLE_CELERY=1`，且通常不设 `SCANNER_FORCE_THREADS=1`

### Qlib 与数据目录
- 安装：`pip install -r requirements-qlib.txt`
- 启用：`ENABLE_QLIB=1`
- 数据产物多在 `instance/qlib_export`、`qlib_bin` 及 meta JSON
- 夜间增量：`QLIB_CELERY_BEAT=1`

### 通达信
- 设置环境变量 `TDX_ROOT_PATH` 为通达信安装根目录
- 可选安装 pytdx 以支持部分扩展读取

### RD-Agent / 因子实验
- `ENABLE_RD_AGENT=1` 开启相关 API 与能力

## 环境变量参考

| 变量 | 含义 |
|------|------|
| `FLASK_SECRET_KEY` | Session 密钥，生产必填 |
| `FLASK_DEBUG` | `1` 开启调试 |
| `QUANT_DATABASE_URI` | SQLAlchemy/SQLite URI |
| `TDX_ROOT_PATH` | 通达信根目录 |
| `ENABLE_QLIB` | 是否启用 Qlib |
| `ENABLE_RD_AGENT` | RD-Agent 研究扩展 |
| `ENABLE_CELERY` | Celery 集成总开关 |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Celery 消息与结果后端 |
| `QLIB_CELERY_BEAT` | `1` 启用夜间 Qlib 增量管线 |
| `DATA_BACKFILL_BEAT` | `1` 启用无存量时的回填调度 |
| `FACTOR_IC_CELERY_BEAT` / `FACTOR_IC_WARN` | 因子 IC 监控定时与阈值 |
| `ENABLE_API_LEGACY_RESPONSE_FIELDS` | API 兼容旧字段 |

## 能力依赖关系

### Celery
启用后可承担：市场扫描、新闻归档、Qlib 增量任务、投资经理收盘任务。
依赖：Redis broker/result backend。

### Qlib
适用于：因子与模型研究、数据导入导出、预测与实验。
额外依赖：`requirements-qlib.txt`、本地数据目录与导出目录。

### RD-Agent
适用于：因子生成、因子监控、AI 研究增强。
额外依赖：LLM 配置、任务调度环境。

## 推荐落地原则
- 开发环境先求轻量，默认关闭重能力
- 研究环境再逐步开启 Qlib、RD-Agent 与调度能力
- 生产环境避免"线程调度 + Celery 调度"混跑
- 新增部署模式时，优先先补文档再补脚本

---
*文档生成基于当前仓库代码结构整理；如有出入以源码为准。*
