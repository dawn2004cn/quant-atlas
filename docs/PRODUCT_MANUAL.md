# Quant Atlas 产品手册

> 整合来源：QUANT_ATLAS_PRODUCT_DOCUMENTATION.md, PART2, PART3, APPENDIX, QUANT_ATLAS_平台手册.md
> 生成时间：2026-06-13

---

## 目录

1. [产品概述与核心价值](#1-产品概述与核心价值)
2. [核心功能详解](#2-核心功能详解)
3. [系统架构](#3-系统架构)
4. [用户手册](#4-用户手册)
5. [部署指南](#5-部署指南)
6. [API 参考](#6-api-参考)
7. [数据字典](#7-数据字典)
8. [安全与合规](#8-安全与合规)
9. [性能优化](#9-性能优化)
10. [故障排查](#10-故障排查)
11. [术语表](#11-术语表)
12. [FAQ](#12-faq)

---

## 1. 产品概述与核心价值

### 1.1 产品概述

Quant Atlas（量子图谱）是一款**工业级全栈智能量化投资平台**，为量化研究员、基金经理、个人投资者和科技创业者提供从市场数据分析、因子挖掘、策略研发、回测验证到模拟交易的**端到端闭环能力**。

平台深度融合 AI、大语言模型、多智能体系统与传统量化方法论，构建**人机协同**的新型投资研究范式。

### 1.2 核心价值主张

| 主张 | 说明 |
|------|------|
| **全链路自动化** | 从数据获取→因子挖掘→策略构建→回测→信号生成→模拟交易全流程自动化，人力需求降低80% |
| **AI原生架构** | 100+ AI Agents，支持自然语言策略生成、研究报告自动解读、情绪监控 |
| **工业化可扩展** | 六边形架构 + SOLID 原则，支持分布式部署、Celery 异步调度、MySQL 持久化 |
| **零门槛体验** | 自然语言描述策略，AI 自动生成 Python 代码；智能选股、投资者教育 |

### 1.3 目标用户

| 用户类型 | 痛点 | 解决方案 |
|---------|------|---------|
| 量化研究员 | 因子挖掘效率低、回测搭建耗时 | RD-Agent 自动因子挖掘、Qlib 一体化回测 |
| 基金经理 | 研究覆盖不足、风控手段单一 | 多 AI Agent 委员会、实时风险监控 |
| 个人投资者 | 缺乏专业工具、选股效率低 | 智能选股、信号旗观察、哨兵预警 |
| 科技创业者 | 无量化背景 | NL 策略生成、ETF 智能配置、一键跟投 |

---

## 2. 核心功能详解

### 2.1 智能投资研究中枢

#### AI 投资委员会（多 Agent 辩论系统）

6 个专业化 Agent 多维度分析：
- **巴菲特 Agent**：基本面价值派
- **彼得·林奇 Agent**：成长投资派
- **卡尔·伍德 Agent**：宏观主题派
- **风控 Agent**：风险管理派
- **情绪 Agent**：舆情分析派
- **新闻 Agent**：事件驱动派

技术实现：LangChain 多 Agent 框架，并行执行 + 加权投票机制。

#### 多智能体 Swarm 系统

29 个预置 Swarm 团队：
| 类别 | 团队示例 |
|------|---------|
| 股票研究 | 股票研究团队、基本面研究团队、财报研究台 |
| 量化策略 | 量化策略台、ML 量化实验室、统计套利台 |
| 风险管理 | 风险委员会、组合审查委员会 |
| 宏观策略 | 宏观策略论坛、全球配置委员会 |
| 加密货币 | 加密交易台、加密研究实验室 |
| ETF 配置 | ETF 配置台 |

#### 专家技能库（74 个专业化 AI 技能模块）
数据获取、基本面分析、技术分析、量化策略、期权衍生、风控、宏观、情绪、工具导出等。

### 2.2 智能选股与信号系统

- **信号旗（Signal Flag Pool）**：多因子信号汇聚，优先级排序，每分钟实时扫描
- **智能推荐（AI Recommendation）**：市场脉搏、策略推荐、个股推荐、产业链机会
- **哨兵主动预警**：价格止损/放量异常/健康度/强势股/北向资金预警

### 2.3 量化研究与策略开发

- **因子工厂**：1000+ Alpha 因子，RD-Agent 自动挖掘，IC 监控，因子正交化
- **策略实验室**：在线 Python 编辑器，回测引擎，参数优化，策略诊断
- **自然语言策略生成**：用中文描述策略逻辑，AI 自动生成 Python 代码

### 2.4 投资组合管理

- 组合概览、收益统计、持仓分析、归因分析
- 均值-方差优化、风险平价、Black-Litterman
- 一键调仓建议

### 2.5 市场数据分析

- **市场全景**：大盘指数、板块轮动、资金流向、涨跌停统计
- **个股详情**：实时行情、K线分析、基本面、资金流向、龙虎榜、研报摘要
- **龙虎榜**：机构买卖、游资动向、关联营业部

### 2.6 投资者服务

- **AI 投资教练**：投资知识问答、策略诊断、学习路径
- **心理学监护**：交易心理分析、行为偏差检测
- **交易日记**：交易记录、复盘笔记、收益曲线

### 2.7 社交与内容

- **投资时刻**：发布动态、互动评论、AI 回复、研报收藏

---

## 3. 系统架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│ Presentation Layer (表现层)                                 │
│   Web UI (Jinja2) │ REST API (Flask) │ WebSocket            │
├─────────────────────────────────────────────────────────────┤
│ Application Layer (应用层)                                  │
│   Services │ DTO │ Workflows                                 │
├─────────────────────────────────────────────────────────────┤
│ Domain Layer (领域层)                                       │
│   Entities │ Contracts │ Events │ Alpha                      │
├─────────────────────────────────────────────────────────────┤
│ Infrastructure Layer (基础设施层)                           │
│   Repositories │ Providers │ Persistence                     │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 技术栈

| 类别 | 技术 |
|------|------|
| 后端 | Python 3.10+, Flask 3.0 |
| 前端 | HTML5, CSS3, JavaScript, Bootstrap 4 |
| 数据库 | MySQL 8.0, Redis, SQLite |
| 任务队列 | Celery + Redis |
| AI/ML | LangChain, LangGraph, Qlib, RD-Agent |
| LLM | OpenAI, DeepSeek, Ollama (本地) |

### 3.3 Agent 系统架构

```
Agent Orchestration Layer
├── Swarm Teams (29)
├── Expert Skills (74)
├── AI Committee (6)
└── LLM Provider (OpenAI / DeepSeek / Ollama / OpenRouter / Gemini)
```

### 3.4 部署架构

```
Load Balancer (Nginx)
├── Flask Web Server
├── Celery Worker
├── MySQL (Primary) → MySQL (Read Replica)
├── Redis (cache/session/real-time quotes)
└── Celery Beat (定时任务调度)
```

---

## 4. 用户手册

### 4.1 快速入门

1. 访问平台 URL，登录
2. 进入**今日操盘台**，查看当日市场概览
3. 左侧导航选择功能模块

### 4.2 核心功能使用

#### 智能选股流程
1. **信号旗选股**：设置筛选条件 → 查看信号强度 → 加入观察
2. **AI 推荐**：查看 Top3 股票 → 阅读推荐理由 → 执行交易
3. **AI 投资委员会**：提交个股 → 等待 6 Agent 分析 → 参考决策

#### 策略开发流程
- **自然语言**：中文描述 → AI 生成代码 → 一键回测
- **手动开发**：量化实验室 → 编写代码 → 设置回测参数 → 运行 → 优化

#### 组合管理
1. 创建组合 → 设定初始资金 → 添加持仓
2. 查看收益与风险 → 优化器调整 → 一键调仓

### 4.3 高级功能

- **Swarm 团队研究**：选择团队 → 输入标的与主题 → 启动分析 → 查看报告
- **因子工厂**：浏览预置因子 → 创建新因子 → 运行检测 → 加入组合
- **投资复盘**：查看交易记录 → 添加复盘笔记 → AI 行为分析

---

## 5. 部署指南

### 5.1 环境准备

```bash
git clone <项目地址>
cd quant-atlas
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 可选 Qlib：pip install -r requirements-qlib.txt
```

### 5.2 启动服务

```bash
export FLASK_SECRET_KEY=your-secret-key
python run.py
```

### 5.3 环境变量

| 变量 | 含义 |
|------|------|
| `FLASK_SECRET_KEY` | Session 密钥 |
| `QUANT_DATABASE_URI` | 数据库 URI |
| `TDX_ROOT_PATH` | 通达信根目录 |
| `ENABLE_QLIB` | 启用 Qlib |
| `ENABLE_CELERY` | 启用 Celery |
| `ENABLE_RD_AGENT` | 启用 RD-Agent |
| `LLM_PROVIDER` | LLM 提供商 |

### 5.4 Docker 部署

```yaml
services:
  web:
    build: .
    ports: ["5000:5000"]
    environment:
      - DATABASE_BACKEND=mysql
      - LLM_PROVIDER=ollama
    depends_on: [db, redis]
  db:
    image: mysql:8.0
  redis:
    image: redis:6-alpine
  worker:
    build: .
    command: celery -A app.tasks worker --loglevel=info
```

---

## 6. API 参考

### 6.1 核心 API 一览

| 接口路径 | 方法 | 功能 |
|---------|------|------|
| `/api/v1/quotes` | GET | 批量获取行情 |
| `/api/v1/kline` | GET | K线数据 |
| `/api/v1/panorama` | GET | 市场全景 |
| `/api/v1/sentiment` | GET | 情绪数据 |
| `/api/v1/watchlist` | GET/POST | 自选股管理 |
| `/api/v1/portfolio` | GET | 组合列表 |
| `/api/v1/signal-flag` | GET | 信号旗 |
| `/api/v1/strategy` | GET/POST | 策略管理 |
| `/api/v1/backtest` | POST | 执行回测 |
| `/api/v1/factor` | GET | 因子列表 |
| `/api/v1/agent-swarm/swarm/run` | POST | 运行 Swarm 团队 |
| `/api/v1/ai-committee/analyze` | POST | AI 投资委员会 |
| `/api/v1/nl-strategy/generate` | POST | 自然语言策略 |
| `/api/v1/auth/login` | POST | 用户登录 |

### 6.2 请求示例

```bash
# 获取行情
GET /api/v1/quotes?symbols=600519,000858&market=CN

# AI 投资委员会分析
POST /api/v1/ai-committee/analyze
{"symbol": "600519", "market": "CN"}

# 自然语言策略
POST /api/v1/nl-strategy/generate
{"description": "MACD金叉且成交量放大1.5倍时买入", "name": "MACD金叉策略"}
```

---

## 7. 数据字典

### 核心表结构

| 表 | 字段 | 说明 |
|----|------|------|
| users | id, username, email, password_hash, risk_preference | 用户 |
| watchlist | id, user_id, symbol, market, added_at | 自选股 |
| portfolios | id, user_id, name, initial_capital, current_value | 组合 |
| positions | id, portfolio_id, symbol, shares, avg_cost | 持仓 |
| trades | id, portfolio_id, symbol, direction, shares, price | 交易记录 |
| signals | id, symbol, signal_type, strength, ic_value | 信号 |
| factors | id, name, expression, category, ic_mean | 因子 |
| strategies | id, user_id, name, code, language, status | 策略 |

---

## 8. 安全与合规

### 8.1 认证授权
- 密码 bcrypt/Argon2 哈希
- JWT Token + Redis Session
- 双因素认证（TOTP）
- 5 次失败锁定 15 分钟

### 8.2 角色权限

| 角色 | 权限 |
|------|------|
| 游客 | 浏览行情 |
| 注册用户 | 自选股、信号、基础分析 |
| 付费用户 | AI 分析、策略实验室、组合优化 |
| 管理员 | 用户管理、系统配置 |

### 8.3 合规要求
- 数据源合规：Tushare、AkShare、通达信、OpenBB
- 模拟交易明确标注，不涉及真实资金
- AI 推荐可解释、可追溯，不承诺收益

---

## 9. 性能优化

### 9.1 数据库优化
- 索引：用户自选、信号查询、持仓查询
- 批量查询代替循环查询
- 缓存策略：实时行情 10 秒、K 线 5 分钟、自选 1 小时

### 9.2 应用优化
- 异步处理：耗时操作使用 Celery
- 连接池：数据库池、Redis 连接池

---

## 10. 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 登录失败 | 用户名错误、数据库连接失败 | 检查数据库连接 |
| 行情不更新 | 数据源限流、定时任务未运行 | 检查 Celery 任务状态 |
| AI 无响应 | LLM 未启动、模型加载失败 | 检查 Ollama 服务 |
| 回测缓慢 | 数据量过大、策略代码效率低 | 减少回测范围、向量化计算 |

---

## 11. 术语表

| 术语 | 说明 |
|------|------|
| Alpha | 超额收益 |
| IC | 信息系数 |
| IR | 信息比率 |
| 回测 | 用历史数据验证策略 |
| 因子 | 股票特征的量化指标 |
| 止损 | 亏损达阈值时卖出 |
| 夏普比率 | 风险调整后收益 |
| 最大回撤 | 账户从最高点到最低点跌幅 |
| Swarm | 多智能体协作系统 |
| RAG | 检索增强生成 |

---

## 12. FAQ

**Q: 如何配置本地大模型？**
A: `.env` 中设置 `LANGCHAIN_PROVIDER=ollama`, `LANGCHAIN_MODEL_NAME=qwen3:8b`, `OLLAMA_BASE_URL=http://localhost:11434`

**Q: 信号旗如何计算信号强度？**
A: 基于因子 IC 值、历史命中率、信号新鲜度加权计算。

**Q: AI 投资委员会建议可靠吗？**
A: 6 个 Agent 多角度分析后加权投票，应结合个人判断，仅供参考。

**Q: 策略回测与实盘差异大？**
A: 常见原因：滑点不足、流动性假设不合理、未来函数、过拟合。使用 Autopilot 检测漂移。

---
*Quant Atlas 团队 | 文档版本：2.0 | 更新时间：2026-06-13*
