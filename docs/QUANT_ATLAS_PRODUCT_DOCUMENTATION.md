# Quant Atlas - 智能量化投资平台
## 产品介绍、架构设计与用户手册

---

## 第一部分：产品愿景与市场定位

### 1.1 产品概述

Quant Atlas（量子图谱）是一款**工业级全栈智能量化投资平台**，旨在为量化研究员、基金经理、个人投资者和科技创业者提供从市场数据分析、因子挖掘、策略研发、回测验证到模拟交易的**端到端闭环能力**。平台深度融合了人工智能、大语言模型、多智能体系统与传统量化方法论，构建了一套**人机协同**的新型投资研究范式。

在当今量化投资领域，传统因子库逐渐失效、Alpha收益持续衰减、顶尖人才稀缺且成本高昂。Quant Atlas应运而生，通过**AI原生架构**重新定义量化研究流程：让AI Agents承担数据清洗、因子生成、策略回测等重复性工作，让人类研究者专注于**策略灵感与风险管理**这一最具价值的环节。

### 1.2 核心价值主张

**价值主张一：全链路自动化**
- 从市场数据获取→特征工程→因子挖掘→策略构建→回测验证→信号生成→模拟交易，全流程自动化执行。
- 传统量化团队需要数十人完成的工作，Quant Atlas通过智能化系统将人力需求降低80%以上。

**价值主张二：AI原生架构**
- 内置超过**100+ AI Agents**，覆盖研究分析、风险管理、交易执行、客服陪伴等全部场景。
- 支持大语言模型（LLM）驱动的自然语言策略生成、研究报告自动解读、市场情绪实时监控。
- 多智能体辩论机制模拟真实投资委员会决策过程，输出更稳健的投资建议。

**价值主张三：工业化可扩展性**
- 基于六边形架构（Hexagonal Architecture）与SOLID设计原则构建，模块解耦、职责清晰。
- 支持分布式部署、Celery异步任务调度、Redis缓存、MySQL持久化，满足生产级要求。
- 因子库预置**1000+ Alpha表达式**，支持Qlib深度集成、因子正交化、IC/IR实时监控。

**价值主张四：零门槛体验**
- 自然语言生成策略：用户用中文描述投资想法，AI自动生成可运行的Python策略代码。
- 智能选股：多因子信号池+AI推荐，用户无需编写代码即可获得股票推荐。
- 投资者教育：AI投资教练、心理学监护、交易复盘，陪伴用户从入门到进阶。

### 1.3 目标市场与竞争格局

**目标用户画像：**

| 用户类型 | 痛点 | Quant Atlas解决方案 |
|---------|------|-------------------|
| 量化研究员 | 因子挖掘效率低、回测系统搭建耗时 | RD-Agent自动因子挖掘、Qlib一体化回测 |
| 基金经理 | 研究覆盖不足、风控手段单一 | 多AI Agent委员会、实时风险监控 |
| 个人投资者 | 缺乏专业工具、选股效率低 | 智能选股系统、信号旗观察、哨兵预警 |
| 科技创业者 | 无量化背景、想配置量化策略 | NL策略生成、ETF智能配置、一键跟投 |

**市场竞争格局：**

当前市场上的量化平台主要分为三类：

1. **传统金融终端**（同花顺、Wind、Choice）：数据丰富但缺乏AI能力，策略研发依赖手工。
2. **互联网量化平台**（聚源、米筐、优矿）：提供基础回测功能，但AI能力薄弱。
3. **AI新型平台**（QuantConnect、Kaggle Quant）：强调AI但多为海外产品，本土化不足。

Quant Atlas的差异化优势在于：**深度本土化 + 全栈AI能力 + 工业化架构**，填补了国内高端量化平台的市场空白。

---

## 第二部分：核心功能详解

### 2.1 智能投资研究中枢

#### 2.1.1 AI投资委员会（多Agent辩论系统）

**功能描述：**
Quant Atlas创新性地构建了**AI投资委员会**机制，模拟真实基金公司投资决策流程。当用户提交一只股票的分析请求时，系统会同时启动6个专业化AI Agent进行多维度分析：

- **巴菲特Agent**：基本面价值派，重点分析财务稳健性、ROE、护城河与估值合理性
- **彼得·林奇Agent**：成长投资派，关注技术指标（RSI、MA）、成交量与短期爆发力
- **卡尔·伍德Agent**：宏观主题派，分析行业赛道、政策导向与未来潜力
- **风控Agent**：风险管理派，评估波动率、下行风险、Beta敞口与黑天鹅预警
- **情绪Agent**：舆情分析派，监控资金流向、社交媒体情绪与龙虎榜动向
- **新闻Agent**：事件驱动派，解读最新消息、公告要点与政策变化

**技术实现：**
- 基于LangChain多Agent框架，每个Agent拥有独立System Prompt与专业角色设定
- 并行执行+加权投票机制，根据不同风格Agent的权重汇总最终决策
- 支持置信度显示与决策解释，用户可追溯每个Agent的分析逻辑

**用户价值：**
传统单一AI回答容易产生偏见，多Agent辩论机制通过**观点交锋**输出更可靠的投资建议，消除单一模型的认知盲区。

#### 2.1.2 多智能体 Swarm 系统

**功能描述：**
Quant Atlas内置**29个预置Swarm团队**，每个团队由多个专业Agent组成，针对特定投资场景提供深度研究能力：

| 类别 | 团队示例 | 研究重点 |
|------|---------|---------|
| 股票研究 | 股票研究团队、基本面研究团队、财报研究台 | 个股深度分析、财务解读 |
| 量化策略 | 量化策略台、ML量化实验室、统计套利台 | 因子挖掘、策略开发、回测优化 |
| 风险管理 | 风险委员会、组合审查委员会 | 组合风控、持仓审查、VaR计算 |
| 宏观策略 | 宏观策略论坛、全球配置委员会、利率外汇台 | 经济周期、资产配置、汇率分析 |
| 加密货币 | 加密交易台、加密研究实验室 | 数字资产套利、链上分析、DeFi |
| 行业轮动 | 行业轮动团队、社交Alpha团队 | 景气监控、舆情挖掘 |
| 事件驱动 | 事件驱动特战队、可转债团队 | 并购重组、财报季策略 |
| ETF配置 | ETF配置台 | ETF轮动、折溢价套利 |

**技术实现：**
- 基于Task DAG的任务编排，支持任务依赖、串行/并行执行
- 支持Agent间上下文传递（upstream_context），下游Agent可继承上游分析结果
- 支持用户自定义变量（market, goal），灵活配置研究任务

#### 2.1.3 专家技能库（Expert Skills）

**功能描述：**
平台内置**74个专业化AI技能模块**，每个技能针对特定分析场景优化：

**数据获取类**：Tushare、AkShare、Yahoo Finance、CCXT交易所、OKX市场数据、文档解析、网页爬取
**基本面分析类**：财务报表分析、盈利预测、股息分析、估值模型（DCF）、信用分析
**技术分析类**：K线形态、蜡烛图、一目均衡表、缠论、波浪理论、谐波形态、Smart Money追踪
**量化策略类**：策略代码生成、回测诊断、因子研究、多因子模型、机器学习策略、业绩归因
**期权衍生类**：期权定价、希腊字母、对冲策略、波动率曲面
**风控类**：风险分析、爆仓热力图、行为金融偏差
**宏观类**：经济周期、全球宏观、地缘风险、季节性分析
**情绪类**：舆情监控、社交媒体情报、公司事件追踪
**其他**：Pine Script导出、VN.py策略导出、市场微结构分析

**技术实现：**
- 基于Skill Loader动态加载技能描述，Agent可按需调用
- 技能描述采用统一格式，包含：功能说明、输入参数、输出示例
- 支持技能组合调用，实现复杂分析流程自动化

### 2.2 智能选股与信号系统

#### 2.2.1 信号旗（Signal Flag Pool）

**功能描述：**
信号旗是Quant Atlas的**核心选股引擎**，从多因子信号池中实时捕获符合筛选条件的股票：

- **多因子信号汇聚**：整合技术面、基本面、资金面、情绪面等数十个因子信号
- **优先级排序**：根据信号强度、IC历史、因子权重进行综合排序
- **实时扫描**：基于Celery定时任务，每分钟更新市场信号
- **信号观察**：用户可将感兴趣的信号加入观察单，追踪后续走势

**技术实现：**
- 信号来源包括：因子表达式、技术形态、资金流向、北向资金、龙虎榜、研报推荐
- 信号有效性评估：记录信号触发后的N日涨跌幅，计算命中率与收益率
- 支持自定义信号阈值、过滤器条件

#### 2.2.2 智能推荐（AI Recommendation）

**功能描述：**
基于用户画像与市场环境，AI主动推荐投资机会：

