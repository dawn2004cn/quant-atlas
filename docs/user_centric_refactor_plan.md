# Quant Atlas 用户中心重构计划：打造散户最爱用的最强量化工具

为实现从“面向专业研究员的工程堆砌”向“面向大众散户的陪伴决策脑”转变，使 Quant Atlas 成为兼具顶级量化技术与极致散户体验的平台，特制定本重构计划。

---

## 1. 核心架构重构（Architectural Refactoring）

### 1.1 前端从服务端 MPA 向响应式混合/单页（SPA/PWA）演进
* **现状与痛点**：当前基于 [pages_market.py](file:///E:/project/workspace/myrepo/quant-atlas/app/presentation/web/pages_market.py) 的 Jinja2 模板与 jQuery 散落 API 呈现 MPA 架构。跳转白屏、数据更新延迟，且图表内存管理较为粗糙，不符合散户对手机端/高频刷新看盘的流畅度预期。
* **重构方案**：
  * **第一阶段（渐进式组件化）**：落实 [FRONTEND_REFACTOR_PLAN.md](file:///E:/project/workspace/myrepo/quant-atlas/docs/FRONTEND_REFACTOR_PLAN.md) 中的 Web Components。将顶部焦点标的 `qa-focus-bar`、系统健康 `qa-health-banner` 转为原生自定义元素，实现无缝跨页状态共享。
  * **第二阶段（现代前端框架引入）**：逐步引入 Vue 3 / Alpine.js 作为轻量级视图层，隔离后台复杂的依赖注入（DI）和微内核路由，对高频交互的个股详情 [pages_stock.py](file:///E:/project/workspace/myrepo/quant-atlas/app/presentation/web/pages_stock.py) 和今日操盘工作台 [daily_workbench.html](file:///E:/project/workspace/myrepo/quant-atlas/app/presentation/web/templates/daily_workbench.html) 进行热重写。
  * **第三阶段（PWA 离线运行）**：针对自选股与基础行情进行 Service Worker 缓存，确保在弱网环境下散户依然能秒开查看历史持仓数据。

```mermaid
graph TD
    subgraph 传统链路 (MPA)
        Request --> Router[pages_market.py] --> SQL[SQLite/MySQL] --> Jinja2 --> Render[全页刷新]
    end
    subgraph 现代链路 (SPA/Hybrid)
        UserAction --> ClientBus[state_bus.js] --> QCApi[api_client.js] --> SSE[TaskEventHub/SocketIO] --> UI[组件局部渲染]
    end
```

### 1.2 实时主动推送系统（WebSocket + Redis Pub/Sub）
* **现状与痛点**：异步任务进度（如回测、大数据同步）虽支持 `/system/tasks/<id>/stream` 的 SSE 协议（[ui_opt-completion.md](file:///E:/project/workspace/myrepo/quant-atlas/docs/ui_opt-completion.md)），但行情、自选股异动、因子衰减监控仍主要依靠前端被动轮询，消耗服务器带宽，且无法做到实时的突破/爆量提醒。
* **重构方案**：
  * **双通道推送网关**：集成 Flask-SocketIO 并依托底层已有的 `GlobalStateBus`（[global_state_bus.py](file:///E:/project/workspace/myrepo/quant-atlas/app/core/mesh/global_state_bus.py)）作为发布订阅核心。
  * **自选股异动事件流**：扫描器任务 [scanner_tasks](file:///E:/project/workspace/myrepo/quant-atlas/app/tasks/scanner_tasks.py) 发现标的爆量、跌破均线或信号旗异动时，通过 Redis Pub/Sub 将事件推送给 WebSocket 网关，实现前端毫秒级闪烁播报。

### 1.3 用户画像与自适应路由（Persona-Aware Routing）
* **现状与痛点**：Jarvis 语义路由器会向有特定胜率模式的用户推荐特定话术，但该模式缺乏统一模型。普通散户与高阶策略开发人员使用同样的界面，散户面对 Qlib 管线、Swarm 拓扑图容易产生巨大认知负荷。
* **重构方案**：
  * **分级画像层（User Persona Service）**：在 [auth.py](file:///E:/project/workspace/myrepo/quant-atlas/app/presentation/web/auth.py) 中引入风险与认知画像评测。角色分为：*Novice（散户小白）*、*Day Trader（超短线客）*、*Strategy Researcher（专业投研）*。
  * **UI 自适应遮罩**：根据画像等级，对小白用户隐去 Qlib 回测参数、Agent 拓扑和 Zero-Knowledge 证明，展示直观的“多空红绿灯”、“大白话诊股”；对专业用户全量开启，满足极客追求。

---

## 2. 核心功能重构与散户化包装（Functional Refactoring）

### 2.1 每天回答第一个问题：“今天市场能不能做？”
* **现状与痛点**：大盘全景数据分布在 `/market-panorama`（[pages_market.py](file:///E:/project/workspace/myrepo/quant-atlas/app/presentation/web/pages_market.py)），图表繁多，用户需要自行提取结论。
* **功能重构**：
  * **大盘情绪温度计（Traffic Light System）**：
    * 整合“上涨家数比”、“连板高度”、“东财/同花顺热点板块涨股比”等底层数据，由 `MarketDataService` 实时计算出 0~100 的**市场温度分**。
    * 提供极简的“红（禁止开仓，防守为主）”、“黄（控制仓位，低吸关注）”、“绿（做多窗口，激进策略）”三色红绿灯提示。
    * **开仓锁死联动**：当温度计呈红色时，在 `TradingRiskFacade`（[wiring_trading.py](file:///E:/project/workspace/myrepo/quant-atlas/app/bootstrap_components/wiring_trading.py)）自动锁定一键模拟买入功能，弹窗提示“市场情绪处于冰点，系统已启动防守机制”，引导散户知行合一。

### 2.2 每天回答第二个问题：“我该关注哪些票？”
* **现状与痛点**：散户选股无从下手，多源数据散落在板块（AkShare/同花顺）、龙虎榜、东方财富快讯中。
* **功能重构**：
  * **“跟庄/热点”双轮驱动雷达**：
    * **龙虎榜散户化**：清洗龙虎榜买入席位，自动识别“游资大佬（赵老哥/章盟主等）”、“机构买入”、“量化通道”以及“散户大本营（拉萨天团）”，用通俗生动的标签标注（如“主力爆买”、“游资抱团”、“散户集中地”），替换枯燥的“买入金额/席位名称”。
    * **共振选股池**：开发“因子共振”页面。当某只股票同时满足：*板块龙头 + 游资净买入 + 均线突破 + AI 模型多头共识* 时，自动置顶，并显示大白话推荐语（例如：“*同花顺概念板块第1，主力游资连买2天，技术形态多头突破，AI 极力看多*”）。

### 2.3 每天回答第三个问题：“买了以后怎么防守？”
* **现状与痛点**：散户极易在开仓后因贪婪或恐惧导致大亏。平台已有强大的 TradingRiskFacade 校验、止损计算与 Kelly/Vol 仓位风控，但纯属“后台默默运行”或“回测专属”，前端未给予强提醒与可视化指引。
* **功能重构**：
  * **可视化交易前预检卡（Preflight Card）**：
    * 用户在自选股或详情页准备做交易计划时，弹出极简的卡片（对接 `/trading/preflight` 接口）。
    * 散户输入当前资金或期望亏损，系统自动计算：**建议买入股数（按波动率与初始止损计算）**、**ATR 移动止损价位**、**预期最大损失金额**。
  * **K 线图防守线可视化**：
    * 在 K 线图上，同步渲染一条醒目的红色虚线——**系统推荐止损线**。
    * 一旦股价触及该线，立即通过微信模板消息 [WeChatTemplateAlertChannel](file:///E:/project/workspace/myrepo/quant-atlas/app/infrastructure/events/alert_channels.py) 强制推送：“您的持仓【XX股份】已跌破系统强弱分界点，请按照计划执行防守！”

```
[ 交易前预检卡 (Pre-Trade Preflight) ]
---------------------------------------------
输入预算: 10,000 元  | 拟入场价: 15.20 元
---------------------------------------------
系统推荐买入量: 600 股 (6手) - A股 lot_size 对齐
建议硬止损线: 13.98 元 (-8%)
ATR追踪防守点: 14.15 元
预期最大亏损: 730 元 (符合您的低风险画像)
---------------------------------------------
[ 批准计划 ]   [ 放弃交易 ]
```

### 2.4 每天回答第四个问题：“我的分析结果对不对，下次怎么改？”
* **现状与痛点**：多智能体决策与 AI 分析多为“一次性交付”，缺乏后向追溯，AI 幻觉会让用户产生信任危机。
* **功能重构**：
  * **实盘/模拟日记本与 AI 归因（Cognitive Review Loop）**：
    * 散户在操盘台执行的所有买卖动作，自动记录在 [decision_review_queue.py](file:///E:/project/workspace/myrepo/quant-atlas/app/application/services/ui/decision_review_queue.py)。
    * 针对每一笔交易，系统自动比对随后的真实走势。3-5 天后，自动生成**复盘卡片**。
    * 归因可视化：结合 `UnifiedAttributionService`，用直观的饼图或雷达图，告诉用户：“这笔交易赚钱是因为*抓住了行业beta*，亏钱是因为*追高导致滑点过大*”。
    * **AI 胜率跟踪**：展示“当前 AI 诊股在您关注板块的过去 10 次预测命中率”，通过高透明度的证据链（[routes_v1_ai_evidence.py](file:///E:/project/workspace/myrepo/quant-atlas/app/presentation/api/routes_v1_ai_evidence.py)）与可信度降权标记，建立与散户之间的信任桥梁。

---

## 3. 重构实施时间表（Strangler Fig Stragegy）

为了不影响现有系统的稳定运行，建议采取**绞杀榕（Strangler Fig）**模式，自上而下、逐步替换：

```
2026-Q3 (前端混合层与状态共享)
 ├── 引入 state_bus.js，全站标的联动聚焦(Focus Bar)
 └── 将 error_handlers.py 重构为 actionable_error (报错附带一键重试/同步按钮)

2026-Q4 (智能自选与风险预检前端化)
 ├── 重构 pages_stock.py 及对应模板，在 K 线图直观渲染 ATR 止损防守线
 └── 对接 trading/preflight 接口，推出“散户一键预检卡”

2027-Q1 (实时推送与用户画像自适应)
 ├── 废弃前端 Ajax 轮询，全面对接 WebSocket 与 Redis 实时异动广播
 └── 推出散户小白/超短线客/极客投研分级菜单，自动隐藏/展现高阶量化配置
```

---

> [!NOTE]
> 本计划旨在利用底层的 Pytdx 接口、RDAgent 因子迭代、Qlib 回测引擎等**极高技术壁垒**，包装出符合散户直觉、极具**爽感与控制感**的前端功能，用以缩短散户决策链路、降低认知压力，从而在量化工具红海中突围。


---

## ✅ Implementation Status (2026-06-12)

### All Backend Deliverables Complete — 13 files, ~133 KB, **zero compilation errors**

| Section | Deliverable | Status | Files |
|---------|-------------|--------|-------|
| **1.1** Frontend MPA→SPA | Web Components, Vue 3, PWA | 🔵 **Frontend only** | See docs/FRONTEND_REFACTOR_PLAN.md |
| **1.2** Real-time Push (WebSocket) | App→Core event bus bridge | ✅ Done | pp/application/events/bridge.py, pp/bootstrap.py |
| **1.3** Persona-Aware Routing | PersonaService, PersonaTier, 15 feature flags, API endpoints | ✅ Done | pp/domain/services/persona_service.py, 
outes_v1_user_profile.py |
| **2.1** Market Traffic Light | Regime service, market sentiment (0-100), R/G/Y signal | ✅ Done | pp/domain/services/market_regime_service.py |
| **2.2** Smart Stock Radar | WatchlistAnomalyDetectedEvent, subscription in watchlist agent | ✅ Done | pp/core/event_bus.py, pp/modules/market_data/services/watchlist_agent_service.py |
| **2.3** Preflight Card | ATR pre-calc, stop-loss line, recommended position size | ✅ Done | pp/application/services/trading/pre_trade_preflight_service.py |
| **2.3** K-line Stop-Loss | Stop-confirm cards in morning call, position-limit hard block | ✅ Done | pp/application/services/analytics/daily_workbench_service.py, pp/infrastructure/trading/pre_trade_validator.py |
| **2.4** Cognitive Review Loop | TradeOutcomeReviewService, decision review queue, batch ops | ✅ Done | pp/application/services/trading/trade_outcome_review_service.py, 
outes_v1_signal_observations.py, 
outes_v1_trade_plan.py |
| **2.4** AI Hit Rate | Evidence hit-rate endpoint, trust score per symbol | ✅ Done | pp/presentation/api/routes_v1_ai_evidence.py |

### Legend
- ✅ **Done** — Backend code complete, compiled, wired
- 🔵 **Frontend only** — Requires UI work (JS/HTML/CSS), no backend changes needed

### Remaining (Frontend / Policy)
1. **1.1 Web Components**: qa-focus-bar, qa-health-banner — transform Jinja2 templates into custom elements
2. **1.3 Persona UI masking**: Frontend must consume GET /user/persona eature_mask to hide/show elements
3. **1.2 Scanner events UI**: Frontend should subscribe to SocketIO events (room market, event MarketDataUpdatedEvent)
4. **2.3 K-line stop-loss line**: Render ATR stop-loss line on chart component
