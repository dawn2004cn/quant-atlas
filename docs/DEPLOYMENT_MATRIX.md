# 部署矩阵

## 目标

项目支持的能力很多，但并不是所有环境都需要完整依赖。下面用矩阵方式给出推荐组合，方便快速选择部署模式。

## 环境类型

### 1. 本地开发最小集

适用场景：

- 开发页面、API、权限、基础服务
- 跑单元测试和大部分集成测试

推荐依赖：

- Python
- `requirements.txt`
- SQLite

可关闭能力：

- Celery
- Redis
- MySQL
- Qlib
- RD-Agent

建议开关：

- `ENABLE_CELERY=0`
- `ENABLE_QLIB=0`
- `ENABLE_RD_AGENT=0`

### 2. 单机演示环境

适用场景：

- 演示平台页面与主要 API
- 小规模数据体验

推荐依赖：

- Python
- SQLite
- 可选 Redis

建议能力：

- 页面与 API 开启
- 若需要异步体验，可启用 Celery + Redis

### 3. 完整研究环境

适用场景：

- 量化研究
- AI 研究流程
- Qlib 数据管线
- 收盘后任务调度

推荐依赖：

- Python
- Redis
- Celery Worker / Beat
- SQLite 或 MySQL
- Qlib 相关依赖
- 对应的大模型与研究配置

建议能力：

- `ENABLE_CELERY=1`
- `ENABLE_QLIB=1`
- `ENABLE_RD_AGENT=1`

### 4. 稳定生产环境

适用场景：

- 长期运行的页面/API 服务
- 定时扫描、归档、收盘任务

推荐依赖：

- Python
- Redis
- Celery Worker / Beat
- MySQL 优先
- 反向代理与日志采集

建议原则：

- 后台任务以 Celery 为主
- 线程调度仅作为开发兜底，不作为生产主路径
- 关键配置显式化，不依赖默认值

## 能力依赖关系

### Celery

启用后可承担：

- 市场扫描
- 新闻归档
- Qlib 增量任务
- 投资经理收盘任务

依赖：

- Redis broker/result backend

### Qlib

适用于：

- 因子与模型研究
- Qlib 数据导入导出
- 预测与实验功能

额外依赖：

- `requirements-qlib.txt`
- 本地数据目录与导出目录

### RD-Agent

适用于：

- 因子生成
- 因子监控
- AI 研究增强

额外依赖：

- LLM 配置
- 任务调度环境

## 推荐落地原则

- 开发环境先求轻量，默认关闭重能力。
- 研究环境再逐步开启 Qlib、RD-Agent 与调度能力。
- 生产环境避免“线程调度 + Celery 调度”混跑。
- 新增部署模式时，优先先补文档再补脚本。

