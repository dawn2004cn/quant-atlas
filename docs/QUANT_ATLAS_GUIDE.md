# Quant Atlas 平台使用说明与技术架构文档

## 1. 平台简介 (Introduction)

**Quant Atlas** 是一个工业级的全栈量化研究与自动化交易平台。它集成了从全球多源行情获取、特征工程自动化挖掘（Alpha Zoo）、大模型辅助研究（LLM Agents）、高维行情预测（Foundation Models）到实盘自动化交易执行的闭环能力。平台旨在为量化研究员、基金经理及开发者提供一个高可扩展、符合 SOLID 设计原则的统一工作站。

---

## 2. 核心功能介绍 (Core Features)

### 2.1 市场全景与多源行情 (Market Panorama & OpenBB)
- **多市场支持**：原生支持 A 股、港股、美股、加密货币及外汇市场。
- **OpenBB 集成**：内置 OpenBB Data Provider，支持从 YFinance, FMP, Tiingo 等数十家国际主流供应商获取数据。
- **智能缓存**：基于 MySQL 的 TTL 行情缓存机制，显著降低 API 限制风险并提升响应速度。

### 2.2 量化实验室与因子挖掘 (Quant Lab & QuantML)
- **Alpha Zoo (1000+)**：预装了 QuantML 提供的超过 1000 个高 IC、高 ICIR 的量化因子表达式。
- **RD-Agent 自动挖掘**：集成微软 RD-Agent，支持基于强化学习和 LLM 的自动因子发现与优化。
- **Qlib 深度集成**：底层采用微软 Qlib 框架进行高效率的数据预处理、模型训练与回测。

### 2.3 预测与基础模型 (Inference & Kronos)
- **Kronos 生成式预测**：集成 Kronos 基础模型（Financial Foundation Model），支持对 K 线序列进行非线性生成式预测，产出 OHLCV 预测序列。
- **多模型管理**：支持 mini, small, base 等不同参数规模的模型切换与版本控制。

### 2.4 AI 智能体分析 (Agentic Analysis & QuantML-Agent)
- **市场情绪分析**：利用 LLM 智能体自动汇总全市场异动、榜单数据，生成贪婪/恐慌指数及趋势研判。
- **研报深度解读**：自动提取研报核心观点、预测逻辑及市场影响评估，将长文本转化为结构化知识。

### 2.5 自动化交易与执行 (Trading Engine & Freqtrade)
- **Bot 核心循环**：移植了 Freqtrade 的核心逻辑，支持基于策略信号的自动开平仓、ROI 动态止盈、硬止损。
- **持仓管理**：完整的交易生命周期管理，支持 MySQL 级审计落库。
- **支付编排 (Hyperswitch)**：内置 Hyperswitch 风格的支付编排引擎，支持多网关路由，为策略订阅或实盘资金管理提供支持。

### 2.6 信号旗与选股系统 (Signal Flag Pool)
- **多因子信号池**：支持多因子信号汇聚、聚合、过滤与优先级排序。
- **实时扫描**：基于 Celery 的定时扫描任务，实时监控市场信号。
- **信号观察**：追踪信号触发后的价格走势，评估信号有效性。

### 2.7 投资经理与模拟 (Investment Manager)
- **虚拟基金经理**：模拟多位知名投资经理（巴菲特、费雪、彼得·林奇等）的投资风格。
- **日间模拟**：收盘后自动执行模拟，记录虚拟持仓与收益。
- **回放功能**：支持历史信号的回放与复盘分析。

### 2.8 AI 对冲基金 (AI Hedge Fund)
- **多智能体分析**：集成 Warren Buffett、Druckenmiller、Cathie Wood 等多位 AI 分析师。
- **研报解读**：自动解析券商研报，提取核心观点与投资逻辑。
- **情绪分析**：基于新闻与社交媒体的市场情绪量化。

### 2.9 金融大模型 (FinGPT)
- **Financial GPT 集成**：支持基于大模型的金融分析。
- **投资建议生成**：基于基本面与技术面生成个性化投资建议。

### 2.10 风险管理 (Risk Management)
- **实时风控**：监控持仓风险敞口、杠杆率、流动性。
- **回撤控制**：设置最大回撤阈值，自动触发风控措施。
- **风险报告**：生成每日风险矩阵与预警报告。

