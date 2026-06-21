# 重构与能力提升路线图（refacter）

> 本文档对照 `docs/refacter.md` 原始愿景与当前代码落地状态，便于产品/研发对齐「已有什么、还缺什么」。

## 总结方向（不变）

通过 **响应式架构 + DTO 标准化** 夯实底座，重点打造以 **「每日推荐 + 产业链诊股」** 为核心的散户产品闭环。

---

## 1. AI 智能体进化

| 能力 | 状态 | 代码/入口 |
|------|------|-----------|
| 证据驱动路由（退市/风险一票否决，跳过部门） | ✅ 已落地 | `app/agents/evidence_router.py`、`integrated_graph.py` |
| 反应式黑板 | ✅ 已落地 | `app/agents/evidence_blackboard.py` |
| 自动胜率回溯 AutoValidator | ✅ 已落地 | `app/agents/auto_validator.py` |
| 分级模型调度 TieredLLM | ✅ 已落地 | `app/agents/research/graph.py` |
| 元学习权重自动调参 | ✅ 已落地 | Top3 `agent_memory` 调权；`evolve_prompts` Celery 周六定时 + `POST /system/retail-meta-learning-evolve`；模式注入 `DynamicPromptBuilder` |

---

## 2. 散户「AI 炒股助手」

| 能力 | 状态 | 代码/入口 |
|------|------|-----------|
| **每日 AI Top 3**（产业链、买卖区间、盈亏比、胜率） | ✅ 已落地 | `RecommendationService.daily_top`、`GET /api/v1/retail-assistant/daily-top-picks`、操盘台「今日 AI Top 3」 |
| **标准化诊股报告**（一句话结论 + 三色灯等） | ✅ 已落地 | `GET /api/v1/diagnosis/report`、`ai-analysis` 页 |
| **产业链智能图谱** | ✅ 已落地 | `IndustryChainMapService`、`GET /api/v1/industry-chain`、个股 `sector_context` |
| **心理卫士** | ✅ 已落地 | 自选/观察单/审计足迹（`trade_plan_adopt`）、`POST psychology-scan` 用户巡检、消息偏好、Celery 全量巡检 |
| **影子操盘** | ✅ 已落地 | 行情+持仓权重+用户投研画像（风险档位调追涨/减仓阈值）；逐标的 `picks` |
| 用户中心链路（简报/采纳/鲜度/任务） | ✅ 已落地 | `QAUserCenter`、`GET /api/v1/ux/decision-flow` |
| 证据链溯源 / 决策快照 / 计划软警告 | ✅ 已落地 | `supporting_evidence`（含 `report_citations` 研报）、`POST /decision/snapshots`、只读分享 `/share/decision/<token>`、`trade-plan` `soft_warnings` |

---

## 3. 高性能基础设施

| 能力 | 状态 | 说明 |
|------|------|------|
| Rust 指标引擎 | 🔶 部分 | `native_compute` / `quant_core`；快速预览 Sharpe 已接入 |
| Redis / 本地缓存 / 鲜度条 | 🔶 部分 | `DataFreshnessService`、集成中枢 |
| QuestDB / ClickHouse 替代 SQLite 海量 K 线 | 🔶 部分 | 读链 + Beat 16:35；操盘台 `integration_digest.timeseries_beat` 摘要 |
| WebSocket 实时行情 | 🔶 部分 | `base_app.js` + 操盘台自选 `quant:quote` 增量刷新 |

---

## 4. 多资产与全球化

| 能力 | 状态 | 说明 |
|------|------|------|
| A 股 / 港股 / 美股 / Crypto | ✅ 已落地 | `MarketCode` + Providers |
| 期货 / 外汇统一 MarketCode | 🔶 部分 | `MarketCode.FX` / `FUTURES`（benchmark/currency）；Provider 待接 |
| 全球联动（美股映射 A 股） | 🔶 部分 | `global-market` 相关能力 |
| 前端 i18n | ⏳ 规划中 | |

---

## 页面入口

| 页面 | 能力 |
|------|------|
| `/retail-assistant` | Top3、心理卫士、影子操盘、四维对照 |
| `/capabilities` | refacter 对照 + 决策链路自检（含散户探针）+ Beat 同步迷你面板 |
| `/architecture-roadmap` | 契约表 + refacter 对照 + 基础设施探针（Beat/QMT/QuestDB） |
| `/integration-hub` | 集成栈状态、QuestDB 同步、Beat/QMT/WebSocket |
| `/data-lake-health` | 数据湖 P95、同步进度、Beat 历史 |
| `/observability` | Trace 查询、集成栈 layers、Beat 同步历史时间线 |
| `/daily-workbench` | 今日 AI Top 3、Beat 迷你面板、自选 WS 报价刷新 |
| `/strategy-snapshots?tab=decision` | 决策研究快照列表；复制复盘链接 / 只读外链 |
| `/decision-snapshot/<id>` | 封存时刻复盘（需登录，非实时行情） |
| `/share/decision/<token>` | 只读分享复盘（免登录） |