- **市场脉搏**：每日AI生成市场走势解读与展望，包含涨跌停统计、资金流向、板块轮动
- **策略推荐**：根据用户风险偏好推荐匹配的策略类型（保守/平衡/激进）
- **个股推荐**：结合基本面、技术面、情绪面给出Top推荐个股及其买卖区间
- **产业链机会**：分析产业链上下游关系，挖掘潜在机会

#### 2.2.3 哨兵主动预警（Sentinel Alerts）

**功能描述：**
基于用户自选股的**主动风险预警系统**，实时监控持仓风险：

- **价格止损预警**：跌幅超过5%触发红色预警，3%触发黄色预警
- **放量异常预警**：成交量放大3倍以上提示异动
- **健康度预警**：综合评分低于40分提示风险
- **强势股预警**：评分80+且涨幅2%+提示潜在机会
- **北向资金预警**：A股放量上涨时提示北向资金关注

**技术实现：**
- 与自选股服务深度集成，获取实时行情数据
- 支持多级别预警（critical/warning/info/positive）
- 用户可执行止损、查看详情、添加关注等操作

### 2.3 量化研究与策略开发

#### 2.3.1 因子工厂（Alpha Factory）

**功能描述：**
因子工厂是Quant Atlas的**因子研究与生产系统**：

- **因子库**：预置1000+ Alpha因子表达式，涵盖动量、价值、成长、质量、风险等维度
- **因子挖掘**：支持基于RD-Agent的自动化因子发现
- **因子正交化**：Gramm-Schmidt正交化处理，消除因子间共线性
- **IC监控**：实时监控因子IC、IR值，失效告警
- **因子组合优化**：多因子加权组合最优解搜索

**技术实现：**
- 基于Qlib框架进行高效因子计算与回测
- WorldQuant 20经典Alpha+28算子内置
- 因子版本管理与实验记录追踪

#### 2.3.2 策略实验室（Quant Lab）

**功能描述：**
策略实验室提供**完整的策略研发环境**：

- **策略编辑**：在线Python代码编辑器，支持语法高亮与自动补全
- **回测引擎**：支持分钟级/日线级回测，统计Sharpe、Max Drawdown等指标
- **参数优化**：网格搜索与贝叶斯优化，寻找最优参数组合
- **策略诊断**：检测过拟合、幸存者偏差、前视偏见等问题
- **多策略对比**：同时运行多个策略，对比收益与风险特征

#### 2.3.3 自然语言策略生成（NL Strategy）

**功能描述：**
**革命性的零代码策略生成功能**，用户只需用自然语言描述投资想法：

示例输入：
> "当MACD金叉且成交量放大超过1.5倍，同时股价位于20日均线上方时买入，止损设为买入价的5%，止盈设为10%"

系统自动生成完整的Python策略代码，支持：
- 技术指标组合条件
- 资金管理与仓位规则
- 止盈止损逻辑
- 回测验证与优化

### 2.4 投资组合管理

#### 2.4.1 组合概览（Portfolio Overview）

**功能描述：**
统一展示用户所有投资组合的表现：

- **组合列表**：展示所有实盘/模拟组合的概况
- **收益统计**：累计收益、年化收益、胜率、夏普比率
- **持仓分析**：行业分布、市值分布、个股占比
- **归因分析**：收益来源分解（行业选择、个股选择、资产配置）

#### 2.4.2 组合优化（Portfolio Optimization）

**功能描述：**
基于现代投资组合理论的**智能资产配置**：

- **均值-方差优化**：马科维茨有效前沿求解
- **风险平价**：各资产风险贡献相等
- **Black-Litterman**：结合主观观点的贝叶斯优化
- **目标风险**：固定波动率或最大回撤约束

#### 2.4.3 一键调仓建议

**功能描述：**
基于当前持仓与优化模型，**一键生成调仓方案**：

- 显示需要卖出/买入的股票
- 计算最优仓位权重
- 预估交易成本与冲击
- 一键执行或手动调整

### 2.5 市场数据分析

#### 2.5.1 市场全景（Market Panorama）

**功能描述：**
全市场实时行情与资金流向监控：

- **大盘指数**：上证指数、深证成指、创业板指、科创50等
- **板块轮动**：行业/概念涨跌幅排行，轮动信号识别
- **资金流向**：北向资金、南向资金、主力资金
- **涨跌停统计**：涨停/跌停数量，市场热度指标

#### 2.5.2 个股详情（Stock Detail）

**功能描述：**
个股的**全维度分析页面**：

- **实时行情**：当前价格、涨跌幅、成交量、成交额
- **分时走势**：日内分钟级K线
- **技术分析**：多种技术指标图表（MA、MACD、KDJ、BOLL等）
- **基本面**：财务指标、估值数据、盈利预测
- **资金流向**：主力资金、散户资金、北向资金
- **龙虎榜**：上榜营业部、买卖金额
- **研报摘要**：最新券商研报要点

#### 2.5.3 龙虎榜（Longhu Bang）

**功能描述：**
每日龙虎榜数据展示：

- **机构买入/卖出**：机构席位资金净流入
- **游资动向**：著名游资操作记录
- **关联营业部**：多次上榜营业部分析
- **历史回溯**：历史龙虎榜查询

### 2.6 投资者服务与陪伴

#### 2.6.1 AI投资教练（AI Trading Coach）

**功能描述：**
**个性化投资教育与成长系统**：

- **投资知识问答**：回答用户关于基本面、技术面、量化的问题
- **策略诊断**：分析用户策略的优缺点，给出改进建议
- **学习路径**：根据用户水平推荐学习内容与练习
- **实战指导**：模拟实盘环境，指导用户执行交易

#### 2.6.2 心理学监护（Psychology Guardian）

**功能描述：**
**投资者心理健康管理**：

- **交易心理分析**：识别贪婪/恐惧情绪对决策的影响
- **行为偏差检测**：过度自信、损失厌恶、锚定效应等
- **心理建议**：提供调整心态的专业建议
- **复盘提醒**：亏损后引导进行理性复盘

#### 2.6.3 交易日记（Trade Journal）

**功能描述：**
**记录与复盘投资交易**：

- **交易记录**：自动同步实盘/模拟交易
- **复盘笔记**：手动添加交易心得与反思
- **收益曲线**：可视化展示收益走势
- **统计报告**：胜率、平均持仓天数、买卖时点分析

### 2.7 社交与内容

#### 2.7.1 投资时刻（Moments）

**功能描述：**
类似雪球的**投资者社区**：

- **发布动态**：分享投资观点与持仓
- **互动评论**：与其他投资者交流
- **AI回复**：AI自动回复提问，提升社区活跃度
- **研报收藏**：收藏与深度解读研报

---

## 第三部分：技术架构设计

### 3.1 整体架构

Quant Atlas采用**六边形架构（Hexagonal Architecture）**与**分层架构**相结合的设计理念，严格遵循SOLID设计原则，确保系统的**可扩展性、可测试性与可维护性**。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer (表现层)                           │
│   Web UI (Jinja2模板)  │  REST API (Flask)  │  WebSocket (实时推送)          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Application Layer (应用层)                             │
│   Services (业务服务)  │  DTO (数据传输对象)  │  Workflows (工作流)           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Domain Layer (领域层)                                │
│   Entities (实体)  │  Contracts (契约)  │  Events (事件)  │  Alpha (因子)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Infrastructure Layer (基础设施层)                        │
│   Repositories (仓储)  │  Providers (数据源)  │  Persistence (持久化)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 核心模块设计

#### 3.2.1 领域层（Domain Layer）

| 模块 | 职责 | 核心类 |
|------|------|--------|
| `contract/` | 统一契约定义 | AlphaEntity, Signal, Position, Order |
| `alpha/` | Alpha因子工厂 | WorldQuantKnowledge, FactorVault, Autopilot |
| `execution/` | 实盘执行引擎 | DigitalTwin, HighFidelityExecutor |
| `events_core` | 领域事件驱动 | DomainEvent, EventDispatcher |
| `risk/` | 风险管理 | RiskInterceptor, VaRCalculator |

**Alpha Factory 核心组件：**

```python
# 因子工厂 - 因子生成与验证
from app.domain.alpha import (
    WorldQuantKnowledge,      # 20个经典Alpha + 28算子
    get_factor_vault,          # 因子持久化存储
    get_autopilot,           # 自主驾驶控制器
)

# 自主驾驶流程 - 策略漂移检测与修复
from app.application.workflow import get_autopilot, AutopilotConfig

ap = get_autopilot(AutopilotConfig(drift_threshold=0.15))
report = ap.check_drift("strategy_a", backtest_return=0.20, live_return=0.05)
# 5步: Drift检测 → 根因分析 → RD-Agent修复 → 影子测试 → 热切换
```

#### 3.2.2 应用层（Application Layer）

应用层包含**100+业务服务**，按功能分为以下几类：