### 2.11 因子研究平台 (Factor Research)
- **因子目录**：1000+ 预置 Alpha 因子表达式。
- **因子正交化**：正交化处理去除因子间共线性。
- **因子自校正**：自动检测因子失效并进行修复。
- **IC 监控**：因子 IC/IR 实时监控与告警。

### 2.12 任务管道 (Task Pipeline)
- **DAG 编排**：基于有向无环图的任务编排系统。
- **任务追踪**：完整的任务执行追踪与日志。
- **定时调度**：支持 Cron 表达式与固定间隔调度。

### 2.13 数据基础设施 (Data Infrastructure)
- **多源数据接入**：支持 TDX、AkShare、腾讯、OpenBB 等多数据源。
- **数据质量监控**：自动检测数据缺失、异常值与延迟。
- **数据回填**：增量与全量数据回填任务。

### 2.14 用户系统与生命周期 (User Lifecycle)
- **投资画像**：基于问卷与行为分析用户风险偏好。
- **访问控制**：基于角色的精细化权限管理 (RBAC)。
- **审计追踪**：完整的用户操作日志与审计。
- **生命周期管理**：用户注册、激活、留存、流失全流程管理。

### 2.15 推荐与决策系统
- **市场脉搏**：每日市场走势 AI 解读与展望。
- **策略推荐**：基于用户画像的策略推荐。
- **产业链分析**：产业链上下游关系图谱与机会挖掘。
- **诊断报告**：股票异常诊断与问题定位。

### 2.16 社交与内容平台 (Moments)
- **投资时刻**：类似雪球的投资者社区。
- **AI 回复**：AI 智能体自动回复用户提问。
- **研报收藏**：研报收藏与深度解读。

### 2.17 工作台与效率工具
- **每日工作台**：集成看盘、分析、决策的一站式工作区。
- **数据优化器**：数据压缩、缓存优化与性能调优。
- **内存优化**：运行时内存监控与优化建议。

---

## 3. 技术架构 (Technical Architecture)

Quant Atlas 遵循**六边形架构 (Hexagonal Architecture)** 与 **分层架构 (Layered Architecture)**，严格遵守设计模式六大原则（SOLID）。

### 3.1 分层职责
1.  **表现层 (Presentation)**:
    - `api/`: 提供 RESTful API 接口（v1/v2）。
    - `web/`: 负责 Flask 模板渲染与 Web 交互。
2.  **应用层 (Application)**:
    - 编排业务流程（如：`KronosPredictionService`, `TradingBotService`）。
    - 组织领域逻辑，不直接依赖底层技术实现。
3.  **领域层 (Domain)**:
    - 定义核心实体 (`Trade`, `Order`, `MarketInsight`, `QuantMLFactor`)。
    - 定义端口接口 (`MarketDataProvider`, `TradeRepository`, `AgentLLMPort`)。
4.  **基础设施层 (Infrastructure)**:
    - **Adapters**: 对接外部系统（`CCXTExchangeAdapter`, `OpenBBDataProvider`, `AgentLLMAdapter`）。
    - **Repositories**: 数据持久化实现（`MySQLTradingRepository`, `MySQLQuantMLFactorRepository`）。

### 3.2 技术栈 (Technology Stack)
- **Core**: Python 3.12+ / Flask
- **Database**: MySQL（事务主库）, SQLite（轻量）, TimescaleDB/PostgreSQL（时序 OHLCV）, Redis（缓存/消息）
- **Tasks**: Celery (异步扫描, 因子回填, 自动交易循环)
- **AI/LLM**: Ollama / DeepSeek / LangChain / LangGraph
- **Quant**: Qlib / RD-Agent / CCXT / OpenBB / Tushare
- **Storage**: SQLAlchemy / Alembic (迁移)
- **Monitoring**: OpenTelemetry / Structlog (日志)

---

## 4. 使用说明 (Usage Guide)

### 4.1 环境准备
1. 确保安装 `requirements.txt` 与 `requirements-qlib.txt` 中的依赖。
2. 配置 `.env` 文件：
   - 主库：`DATABASE_BACKEND=mysql` 并填写 `MYSQL_*`
   - 时序（可选，与 MySQL 并存）：`USE_TIMESCALEDB=1` 并填写 `TIMESCALEDB_*`（默认端口 `5434`）
3. 确保 Ollama 服务已启动（用于 AI Agent 模块）。