---

## 快速验证 API

```http
GET /api/v1/retail-assistant/refactor-status
GET /api/v1/retail-assistant/daily-top-picks?market=CN&top_n=3
GET /api/v1/retail-assistant/meta-learning-status
GET /api/v1/retail-assistant/psychology-status
GET /api/v1/retail-assistant/psychology-guardian
POST /api/v1/retail-assistant/psychology-scan
POST /api/v1/system/retail-psychology-scan
POST /api/v1/system/retail-meta-learning-evolve?force=1
GET /api/v1/retail-assistant/shadow-mirror?symbol=600519&symbol=000858
GET /api/v1/ux/decision-flow?market=CN&symbol=600519
GET /api/v1/stocks/CN/600519/decision-brief
POST /api/v1/decision/snapshots
GET /api/v1/decision/snapshots/<id>
GET /api/v1/decision/snapshots/public/<share_token>
GET /api/v1/data/timeseries-health
GET /api/v1/data/timeseries-sync-history?limit=20&source=celery_beat
GET /api/v1/data/timeseries-bars?symbol=600519&days=60
POST /api/v1/system/questdb-ohlcv-sync
POST /api/v1/system/questdb-ohlcv-sync
POST /api/v1/system/timeseries-ohlcv-sync
GET /api/v1/data/timeseries-backfill-status
POST /api/v1/system/timeseries-ohlcv-backfill
GET /api/v1/data/websocket/status
GET /api/v1/integration/stack-status
GET /api/v1/execution/qmt-status
```

---

## Sprint 收敛说明（2026-06-16）

### 本轨道已闭环（Sprint 18 → 31）

| 范围 | 状态 |
|------|------|
| THS / 实验 API / 因子演化 UI | ✅ |
| QuestDB 同步 · Beat 16:35 · JSONL 历史 | ✅ |
| 集成中枢 / 数据湖健康 / 观测台 | ✅ |
| QMT simulation 标注 · 决策自检 18 探针 | ✅ |
| `QAUserCenter.mountBeatSyncMiniPanel` 统一展示 | ✅ |
| React 操盘台 `TimeseriesOpsCard` | ✅ |

**单一事实来源（基础设施 UI）**

- API：`timeseries-health`、`timeseries-sync-history`、`integration/stack-status`
- 组件：`QAUserCenter.mountBeatSyncMiniPanel`（capabilities / architecture-roadmap）
- 聚合：`GET /api/v1/retail-assistant/refactor-status` → `probes.timeseries.beat`

### 还剩多少 Sprint？

| 类型 | 数量 | 说明 |
|------|------|------|
| **本轨道必做** | **0** | 基础设施可观测已可运维闭环，不再按周开 Sprint |
| **可选收尾** | **0～1** | 仅当需要 Flask 版 `daily-workbench` 与 React 操盘台完全 parity 时，加一行 Beat 链路到现有页（非必须） |
| **Backlog（大 Phase，非 Sprint 碎片）** | 3～5 个主题 | 见下表，应单独立项而非「继续」式微 Sprint |

### Backlog（建议立项，勿再拆微 Sprint）

| # | 主题 | Sprint 32 状态 | 剩余工作 |
|---|------|----------------|----------|
| 1 | QuestDB/ClickHouse 数据面 | ✅ API + Celery + UI | 生产环境跑满 TDX 宇宙至 >100 万行 |
| 2 | WebSocket 全站 | ✅ 操盘台 + 自选 + 全景 | 其他行情页按需推广 |
| 3 | Rust 指标引擎 | ✅ `calc_metrics` 热路径 | 全引擎统一 + 基准报告 |
| 4 | Gemini 审计 Phase A（安全/CI） | 🔶 ruff/pip-audit/npm audit；CI Redis 已修 | 密钥扫描 gate（可选） |
| 5 | 产品 Backlog | 🔶 `FX`/`FUTURES` enum | Provider、前端 i18n、全球联动深化 |

---

## 后续优先项（建议）

1. **心理卫士**：已合并自选、观察单、审计与 `execution_feedback`（`strategy_id=retail_user_{id}`）；QMT 成交写入心理样本。
2. **影子操盘**：投研画像 + 组合成交成本/浮盈（`portfolio_trade_service`）参与减仓建议。
3. **Top 3 / 元学习**：观察单胜率 + `agent_memory` 调权；Prompt 演化已异步（`instance/meta_learning`）。
4. **基础设施**：QuestDB/ClickHouse 与 WebSocket 全站推送按 Phase 分批实施。