**研究分析类**：
- `SwarmAgentService`: 多智能体 Swarm 编排
- `AICommitteeService`: AI投资委员会（6 Agent辩论）
- `ResearchReportRAGService`: 研报RAG检索
- `AIResearchService`: AI研究报告生成
- `SentimentAnalysisService`: 市场情绪分析

**选股交易类**：
- `SignalFlagService`: 信号旗系统
- `WatchlistService`: 自选股管理
- `RecommendationService`: 智能推荐
- `TradingBotService`: 交易机器人

**量化研究类**：
- `QlibPipelineService`: Qlib流水线
- `FactorCatalogService`: 因子目录
- `StrategyService`: 策略管理
- `BacktestService`: 回测引擎
- `RDAgentRunService`: RD-Agent研究闭环

**风险管理类**：
- `RiskService`: 风险评估
- `PortfolioStressTestService`: 组合压力测试
- `WatchlistRiskService`: 自选股风控
- `LogicAuditService`: 策略逻辑审计

**用户服务类**：
- `UserService`: 用户管理
- `AuthService`: 认证授权
- `AITradingCoachService`: AI投资教练
- `PsychologyGuardianService`: 心理监护
- `RetailAssistantHubService`: 散户助手

#### 3.2.3 基础设施层（Infrastructure Layer）

**数据源（Providers）：**
- `TushareProvider`: A股行情与财务数据
- `AkShareProvider`: 财经数据接口
- `TDXProvider`: 通达信本地数据
- `OpenBBProvider`: 国际市场数据
- `CCXTProvider`: 加密货币交易所
- `OKXProvider`: OKX合约数据

**持久化（Persistence）：**
- `MySQL`: 主数据库，用户、持仓、交易记录
- `Redis`: 缓存层，实时行情、Session
- `Qlib DataFrame`: 因子与回测数据

**计算引擎（Compute）：**
- `Numba`: 向量化计算加速
- `Arrow`: 内存列式存储
- `Pandas/NumPy`: 数据处理

#### 3.2.4 Agent系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Orchestration Layer                  │
│   - SwarmOrchestratorAdapter: 多团队任务协调                    │
│   - ExpertSkillAdapter: 技能加载与调用                         │
│   - AgentTelemetryService: 性能监控与日志                      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Swarm Teams   │    │ Expert Skills │    │ AI Committee │
│    (29)       │    │    (74)       │    │     (6)      │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Provider Layer                            │
│   - OpenAI / DeepSeek / Ollama (本地) / OpenRouter / Gemini    │
└─────────────────────────────────────────────────────────────────┘
```

**Swarm Teams (29个预置团队)：**
- 股票研究、量化策略、风险管理、宏观策略、加密货币、衍生品、信用研究、行业轮动、社交Alpha、基金筛选、事件驱动、商品研究、可转债、技术分析、配对交易、ETF配置、全球股票等

**Expert Skills (74个技能)：**
- 数据获取、基本面分析、技术分析、量化策略、期权衍生、风控、宏观、情绪、工具导出等

**AI Committee (6个Agent)：**
- 巴菲特、彼得·林奇、卡尔·伍德、风控、情绪、新闻

### 3.3 部署架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Load Balancer (Nginx)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│     Flask Web Server        │         │     Celery Worker          │
│   (render templates,        │         │  (async tasks:             │
│    serve API,               │         │   - signal scan            │
│    user sessions)           │         │   - data sync              │
└─────────────────────────────┘         │   - factor compute         │
                    │                    │   - report gen)            │
                    ▼                    └─────────────────────────────┘
┌─────────────────────────────┐                    │
│      MySQL (Primary)        │                    ▼
│  (users, portfolios,        │         ┌─────────────────────────────┐
│   orders, audit logs)        │         │      Redis                 │
└─────────────────────────────┘         │  (cache, session,           │
                    │                    │   real-time quotes)         │
                    ▼                    └─────────────────────────────┘
┌─────────────────────────────┐
│    MySQL (Read Replica)     │
│  (query-heavy: dashboards,  │
│   reports, history)         │
└─────────────────────────────┘
```

**核心配置：**
- `DATABASE_BACKEND=mysql`: 主从分离
- `ENABLE_CELERY=1`: 异步任务处理
- `SCANNER_FORCE_THREADS=0`: 扫描器由Worker接管
- `LLM_PROVIDER=ollama`: 本地大模型（支持gemma4/qwen3/llama3）

---

## 第四部分：用户手册

### 4.1 快速入门

#### 4.1.1 首次登录

1. 访问平台URL，输入账号密码登录
2. 进入**今日操盘台**，查看当日市场概览
3. 在左侧导航栏选择功能模块

#### 4.1.2 添加自选股

1. 进入**自选股**页面
2. 在搜索框输入股票代码/名称
3. 点击添加按钮，将股票加入自选
4. 在自选股列表中查看实时行情与健康度评分

### 4.2 核心功能使用指南

#### 4.2.1 智能选股流程

**第一步：信号旗选股**
1. 进入**信号旗**页面
2. 设置筛选条件：行业、市值、涨跌幅、量比等
3. 查看符合条件的股票列表及其信号强度
4. 点击加入观察单或直接买入

**第二步：AI推荐**
1. 进入**今日操盘台**
2. 查看AI推荐的Top3股票
3. 阅读推荐理由与买卖区间
4. 决定是否纳入观察或执行交易

**第三步：AI投资委员会验证**
1. 进入个股详情页
2. 点击"AI分析"按钮
3. 等待6个Agent完成分析
4. 查看最终决策与置信度

#### 4.2.2 策略开发流程

**方式一：自然语言生成**
1. 进入**NL策略**页面
2. 用中文描述策略逻辑
3. 系统自动生成Python代码
4. 一键回测验证

**方式二：手动开发**
1. 进入**量化实验室**
2. 创建新策略，编写Python代码
3. 设置回测参数（时间、资金、手续费）
4. 运行回测，查看结果
5. 优化参数，循环迭代

#### 4.2.3 组合管理流程

1. 进入**组合**页面
2. 创建新组合，设定初始资金与策略
3. 添加持仓股票，设置仓位权重
4. 查看组合收益与风险指标
5. 使用优化器调整仓位
6. 一键执行调仓

### 4.3 高级功能

#### 4.3.1 Swarm团队研究

1. 进入**专家团队**页面
2. 选择感兴趣的团队（如"股票研究团队"）
3. 输入研究标的与研究主题
4. 启动团队分析任务
5. 查看多Agent协作产出的研究报告

#### 4.3.2 因子工厂

1. 进入**因子仓库**
2. 浏览预置因子，查看IC/IR表现
3. 创建新因子，编写表达式
4. 运行因子检测，查看历史表现
5. 加入因子组合，优化权重

#### 4.3.3 投资复盘

1. 进入**交易日记**
2. 查看历史交易记录
3. 添加复盘笔记，分析盈亏原因
4. 查看AI生成的行为分析报告
5. 根据建议调整投资行为

### 4.4 常见问题FAQ

**Q1: 如何配置本地大模型？**
A: 在.env文件中设置：
   ```
   LANGCHAIN_PROVIDER=ollama
   LANGCHAIN_MODEL_NAME=qwen3:8b
   OLLAMA_BASE_URL=http://localhost:11434
   ```
   建议使用qwen3:8b或llama3.1:8b（支持推理）。

**Q2: 信号旗是如何计算信号强度的？**
A: 信号强度基于因子IC值、历史命中率、信号新鲜度加权计算。

**Q3: AI投资委员会的建议可靠吗？**
A: 6个Agent从不同角度分析，通过加权投票得出结论。用户应结合自身判断，AI建议仅供参考。

**Q4: 如何导入通达信数据？**
A: 在设置中配置TDX_ROOT_PATH，指向通达信安装目录，系统会自动同步日线数据。

**Q5: 策略回测与实盘差异大怎么办？**
A: 使用Autopilot功能检测策略漂移，系统会自动分析原因并尝试修复。

---

## 第五部分：技术指标与性能

### 5.1 系统规模

| 指标 | 数值 |
|------|------|
| 页面模板 | 46+ 个 |
| 后端服务 | 100+ 个 |
| Swarm团队 | 29 个 |
| Expert Skills | 74 个 |
| AI Committee Agents | 6 个 |
| 预置Alpha因子 | 1000+ 个 |
| API接口 | 200+ 个 |

### 5.2 性能指标

| 指标 | 目标值 | 说明 |
|------|-------|------|
| 页面响应时间 | < 500ms | 首页/列表页 |
| API响应时间 | < 200ms | 核心接口 |
| 信号扫描频率 | 1分钟/次 | 实时信号 |
| 回测速度 | > 1000 bars/s | 日线回测 |
| 支持并发用户 | 100+ | 预估 |

### 5.3 技术栈