### 4.2 启动服务
- **Web 端**: 运行 `python run.py`，默认监听 `5000` 端口。
- **异步任务 (Worker)**: 运行 `start-celery - work.bat`。
- **定时调度 (Beat)**: 运行 `start-celery - beat.bat`。

### 4.3 核心工作流
1.  **因子同步**: 调用 `/api/v1/factors/sync` (内部) 或通过 `QuantMLFactorService` 导入 1000+ 基准因子。
2.  **市场研判**: 在首页查看 AI Agent 自动生成的 `MarketInsight`。
3.  **预测生成**: 针对选定标的调用 Kronos 预测接口，获取未来 5 日的预测走势。
4.  **Bot 运行**: 选择 `SampleStrategy`，启动 Trading Bot 进行模拟或实盘自动监控。
5.  **信号扫描**: 配置因子组合，通过信号旗池监控实时信号触发。
6.  **投资模拟**: 收盘后自动执行投资经理模拟，记录虚拟组合表现。
7.  **风险监控**: 实时监控持仓风险敞口，超阈值自动告警。
8.  **因子监控**: 因子 IC 低于阈值时自动发送告警通知。
9.  **数据维护**: 定时执行数据质量检查与回填任务。

---

## 5. 维护与扩展
- **新增数据源**: 在 `app/infrastructure/adapters` 中实现 `MarketDataProvider` 端口，并在 `bootstrap.py` 中注册。
- **新增策略**: 继承 `app/domain/strategy.py` 中的 `BaseStrategy`，实现 `populate_indicators` 等核心方法。
- **新增服务**: 在 `app/application/services` 中实现业务服务，并在 `bootstrap_components/services.py` 中注册。
- **新增 API**: 在 `app/presentation/api/routes_v1_*.py` 中添加新的蓝图注册。

### 5.1 结构性重构摘要（阶段 11–17，2026-05-23）

| 阶段 | 主题 | 要点 |
|------|------|------|
| 11 | DI 单源 | `service_wiring.wire_legacy_container_services` 取代 `container` 补位；Celery 经 `task_wiring` |
| 12 | 事务边界 | application 禁止 `conn.commit` / `_session_factory`；经 `mysql_access` Port |
| 13 | 热点 + Workbench DTO | `HotSectorStoragePort`、`DailyWorkbenchSnapshotDTO` |
| 14 | Workbench 路由 + TDX 板块 | 路由复用 bootstrap 服务；`TdxBlockReadPort` |
| 15 | TDX 写入仓储 | dayk/base ingest、`NullHotSectorStorageRepository` |
| 16 | Qlib + 集成探针 | dayk history 只读、 `IntegrationProbePort` |
| 17 | 文档 + 单测 | `repositories-layout.md`、`test_mysql_repository_ports.py` |

**权威路径**：服务装配 `bootstrap_components` + `service_wiring`；仓储工厂 `infrastructure/repositories/deps`（仅 bootstrap/tasks）；MySQL 读写 Port 见 `infrastructure_binding.py`。

详情：`docs/refactor/structural-debt-roadmap.md`、`REFACTORING_LOG.md`（2026-05-23 各阶段小节）。阶段 18–26 含 Health/ TDX Base deps 与 Factor Beat 钩子。

## 6. 目录结构

```
quant-atlas/
├── app/                    # 主应用
│   ├── application/        # 应用服务层
│   │   ├── services/      # 业务服务 (70+ 服务)
│   │   ├── workflows/     # 工作流编排
│   │   └── dto/           # 数据传输对象
│   ├── domain/            # 领域层
│   │   ├── contracts/     # 契约定义
│   │   ├── alpha/         # Alpha因子
│   │   └── events_core/  # 领域事件
│   ├── infrastructure/    # 基础设施层
│   │   ├── adapters/      # 外部适配器
│   │   ├── repositories/  # common / mysql / sqlite / postgres
│   │   ├── database/      # 连接层（mysql_client, postgres_client）
│   │   └── providers/     # 数据提供者
│   ├── presentation/      # 表现层
│   │   ├── api/           # REST API
│   │   └── web/           # Web 页面
│   └── tasks/             # Celery 任务
├── scripts/               # 脚本工具
├── tests/                 # 测试
└── docs/                  # 文档
```

---

*文档版本：v3.2 (2026-05-23)*
*由 Quant Atlas 架构重构组发布*
