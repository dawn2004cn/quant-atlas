# 01 · 产品与系统概览

## 定位

**Quant Atlas** 是面向零售与专业投研的量化研究与交易平台（模块化单体）：

- 多市场行情与研究数据接入（A 股 / 港股 / 美股等）
- 回测、因子、策略与组合风控
- 多智能体研究（LangGraph）与证据链
- Web 管理端（经典 Jinja）与现代 SPA（`/app`）

一句话：**中国市场深度的 AI 投研操作系统骨架** — 研究 → 因子 → 策略 → 回测 → 风控 → 执行 → 复盘。

## 能力地图（对外可陈述）

| 层 | 能力 |
|----|------|
| Research | 研究流水线、Notebook/Agent 相关能力、Qlib / RD-Agent 集成路径 |
| Alpha | 因子仓库、归因、Marketplace（若开启特性开关） |
| Strategy | 回测、选股、优化、策略快照 |
| Execution | 预检、Paper / 券商网关适配（以部署配置为准） |
| Control | 健康检查、任务中心、告警、Persona / 特性开关 |

## 市场覆盖

- A 股（`.SH` / `.SZ`）、港股（`.HK`）、美股；数据源含 TDX、yfinance、AkShare 等（可用性取决于环境配置）

## 明确不做（产品边界）

对外沟通时请避免承诺：

- 自建封闭行情云（聚宽式数据独占）
- 全量 Rust 重写交易内核
- DEX 做市作为主线产品
- 未开启特性开关的实验页面为「生产 SLA」

## 技术栈（当前）

| 层 | 技术 |
|----|------|
| 语言 | Python ≥ 3.11 |
| Web | Flask、Flask-Login；前端 SPA（React + Vite，路径 `/app`）+ 经典模板 |
| 数据 | SQLAlchemy、MySQL/SQLite、Redis、Pandas |
| 任务 | Celery（可选） |
| AI | LangGraph / LangChain 生态 |
| 质量 | Ruff、Mypy、Pytest |

## 下一步

- 开发者：[快速开始](./03-getting-started.md)
- 架构：[架构说明](./02-architecture.md)
- 接入：[API](./04-api.md)