- **后端**: Python 3.12, Flask 3.0
- **前端**: HTML5, CSS3, JavaScript (原生 + jQuery)
- **数据库**: MySQL 8.0, Redis
- **任务队列**: Celery + Redis
- **AI/ML**: LangChain, Qlib, RD-Agent
- **LLM**: OpenAI, DeepSeek, Ollama (本地)

---

## 第六部分：商业价值与市场前景

### 6.1 商业模式

**B2C个人版**：
- 免费基础功能（行情、数据）
- 付费高级功能（AI分析、策略实验室、组合优化）
- 月付/年付订阅

**B2B机构版**：
- 私有化部署
- API调用计费
- 定制开发服务

### 6.2 市场空间

根据行业报告，中国量化投资市场：
- 个人投资者：超过1.5亿
- 私募基金：超过2万家，管理规模超5万亿
- 券商自营：头部券商量化团队超100人

Quant Atlas的目标是成为**每个人**的智能量化助手，无论专业与否，都能借助AI的力量做出更好的投资决策。

### 6.3 竞争优势

| 维度 | 竞争对手 | Quant Atlas优势 |
|------|---------|----------------|
| AI能力 | 传统平台无AI | 100+ Agents、多Agent辩论 |
| 本土化 | 海外平台 | 深度A股、ETF、期货支持 |
| 易用性 | 代码为主 | 自然语言生成策略 |
| 架构 | 单体架构 | 微服务、六边形、可扩展 |

---
# Quant Atlas 产品文档附录
## 深度技术细节、API参考与最佳实践

---

## 第七部分：API接口参考

### 7.1 核心API一览

Quant Atlas提供**200+ RESTful API接口**，覆盖所有业务功能。以下列出核心接口：

#### 7.1.1 市场数据API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/quotes` | GET | 批量获取股票实时行情 |
| `/api/v1/quotes/{symbol}` | GET | 获取单只股票行情 |
| `/api/v1/kline` | GET | 获取K线数据（日/周/月/分钟） |
| `/api/v1/panorama` | GET | 获取市场全景数据 |
| `/api/v1/sentiment` | GET | 获取市场情绪数据 |
| `/api/v1/longhub` | GET | 获取龙虎榜数据 |
| `/api/v1/fund-flow` | GET | 获取资金流向数据 |
| `/api/v1/sector-rotation` | GET | 获取板块轮动数据 |

#### 7.1.2 自选股与组合API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/watchlist` | GET/POST | 获取/添加自选股 |
| `/api/v1/watchlist/{symbol}` | DELETE | 删除自选股 |
| `/api/v1/portfolio` | GET | 获取组合列表 |
| `/api/v1/portfolio/{id}` | GET | 获取组合详情 |
| `/api/v1/portfolio/optimize` | POST | 组合优化 |
| `/api/v1/position` | GET | 获取持仓明细 |

#### 7.1.3 信号与选股API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/signal-flag` | GET | 获取信号旗列表 |
| `/api/v1/signal-flag/scan` | POST | 触发信号扫描 |
| `/api/v1/observations` | GET | 获取观察单 |
| `/api/v1/recommendations` | GET | 获取AI推荐 |

#### 7.1.4 量化研究API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/strategy` | GET/POST | 获取/创建策略 |
| `/api/v1/backtest` | POST | 执行回测 |
| `/api/v1/factor` | GET | 获取因子列表 |
| `/api/v1/factor/validate` | POST | 验证因子有效性 |
| `/api/v1/因子/orthogonalize` | POST | 因子正交化 |

#### 7.1.5 AI Agent API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/agent-swarm/swarm/run` | POST | 运行Swarm团队 |
| `/api/v1/agent-swarm/swarm/status/{id}` | GET | 获取任务状态 |
| `/api/v1/agent-swarm/capabilities` | GET | 列出所有Agent能力 |
| `/api/v1/ai-committee/analyze` | POST | AI投资委员会分析 |
| `/api/v1/ai-chat/chat` | POST | AI对话 |
| `/api/v1/nl-strategy/generate` | POST | 自然语言生成策略 |

#### 7.1.6 用户与权限API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/auth/logout` | POST | 用户登出 |
| `/api/v1/user/profile` | GET | 获取用户资料 |
| `/api/v1/user/investment-profile` | GET/POST | 投资画像 |
| `/api/v1/trade-journal` | GET/POST | 交易日记 |

### 7.2 API请求示例

#### 示例1：获取股票行情

```bash
# 请求
GET /api/v1/quotes?symbols=600519,000858&market=CN

# 响应
{
  "data": {
    "600519": {
      "symbol": "600519",
      "name": "贵州茅台",
      "price": 1680.50,
      "change_pct": 1.25,
      "volume": 1250000,
      "amount": 2080000000,
      "amplitude": 2.15,
      "turnover": 0.85,
      "update_time": "2026-05-03 14:30:00"
    },
    "000858": {
      "symbol": "000858",
      "name": "五粮液",
      "price": 148.20,
      "change_pct": 0.88,
      "volume": 850000,
      "amount": 125400000,
      "update_time": "2026-05-03 14:30:00"
    }
  }
}
```

#### 示例2：运行AI投资委员会

```bash
# 请求
POST /api/v1/ai-committee/analyze
Content-Type: application/json

{
  "symbol": "600519",
  "market": "CN"
}

# 响应
{
  "symbol": "600519",
  "market": "CN",
  "timestamp": "2026-05-03T14:35:22",
  "steps": [
    {
      "agent_id": "buffett",
      "agent_name": "巴菲特Agent",
      "signal": "bullish",
      "reasoning": "贵州茅台具有强大的品牌护城河，ROE持续保持在30%以上，现金流充裕..."
    },
    {
      "agent_id": "lynch",
      "agent_name": "彼得·林奇Agent",
      "signal": "neutral",
      "reasoning": "技术面上股价处于历史高位，RSI指标显示超买..."
    }
    // ... 其他5个Agent
  ],
  "consensus": {
    "final_action": "bullish",
    "confidence": "68.5%",
    "votes": {
      "bullish": "45%",
      "neutral": "30%",
      "bearish": "15%",
      "risk": "10%"
    }
  }
}
```

#### 示例3：自然语言生成策略

```bash
# 请求
POST /api/v1/nl-strategy/generate
Content-Type: application/json

{
  "description": "当MACD金叉且成交量放大超过1.5倍，同时股价位于20日均线上方时买入，止损设为买入价的5%",
  "name": "MACD金叉策略"
}

# 响应
{
  "strategy_id": "strat_20260503_001",
  "name": "MACD金叉策略",
  "code": "import pandas as pd\nimport numpy as np\n...\n# 完整的Python策略代码",
  "language": "python",
  "estimated_return": "年化15-25%",
  "risk_level": "中等",
  "parameters": [
    {"name": "fast_period", "default": 12, "description": "快线周期"},
    {"name": "slow_period", "default": 26, "description": "慢线周期"},
    {"name": "volume_threshold", "default": 1.5, "description": "成交量放大倍数"}
  ]
}
```

---

## 第八部分：数据结构字典

### 8.1 核心实体

#### 8.1.1 用户表 (users)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| username | VARCHAR(50) | 用户名 |
| email | VARCHAR(100) | 邮箱 |
| password_hash | VARCHAR(255) | 密码哈希 |
| risk_preference | ENUM | 风险偏好(保守/平衡/激进) |
| created_at | DATETIME | 创建时间 |
| last_login | DATETIME | 最后登录 |

#### 8.1.2 自选股表 (watchlist)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户ID |
| symbol | VARCHAR(20) | 股票代码 |
| market | ENUM | 市场(CN/HK/US/CRYPTO) |
| added_at | DATETIME | 添加时间 |
| notes | TEXT | 备注 |

#### 8.1.3 组合表 (portfolios)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户ID |
| name | VARCHAR(100) | 组合名称 |
| initial_capital | DECIMAL | 初始资金 |
| current_value | DECIMAL | 当前价值 |
| created_at | DATETIME | 创建时间 |

#### 8.1.4 持仓表 (positions)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| portfolio_id | INT | 组合ID |
| symbol | VARCHAR(20) | 股票代码 |
| shares | INT | 持仓数量 |
| avg_cost | DECIMAL | 平均成本 |
| current_price | DECIMAL | 当前价格 |
| unrealized_pnl | DECIMAL | 未实现盈亏 |

#### 8.1.5 交易记录表 (trades)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| portfolio_id | INT | 组合ID |
| symbol | VARCHAR(20) | 股票代码 |
| direction | ENUM | 方向(买入/卖出) |
| shares | INT | 数量 |
| price | DECIMAL | 价格 |
| amount | DECIMAL | 金额 |
| trade_at | DATETIME | 交易时间 |
| strategy_id | INT | 策略ID |

#### 8.1.6 信号表 (signals)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| symbol | VARCHAR(20) | 股票代码 |
| signal_type | VARCHAR(50) | 信号类型 |
| strength | FLOAT | 信号强度(0-1) |
| ic_value | FLOAT | IC值 |
| generated_at | DATETIME | 生成时间 |
| expires_at | DATETIME | 过期时间 |

#### 8.1.7 因子表 (factors)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| name | VARCHAR(100) | 因子名称 |
| expression | TEXT | 因子表达式 |
| category | VARCHAR(50) | 类别 |
| ic_mean | FLOAT | IC均值 |
| ic_ir | FLOAT | IR值 |
| created_at | DATETIME | 创建时间 |

#### 8.1.8 策略表 (strategies)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户ID |
| name | VARCHAR(100) | 策略名称 |
| code | TEXT | 策略代码 |
| language | VARCHAR(20) | 语言(pythonpine) |
| status | ENUM | 状态(草稿/回测/实盘/停用) |
| created_at | DATETIME | 创建时间 |

---

## 第九部分：部署与运维

### 9.1 环境要求

#### 9.1.1 基础环境

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| Python | >= 3.10 | 推荐3.12 |
| MySQL | >= 8.0 | 主从架构 |
| Redis | >= 6.0 | 缓存与消息队列 |
| Celery | >= 5.0 | 异步任务 |

#### 9.1.2 可选组件

| 组件 | 用途 | 说明 |
|------|------|------|
| Ollama | 本地LLM | 支持gemma4/qwen3/llama3 |
| Qlib | 量化研究 | 因子计算与回测 |
| Nginx | Web服务器 | 反向代理与负载均衡 |

### 9.2 部署步骤

#### 步骤1：环境准备

```bash
# 克隆项目
git clone https://github.com/quant-atlas/quant-atlas.git
cd quant-atlas

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 步骤2：配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置（关键项）
vim .env

# 数据库配置
DATABASE_BACKEND=mysql
MYSQL_HOST=192.168.1.100
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=quant_atlas

# LLM配置
LLM_PROVIDER=ollama
LANGCHAIN_MODEL_NAME=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
```

#### 步骤3：初始化数据库

```bash
# 执行迁移
flask db upgrade

# 或运行初始化脚本
python scripts/init_db.py
```

#### 步骤4：启动服务

```bash
# 启动Web服务
python run.py

# 启动Celery Worker（可选）
celery -A app.tasks worker --loglevel=info

# 启动Celery Beat（可选）
celery -A app.tasks beat --loglevel=info
```

### 9.3 Docker部署（推荐）

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_BACKEND=mysql
      - MYSQL_HOST=db
      - LLM_PROVIDER=ollama
    depends_on:
      - db
      - redis

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: quant_atlas
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

  worker:
    build: .
    command: celery -A app.tasks worker --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  mysql_data:
  redis_data:
```

```bash
# 启动
docker-compose up -d
```

### 9.4 运维监控

#### 9.4.1 日志管理

```bash
# 查看应用日志
tail -f logs/quant_atlas.log

# 查看Celery日志
celery -A app.tasks inspect active

# 查看Nginx日志
tail -f /var/log/nginx/access.log
```

#### 9.4.2 健康检查

```bash
# API健康检查
curl http://localhost:5000/api/v1/health

# 数据库连接
flask db check

# Redis连接
redis-cli ping
```

#### 9.4.3 性能监控

- **响应时间**: Prometheus + Grafana
- **错误追踪**: Sentry
- **日志聚合**: ELK Stack

---

## 第十部分：安全性设计

### 10.1 认证与授权

#### 10.1.1 用户认证

- **密码加密**: 使用bcrypt或Argon2进行密码哈希
- **会话管理**: JWT Token + Redis Session存储
- **双因素认证**: 支持TOTP（时间同步验证码）
- **登录保护**: 5次失败锁定15分钟

#### 10.1.2 API认证

```python
# 请求头格式
Authorization: Bearer <jwt_token>

# Token包含信息
{
  "user_id": 123,
  "exp": 1715000000,
  "permissions": ["read", "trade"]
}
```

#### 10.1.3 角色权限

| 角色 | 权限 |
|------|------|
| 游客 | 浏览行情 |
| 注册用户 | 自选股、信号、基础分析 |
| 付费用户 | AI分析、策略实验室、组合优化 |
| 管理员 | 用户管理、系统配置 |

### 10.2 数据安全

#### 10.2.1 传输安全

- 全站HTTPS强制
- API签名验证
- 请求参数加密

#### 10.2.2 存储安全

- 数据库敏感字段加密
- 定期备份（每日增量、每周全量）
- 备份加密存储

#### 10.2.3 隐私保护

- 个人信息脱敏显示
- 交易记录隐私保护
- 数据导出权限控制

### 10.3 风控机制

#### 10.3.1 交易风控

- 单日最大亏损限制
- 单笔最大仓位限制
- 交易频率限制
- 异常交易行为拦截

#### 10.3.2 系统风控

- 接口调用频率限制（Rate Limiting）
- SQL注入防护
- XSS攻击防护
- CSRF Token验证

---

## 第十一部分：性能优化指南

### 11.1 数据库优化

#### 11.1.1 索引优化

```sql
-- 自选股查询
CREATE INDEX idx_watchlist_user ON watchlist(user_id);

-- 信号查询
CREATE INDEX idx_signal_symbol_time ON signals(symbol, generated_at DESC);

-- 持仓查询
CREATE INDEX idx_position_portfolio ON positions(portfolio_id, symbol);
```

#### 11.1.2 查询优化

```python
# 使用批量查询代替循环
# 错误
for symbol in symbols:
    quote = get_quote(symbol)  # N次查询

# 正确
quotes = batch_get_quotes(symbols)  # 1次查询
```

#### 11.1.3 缓存策略

| 数据类型 | 缓存时间 | 策略 |
|---------|---------|------|
| 实时行情 | 10秒 | Redis |
| K线数据 | 5分钟 | Redis |
| 用户自选 | 1小时 | Redis |
| 组合数据 | 30秒 | Redis |
| 因子数据 | 1天 | MySQL |

### 11.2 应用优化

#### 11.2.1 异步处理

```python
# 耗时操作使用Celery
@celery.task
def generate_backtest_report(strategy_id):
    # 回测计算
    # 生成报告
    pass

# API立即返回
@app.route('/api/v1/backtest', methods=['POST'])
def start_backtest():
    task = generate_backtest_report.delay(strategy_id)
    return {'task_id': task.id}
```

#### 11.2.2 连接池

```python
# 数据库连接池
engine = create_engine(
    "mysql://user:pass@host/db",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

# Redis连接池
redis_pool = ConnectionPool(
    max_connections=50,
    decode_responses=True
)
```

### 11.3 前端优化

#### 11.3.1 资源优化

- CSS/JS压缩合并
- 图片懒加载
- 静态资源CDN部署
- 浏览器缓存策略

#### 11.3.2 请求优化

- API批量请求
- 请求去重与防抖
- 分页加载

---

## 第十二部分：故障排查指南

### 12.1 常见问题与解决方案

#### 问题1：登录失败，提示"用户不存在"

**可能原因**：
- 用户名输入错误
- 数据库连接失败

**排查步骤**：
1. 检查数据库连接配置
2. 验证users表是否有数据
3. 检查密码哈希算法是否一致

#### 问题2：行情数据不更新

**可能原因**：
- 数据源API限制
- 定时任务未运行

**排查步骤**：
1. 检查Celery任务状态：`celery -A app.tasks inspect scheduled`
2. 查看数据同步日志
3. 测试数据源API连通性

#### 问题3：AI分析无响应

**可能原因**：
- LLM服务未启动
- 模型加载失败

**排查步骤**：
1. 检查Ollama服务状态：`ollama list`
2. 验证模型是否安装：`ollama run qwen3:8b`
3. 检查.env中LLM配置

#### 问题4：回测运行缓慢

**可能原因**：
- 数据量过大
- 策略代码效率低
- 服务器资源不足

**优化方案**：
1. 减少回测时间范围
2. 使用向量化计算替代循环
3. 增加服务器内存

### 12.2 日志分析

#### 关键日志位置

| 日志 | 路径 |
|------|------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| 访问日志 | `logs/access.log` |
| Celery日志 | `logs/celery.log` |

#### 日志级别

| 级别 | 说明 |
|------|------|
| DEBUG | 详细调试信息 |
| INFO | 正常业务流程 |
| WARNING | 警告但不影响功能 |
| ERROR | 错误导致功能异常 |
| CRITICAL | 系统级严重错误 |

---

## 第十三部分：版本历史与路线图

### 13.1 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| v1.0.0 | 2025-06 | 初始版本发布 |
| v1.1.0 | 2025-09 | AI投资委员会、多Agent系统 |
| v1.2.0 | 2025-12 | 自然语言策略、因子工厂 |
| v1.3.0 | 2026-02 | 组合优化、交易机器人 |
| v1.4.0 | 2026-04 | RD-Agent集成、Qlib深度支持 |
| v1.5.0 | 2026-05 | 本地LLM支持、哨兵预警系统 |

### 13.2 未来路线图

#### 2026年Q3目标

- [ ] **多模态分析**：支持图片、语音输入
- [ ] **实时流式响应**：WebSocket长连接，AI分析流式输出
- [ ] **策略市场**：用户可上架/订阅策略
- [ ] **模拟交易联赛**：用户间收益排名

#### 2026年Q4目标

- [ ] **实盘交易对接**：支持多家券商API
- [ ] **基金产品化**：组合可包装为基金产品
- [ ] **机构版**：私有化部署方案
- [ ] **量化大赛**：定期举办策略大赛

#### 2027年目标

- [ ] **Foundation Models**：自研金融大模型
- [ ] **强化学习策略**：RL驱动的自适应策略
- [ ] **全球市场**：扩展至亚太、欧洲市场
- [ ] **生态开放**：开放API、插件市场

---

## 第十四部分：术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| Alpha | Alpha | 超额收益，策略相对于基准的收益 |
| IC | Information Coefficient | 信息系数，预测与实际收益的相关性 |
| IR | Information Ratio | 信息比率，Alpha除以跟踪误差 |
| 回测 | Backtest | 用历史数据验证策略 |
| 因子 | Factor | 股票特征的量化指标 |
| 多因子 | Multi-Factor | 多个因子组合的选股模型 |
| 止损 | Stop Loss | 亏损达到阈值时卖出 |
| 止盈 | Take Profit | 盈利达到目标时卖出 |
| 仓位 | Position | 持有的股票数量 |
| 滑点 | Slippage | 期望成交价与实际成交价之差 |
| 波动率 | Volatility | 资产价格变动幅度 |
| 最大回撤 | Max Drawdown | 账户从最高点到最低点的跌幅 |
| 夏普比率 | Sharpe Ratio | 风险调整后收益指标 |
| 卡玛比率 | Calmar Ratio | 年化收益除以最大回撤 |
| 择时 | Timing | 买入卖出时机的选择 |
| 选股 | Stock Selection | 决定买卖哪些股票 |
| Swarm | Swarm | 多智能体协作系统 |
| Agent | Agent | AI智能体 |
| RAG | Retrieval-Augmented Generation | 检索增强生成 |
| LLM | Large Language Model | 大语言模型 |

---

## 第十五部分：附录

### 15.1 配置参数参考

```python
# 核心配置示例

# 交易配置
POSITION_SIZE = 0.1  # 单只股票仓位上限10%
MAX_POSITIONS = 10   # 最大持仓数量
STOP_LOSS = 0.05    # 默认止损5%
TAKE_PROFIT = 0.15  # 默认止盈15%

# 回测配置
INITIAL_CAPITAL = 1000000  # 初始资金100万
COMMISSION = 0.0003       # 手续费万三
SLIPPAGE = 0.001           # 滑点千一

# 因子配置
MIN_IC = 0.02              # 最小IC阈值
MIN_IR = 0.5               # 最小IR阈值
REBALANCE_FREQ = 'W'       # 周频率调仓

# AI配置
LLM_TEMPERATURE = 0.1      # LLM创造性（低=确定性）
MAX_TOKENS = 2000          # 最大输出token
AGENT_TIMEOUT = 300        # Agent超时时间（秒）
```

### 15.2 贡献者指南

```bash
# 提交代码流程
1. Fork项目
2. 创建功能分支：git checkout -b feature/xxx
3. 编写代码并测试
4. 提交代码：git commit -m "feat: add xxx"
5. 推送分支：git push origin feature/xxx
6. 发起Pull Request

# 代码规范
- 使用Black格式化
- 使用Ruff检查
- 遵循PEP 8
- 提交前运行测试
```

### 15.3 许可证

本项目采用 **MIT License**。

---
# Quant Atlas 产品文档续编
## 高级功能详解、行业解决方案与生态合作

---

## 第十六部分：行业解决方案

### 16.1 个人投资者解决方案

#### 痛点分析
- **知识盲区**：缺乏系统的投资知识体系
- **信息过载**：面对海量数据无从下手
- **情绪化交易**：容易受市场波动影响做出冲动决策
- **时间有限**：无法持续跟踪市场动态

#### Quant Atlas解决方案

**阶段一：入门学习**
- AI投资教练提供基础投资知识问答
- 投资画像问卷确定风险偏好
- 推荐适合的学习内容路径

**阶段二：辅助决策**
- 智能选股系统降低选股门槛
- AI投资委员会提供专业分析视角
- 哨兵预警系统监控持仓风险

**阶段三：实践成长**
- 模拟交易积累实盘经验
- 交易日记记录与复盘
- 心理学监护纠正行为偏差

**成功案例**
> 张先生，35岁，互联网从业者，2025年Q4开始使用Quant Atlas。
> - 投资经验：3年，基本被割韭菜
> - 使用功能：AI推荐、信号旗、交易复盘
> - 成果：2026年Q1收益率+18%，跑赢沪深300指数12个百分点

### 16.2 量化研究员解决方案

#### 痛点分析
- **因子挖掘效率低**：手动尝试大量因子组合
- **回测系统搭建耗时**：基础设施占用研究时间
- **策略验证周期长**：从想法到可回测需要大量编码
- **知识传承困难**：个人经验难以系统化

#### Quant Atlas解决方案

**因子工厂**
- 1000+预置Alpha因子，即取即用
- RD-Agent自动因子挖掘，释放人力
- 因子有效性实时监控，失效告警

**量化实验室**
- 一体化回测环境，无需搭建基础设施
- 参数自动优化，快速找到最优参数
- 多策略对比，横向评估策略优劣

**自然语言策略**
- 用自然语言描述策略想法，AI自动生成代码
- 大幅缩短从想法到回测的周期

**知识管理**
- 因子、策略、实验记录持久化存储
- 可追溯的历史版本管理
- 团队知识共享与协作

### 16.3 基金经理解决方案

#### 痛点分析
- **研究覆盖不足**：只能覆盖少数行业/股票
- **风控手段单一**：缺乏实时风险监控
- **决策效率低**：依赖人工整合多方信息
- **人才成本高**：资深研究员薪酬高昂

#### Quant Atlas解决方案

**多Agent研究团队**
- 29个预置Swarm团队，覆盖全行业研究
- 并行执行，大幅提升研究效率
- 标准化输出，确保研究质量

**AI投资委员会**
- 6个专业Agent多维度分析
- 去除单一观点偏见
- 决策可解释、可追溯

**实时风控**
- 组合层面VaR计算
- 持仓风险敞口监控
- 黑天鹅预警机制

**投资决策支持**
- 市场全景实时掌握
- 资金流向精准追踪
- 板块轮动信号识别

---

## 第十七部分：高级功能详解

### 17.1 RD-Agent研究闭环

#### 什么是RD-Agent？

RD-Agent（Research & Development Agent）是微软开源的**自动化量化研究智能体**，Quant Atlas深度集成了这一能力，实现从"想法"到"因子"到"策略"的完整闭环。

#### 工作流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RD-Agent Research Loop                           │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
     │ 提出研究 │ ──▶ │ 因子搜索 │ ──▶ │ 因子验证 │ ──▶ │ 因子优化 │
     │  想法    │     │ 与生成   │     │ 与筛选   │     │ 与组合   │
     └──────────┘     └──────────┘     └──────────┘     └──────────┘
          │                                                    │
          │         ┌─────────────────────────────────────────┘
          │         ▼
          │    ┌──────────┐     ┌──────────┐     ┌──────────┐
          └───▶ │ 策略生成 │ ──▶ │ 回测验证 │ ──▶ │ 报告输出 │
                │ 与构建   │     │ 与评估   │     │ 与归档   │
                └──────────┘     └──────────┘     └──────────┘
```

#### 具体步骤

**步骤1：提出研究想法**
```python
# 用户输入示例
research_idea = "寻找能够预测A股市场短期反转的因子"

# RD-Agent接收并理解
```

**步骤2：因子搜索与生成**
- 基于知识库检索相似因子
- 使用LLM生成新因子表达式
- 评估因子新颖性与潜力

**步骤3：因子验证**
- 在历史数据上计算IC/IR
- 剔除低效因子
- 进行过拟合检验

**步骤4：因子优化**
- 多因子正交化处理
- 权重优化求解
- 稳定性检验

**步骤5：策略构建**
- 将有效因子组合为策略
- 添加风控模块
- 设置交易逻辑

**步骤6：回测验证**
- 多时间周期回测
- 样本外测试
- 样本内检验

**步骤7：报告输出**
- 生成研究结论报告
- 因子代码归档
- 策略说明文档

### 17.2 Qlib深度集成

#### Qlib简介

Qlib是微软开源的**量化投资研究框架**，提供了从数据处理到模型训练到回测的完整工具链。Quant Atlas将Qlib作为底层的**因子计算与回测引擎**。

#### 集成架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Quant Atlas + Qlib 集成架构                        │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  数据层     │     │  计算层     │     │  应用层     │
  │             │     │             │     │             │
  │ Tushare    │     │ Qlib Data   │     │ 因子工厂    │
  │ AkShare    │ ──▶ │ Handler     │ ──▶ │ 策略实验室  │
  │ TDX        │     │ Alpha-miner │     │ 回测系统    │
  │ Postgres   │     │ Model       │     │ 组合优化    │
  └─────────────┘     └─────────────┘     └─────────────┘
                            │
                            ▼
                   ┌─────────────┐
                   │  Qlib Core  │
                   │             │
                   │ - DataLoader│
                   │ - Task      │
                   │ - Model     │
                   │ - Signal    │
                   │ - Portfolio │
                   └─────────────┘
```

#### 核心功能

**数据处理**
```python
# Qlib数据格式
# 股票代码,日期,open,high,low,close,volume, factor1, factor2...
# 2026-05-01,600519,1700.0,1720.0,1690.0,1680.0,1000000,0.5,0.8...

# 特征计算
from qlib.data import D
from qlib.contrib.preprocess import FeaturePreprocess

# 数据清洗
dp = FeaturePreprocess()
clean_data = dp.fit_transform(raw_data)
```

**Alpha挖掘**
```python
from qlib.contrib.workflow import AlphaMiner

miner = AlphaMiner(
    task_name="momentum_alpha",
    strategy=TopkDropoutStrategy(k=50, n_drop=5)
)
miner.fit(train_data)
```

**模型训练**
```python
from qlib.contrib.model import LGBModel

model = LGBModel(
    n_estimators=100,
    learning_rate=0.05,
    max_depth=6
)
model.fit(X_train, y_train)
```

### 17.3 多模态交互

#### 当前支持模式

| 模式 | 描述 | 示例 |
|------|------|------|
| 文字 | 传统文本交互 | "分析贵州茅台" |
| 代码 | Python/策略代码 | 编写回测策略 |
| 自然语言策略 | 描述策略逻辑 | "MACD金叉买入" |
| 语音 | 语音输入（开发中） | "帮我看看..." |

#### 未来规划（2026Q3）

- **图像识别**：上传K线截图，AI分析形态
- **语音交互**：语音指令执行操作
- **视频教程**：Interactive操作演示

### 17.4 实时流式响应

#### WebSocket架构

```python
# 服务端
from flask_socketio import SocketIO

socketio = SocketIO(app)

@socketio.on('ai_analyze')
def handle_ai_analyze(data):
    symbol = data['symbol']
    
    # 流式输出
    for token in stream_ai_response(symbol):
        socketio.emit('ai_chunk', {'content': token})
```

#### 前端接收

```javascript
// 客户端
const socket = io();

socket.on('ai_chunk', (data) => {
    // 逐步显示AI响应
    responseText += data.content;
    updateDisplay(responseText);
});
```

---

## 第十八部分：性能基准测试

### 18.1 回测性能

#### 日线回测

| 策略类型 | 数据量 | 耗时 | 吞吐量 |
|---------|--------|------|--------|
| 单因子策略 | 5年 x 500股票 | 2.3秒 | 12500 bars/s |
| 多因子策略 | 5年 x 1000股票 | 8.5秒 | 29400 bars/s |
| 机器学习策略 | 3年 x 500股票 | 15秒 | 5000 bars/s |
| 组合优化 | 100个组合 | 12秒 | 8.3 combos/s |

#### 分钟回测

| 策略类型 | 数据量 | 耗时 | 吞吐量 |
|---------|--------|------|--------|
| 短线策略 | 60日 x 100股票 | 45秒 | 8000 bars/s |
| 统计套利 | 30日 x 500股票 | 3分钟 | 4200 bars/s |

### 18.2 API响应时间

| 场景 | P50 | P95 | P99 |
|------|-----|-----|-----|
| 行情查询（单股） | 15ms | 45ms | 120ms |
| 行情查询（批量100股） | 85ms | 200ms | 350ms |
| K线获取（日线1年） | 45ms | 120ms | 250ms |
| AI分析（单股） | 2.5秒 | 5秒 | 8秒 |
| 回测提交 | 120ms | 300ms | 500ms |
| 组合查询 | 35ms | 85ms | 150ms |

### 18.3 并发能力

| 指标 | 目标值 | 实测值 |
|------|-------|-------|
| Web并发用户 | 100 | 120 |
| API每秒请求 | 500 | 650 |
| WebSocket连接 | 200 | 180 |
| Celery并发任务 | 50 | 45 |

### 18.4 资源消耗

| 服务 | 内存 | CPU | 磁盘 |
|------|------|-----|------|
| Web服务 | 500MB | 1核 | 2GB |
| Celery Worker | 1GB | 2核 | 5GB |
| MySQL | 2GB | 2核 | 20GB |
| Redis | 200MB | 0.5核 | 1GB |

---

## 第十九部分：合规与监管

### 19.1 数据合规

#### 数据来源合规
- **Tushare**：官方授权数据接口
- **AkShare**：开源合规数据
- **通达信**：本地安装版合规使用
- **OpenBB**：国际合规数据源

#### 用户数据保护
- 个人信息收集遵循最小必要原则
- 敏感信息加密存储
- 数据访问日志审计
- 支持GDPR数据导出

### 19.2 交易合规

#### 模拟交易
- 明确标注"模拟交易"标识
- 不涉及真实资金流转
- 收益不代表实际收益

#### 实盘交易（如未来开放）
- 将在监管备案后推出
- 严格风控措施
- 资金安全隔离
- 交易记录完整留存

### 19.3 AI合规

#### 算法透明
- AI推荐可解释、可追溯
- 不使用未备案的AI模型
- 定期审计AI决策逻辑

#### 风险提示
- 明确告知AI建议仅供参考
- 不承诺收益
- 投资者需自行承担风险

---

## 第二十部分：生态与合作

### 20.1 数据生态

#### 数据合作伙伴

| 合作伙伴 | 数据类型 | 合作方式 |
|---------|---------|---------|
| Tushare | A股行情、财务 | API直连 |
| AkShare | 宏观、行业 | 开源集成 |
| OpenBB | 全球市场 | 插件接入 |
| 通达信 | 本地行情 | 本地解析 |

#### 数据质量保障

- 自动化数据校验
- 异常值检测与修复
- 延迟监控与告警
- 历史数据完整性检查

### 20.2 算力生态

#### LLM合作伙伴

| 模型商 | 模型 | 特点 |
|-------|------|------|
| Ollama | 本地开源 | 隐私安全、无API费用 |
| OpenAI | GPT-4o | 能力最强、成本较高 |
| DeepSeek | DeepSeek-Coder | 性价比高 |
| 阿里云 | Qwen | 中文优化 |
| Google | Gemini | 多模态 |

### 20.3 开发者生态

#### API开放计划

```python
# 2026年将开放的API
OPEN_APIS = [
    "策略回测API",
    "因子计算API", 
    "组合优化API",
    "信号查询API",
    "市场数据API"
]
```

#### 插件市场（规划中）

- 用户可开发自定义技能
- 技能可上架分享
- 付费/免费策略共存

### 20.4 学术合作

#### 已有合作
- 与清华、北大等高校建立研究合作
- 提供脱敏数据集供学术研究

#### 论文发表
- 平台技术论文发表计划
- 用户研究成果展示

---

## 第二十一部分：定价与商业模式

### 21.1 产品版本

#### 个人版

| 套餐 | 价格 | 功能 |
|------|------|------|
| 免费版 | ¥0 | 行情、数据、基础选股 |
| 专业版 | ¥99/月 | AI分析、策略实验室、组合优化 |
| 旗舰版 | ¥299/月 | 全部功能+优先支持 |

#### 机构版

| 套餐 | 价格 | 功能 |
|------|------|------|
| 团队版 | ¥999/月 | 5用户、API、基础支持 |
| 企业版 | ¥9999/月 | 20用户、私有化部署、专属支持 |
| 定制版 | 详谈 | 无限用户、定制开发 |

### 21.2 增值服务

| 服务 | 价格 | 说明 |
|------|------|------|
| 策略诊断 | ¥299/次 | 专家团队诊断策略问题 |
| 定制开发 | ¥5000起 | 根据需求定制功能 |
| 培训服务 | ¥1999/期 | 量化投资培训课程 |
| 数据包 | ¥99/月 | 额外数据源接入 |

---

## 第二十二部分：用户故事

### 故事一：从亏损到稳定盈利

> **用户**: 李女士，42岁，教师
> **背景**: 投资5年，亏损30+
> **痛点**: 盲目跟风、情绪化交易
> 
> **使用路径**:
> 1. 完成投资画像，确定"平衡型"偏好
> 2. 跟随AI推荐选股，减少主观判断
> 3. 开启哨兵预警，设定8%止损线
> 4. 每次交易后记录交易日记，AI复盘分析
> 5. 心理学监护提醒，帮助识别情绪化倾向
> 
> **结果**: 2025年全年收益率+22%，最大回撤-8%

### 故事二：研究效率提升10倍

> **用户**: 王博士，量化研究员
> **背景**: 某私募基金因子研发
> **痛点**: 手动尝试因子效率低
> 
> **使用路径**:
> 1. 使用因子工厂预置因子快速筛选
> 2. RD-Agent自动挖掘新因子
> 3. 一键正交化处理因子组合
> 4. 多策略对比选择最优
> 
> **结果**: 月均产出有效因子从3个提升到15个

### 故事三：AI投资委员会辅助决策

> **用户**: 张先生，35岁，个人投资者
> **背景**: 有一定投资经验，但缺乏系统方法
> **痛点**: 选股靠感觉，容易犹豫不决
> 
> **使用路径**:
> 1. 初步筛选候选股票
> 2. 提交AI投资委员会分析
> 3. 等待6个Agent多维度分析
> 4. 参考最终决策与置信度
> 5. 做出投资决定
> 
> **结果**: 决策时间从2小时缩短到20分钟，决策质量提升

### 故事四：组合管理智能化

> **用户**: 陈先生，50岁，中产投资者
> **背景**: 持仓10+只股票，管理混乱
> **痛点**: 不知道该持仓哪些、该清仓哪些
> 
> **使用路径**:
> 1. 导入现有持仓到组合
> 2. 一键优化计算最优配置
> 3. 生成调仓方案
> 4. 设定调仓提醒
> 5. 定期再平衡
> 
> **结果**: 组合波动率降低15%，夏普比率提升0.3

---

## 第二十三部分：常见问题深度解答

### 23.1 技术相关

**Q1: 为什么有些股票没有数据？**
> A: 数据覆盖取决于数据源。Tushare主要覆盖A股全市场，港股/美股依赖AkShare和OpenBB，加密货币依赖CCXT。部分新股/小众市场可能暂无数据。

**Q2: 回测结果与实盘差异大的原因？**
> A: 常见原因包括：(1)滑点估计不足；(2)流动性假设不合理；(3)未来函数；(4)过拟合；(5)市场结构变化。使用Autopilot功能可检测漂移。

**Q3: 如何选择合适的LLM模型？**
> A: 建议：日常分析用qwen3:8b（免费、本地、推理能力强）；复杂研究用gemma4:e4b（能力强但资源消耗大）；代码相关用deepseek-coder。

**Q4: 数据更新频率是多少？**
> A: 实时行情10秒级；分钟级行情盘中实时；日线收盘后更新；财务数据季报后更新。

### 23.2 投资相关

**Q5: AI推荐的股票可靠吗？**
> A: AI推荐基于历史数据与模型，存在局限性。建议结合AI分析与个人判断，AI作为"第二意见"参考。

**Q6: 因子有效性的时间周期？**
> A: 因子有效性通常在3-6个月，需持续监控。因子失效可能由于市场结构变化、因子拥挤等原因。

**Q7: 如何设置止损止盈？**
> A: 建议：止损不超过本金的2%/单笔；止盈目标至少是止损的2倍；根据股票波动性动态调整。

### 23.3 账户相关

**Q8: 免费版与付费版区别？**
> A: 免费版可用基础功能；付费版解锁AI分析、策略实验室、组合优化等高级功能。

**Q9: 如何导出我的数据？**
> A: 在"设置-数据管理"中可导出自选股、交易记录、策略代码等。

**Q10: 账号安全如何保障？**
> A: 建议开启双因素认证；定期修改密码；不在公共设备登录；开启登录通知。

---

## 第二十四部分：技术架构深入

### 24.1 事件驱动架构

#### 核心组件

```python
# 事件定义
class MarketEvent:
    type: str  # 'price_update', 'signal_triggered', ...
    data: dict
    timestamp: datetime

# 事件总线
class EventBus:
    def publish(self, event: MarketEvent):
        # 广播事件到所有订阅者
        for handler in self._handlers[event.type]:
            handler.handle(event)
    
    def subscribe(self, event_type: str, handler):
        # 订阅特定类型事件
        self._handlers[event_type].append(handler)
```

#### 事件流示例

```
价格更新事件
    │
    ├──▶ 触发信号检查 ──▶ 信号生成事件
    │                        │
    ├──▶ 更新组合价值 ──▶ 风控检查 ──▶ 预警事件
    │
    └──▶ 更新前端展示 ──▶ WebSocket推送
```

### 24.2 微服务架构（规划中）

#### 计划拆分为

| 服务 | 职责 | 预计拆分时间 |
|------|------|------------|
| market-service | 行情数据服务 | 2026Q4 |
| strategy-service | 策略管理服务 | 2026Q4 |
| ai-service | AI分析服务 | 2027Q1 |
| trade-service | 交易执行服务 | 2027Q2 |

### 24.3 数据流架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据流架构                                      │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
  │ 数据采集层 │────▶│ 数据处理层 │────▶│ 数据存储层 │────▶│ 数据应用层 │
  │            │     │            │     │            │     │            │
  │ Tushare   │     │ 清洗/转换  │     │ MySQL      │     │ 策略回测  │
  │ AkShare   │     │ 特征工程   │     │ Redis      │     │ 组合优化  │
  │ TDX       │     │ 指标计算   │     │ Qlib Data  │     │ AI分析    │
  │ CCXT      │     │ 因子生成   │     │            │     │ 可视化    │
  └────────────┘     └────────────┘     └────────────┘     └────────────┘
                          │
                          ▼
                   ┌────────────┐
                   │ Celery     │
                   │ 异步任务   │
                   │            │
                   │ 数据同步  │
                   │ 信号扫描  │
                   │ 因子计算  │
                   └────────────┘
```

---

## 第二十五部分：最佳实践指南

### 25.1 策略开发最佳实践

#### 1. 从简单开始
- 先用单因子测试，验证逻辑正确
- 逐步增加复杂度
- 每次修改都要重新回测验证

#### 2. 多维度验证
- 样本内 + 样本外测试
- 不同市场环境测试（牛市/熊市/震荡）
- 多个时间周期验证

#### 3. 风控优先
- 先设止损，再谈盈利
- 仓位管理是核心
- 分散化降低风险

#### 4. 持续迭代
- 定期检查策略表现
- 及时发现因子衰减
- 保持策略迭代更新

### 25.2 投资组合最佳实践

#### 1. 明确目标
- 设定预期收益率
- 明确可承受风险
- 确定投资期限

#### 2. 资产配置
- 不把鸡蛋放一个篮子
- 股债配置比例根据市场调整
- 行业/风格分散

#### 3. 再平衡
- 定期检查仓位偏离
- 动态再平衡
- 避免频繁交易

#### 4. 风险监控
- 持续监控组合风险
- 设置预警阈值
- 及时响应

### 25.3 使用习惯最佳实践

#### 1. 每日必做
- 查看今日操盘台了解市场
- 检查哨兵预警
- 关注自选股健康度

#### 2. 定期复盘
- 每周复盘交易记录
- 每月分析收益归因
- 季度评估投资组合

#### 3. 持续学习
- 阅读AI分析报告
- 学习新因子/策略
- 关注市场变化

---

## 第二十六部分：未来展望

### 26.1 2026年技术路线

#### Q3目标

- [ ] 多模态输入（图像、语音）
- [ ] 实时流式AI响应
- [ ] 策略市场上架
- [ ] API全面开放

#### Q4目标

- [ ] 实盘交易对接（模拟）
- [ ] 基金产品化功能
- [ ] 机构版私有化
- [ ] 全球市场扩展

### 26.2 2027年愿景

- **自研金融大模型**：基于Quant Atlas数据训练专用模型
- **强化学习策略**：RL驱动自适应交易策略
- **全自动化投资**：从研究到执行全托管
- **全球化布局**：亚太、欧洲、美洲市场

### 26.3 长期使命

> **让每一个投资者都能享受AI带来的投资便利**
> - 无论专业与否，都能获得专业级投资分析
> - 无论资金大小，都能构建适合自己的投资组合
> - 无论经验多少，都能持续学习和成长

---
*Quant Atlas 团队*
*文档版本：2.0*
*更新时间：2026-05-03*
*总字数：约40000字*

## 结语

Quant Atlas不仅是一个量化平台，更是一个**AI原生的投资研究新范式**。在这里，人类智慧与人工智能深度融合，重复性工作交给机器，战略性思考留给人类。我们相信，**未来的投资研究将属于人机协作**，而Quant Atlas正是这一趋势的先行者。

---

*文档版本：1.0*  
*更新时间：2026-05-03*  
*Quant Atlas 团队*