# 01_dif 借鉴优化方案（结合 Quant Atlas 实例）

> **来源：** `docs/01_Requirements/01_dif.md`  
> **对照：** 仓库现状（含 2026-08 SRS Trading OS 已落地项）+ 产品决策 D1–D6  
> **原则：** 借鉴模式与门禁，不整仓替换引擎；A 股优先；安全先于进化 UI。

---

## 0. 总判（一句话）

`01_dif` 的「四步走」与 Quant Atlas **高度同构**——步骤一/四（前端交互、MCP、统一路由、红线、数据主链）已约 **3.5–4/5**；步骤二锦标赛约 **3.5** 但缺 **Bias→上线硬门禁**；步骤三 ML/RL 约 **0–2.5**，是最大可借鉴缺口。  
下一批应 **锁门禁 + Paper 进化闭环**，再补 **Feature Pipeline**，勿追 Vue / 完整 vnpy / TradeMaster 全套。

---

## 1. 与 SRS / 已交付的关系

| DIF 主张 | SRS 决策 | 仓库已有（示例路径） | 借鉴姿态 |
|----------|----------|----------------------|----------|
| Vue3 + 侧边 AI | **D1：React** | `frontend/.../AiAssistantDrawer.tsx`、`PriceHistoryChart.tsx` | **已对齐交互；勿迁 Vue** |
| FastMCP 交易面 | D4 | `scripts/mcp-servers/quant-atlas-mcp/` | **已有三工具；补门禁串联** |
| 多 Agent 辩论 | — | `app/agents/research/` | **已强；补上线硬连接** |
| TradeSight 锦标赛 | — | `tournament/gates.py`、`offline_runner`、Beat | **硬门槛已有；缺 Bias/运维默认开/质量回写** |
| FreqAI 特征管线 | — | qlib / `model_zoo` 启发式 | **应借鉴管线形态；勿嵌 Freqtrade 内核** |
| TradeMaster RL | — | 无 | **P2 研究旁路** |
| OpenAlgo/vnpy 路由 | D2 QMT | `contracts.py`、`borderless_router`、`qmt_*` | **契约已有；深联调 QMT** |
| 红线（风控/禁提现/沙箱/TG） | SRS P0 | `risk_guard*`、`exchange_api_key_policy`、`STRATEGY_SANDBOX`、`telegram_alerter` | **加固持久化与全路径** |
| Timescale+Redis | D3 | dayk sync / Redis / quote_latency_slo | **观测→告警；勿恢复 CH 入库主路径** |

已落地的 SRS 计划：`docs/superpowers/plans/2026-08-06-srs-trading-os-refactor.md`（主路径收束）。本方案是 **DIF 视角的下一波增量**，不重复重做 B–E。

---

## 2. 四步走 × 成熟度（0–5）

| DIF 步骤 | 成熟度 | 项目实例 | 主要差距 |
|----------|--------|----------|----------|
| 一 · QuantDinger 式 UI | 4 | SPA Layout + AI 抽屉 + MA/成交量切换；Jinja 双轨 | 非 Vue；进化可视化未做 |
| 一 · 量化 MCP | 3.5 | `get_historical_kline` / `execute_backtest` / `get_portfolio_status` + wind/ifind/akshare MCP | 回测结果未自动入 Tournament 候选 |
| 二 · AI-Trader 辩论 | 4 | Supervisor + Analyst + Bull/Bear + Risk | 与实盘门禁未硬连 |
| 二 · Bias / Risk 门禁 | Bias 2 / Risk 图内 4 | `LookAheadBiasDetector` 存在但未串门禁 | **未检偏可进 Paper** |
| 二 · TradeSight 锦标赛 | 3.5 | Sharpe>1.8 & MDD&lt;12% → Paper；Beat 默认关 | 指标回写弱；无热力图/进化树 |
| 三 · FreqAI Feature Pipeline | 2 | qlib Alpha / model_zoo LightGBM 目录 | 无可插拔特征规范 + 训练调度 |
| 三 · RL Sim2Real | 0–1 | — | 不作为 A 股近期主路径 |
| 四 · 统一路由 | 4 | OrderRequest + Borderless + QMT/CCXT | IBKR/CTP stub（P2） |
| 红线 + 数据 SLO | 3.5–4 | Risk Guard / 禁提现 / 沙箱 / TG / Timescale / 50ms 观测 | Guard 内存态；SLO 非硬闸 |

---

## 3. 三类借鉴清单

### 3.1 已对齐（保持，少动）

1. React SPA + AI 侧栏 + Lightweight Charts 叠加均线  
2. `quant-atlas-mcp` 三工具 + 数据 MCP 目录结构  
3. `app/agents/research` 多 Agent 辩论（不依赖 TradingAgents-CN 包）  
4. Tournament 硬门槛 → Paper；统一 Order 契约 + QMT/CCXT  
5. Timescale + CSV + qlib 权威写入；Risk Guard / 沙箱 / 禁提现策略骨架  

### 3.2 应借鉴（抽模式进现有架构）

| # | 借鉴自 | 落地到 Quant Atlas | 成功标准 |
|---|--------|-------------------|----------|
| B1 | AI-Trader / DIF 安全观 | `LookAheadBiasDetector` **硬串** MCP 回测 → 候选池 → Tournament | 未通过 Bias 的策略不可入 Paper |
| B2 | TradeSight 运维 | 默认可开 Beat + Paper 晋级指标回写（非空 `total_return`） | 夜间跑一圈有可审计记录 |
| B3 | FreqAI Feature Pipeline | 在 qlib/自研上定义 **FeatureSpec**（日频因子归一化）→ LightGBM 训练任务 | 一条可调度训练→注册模型路径 |
| B4 | OpenAlgo 风控中枢 | Risk Guard **Redis 快照** + 全下单入口 `ensure_order_allowed` | 重启不丢日回撤/连亏态 |
| B5 | QuantDinger MCP 闭环 | `execute_backtest` 成功且过 Bias → 写入 Tournament 候选 | NL/MCP 策略可进淘汰池 |

### 3.3 勿照搬

1. 整仓 Vue3 重写（违反 D1）  
2. 嵌入完整 vnpy / Freqtrade 替代现有回测与路由  
3. 优先做 TradeSight 热力图/进化树 UI（先于硬门禁与指标回写）  
4. TradeMaster 全套 RL 作为默认实盘路径  
5. IBKR/CTP/Alpaca 抢 QMT 近中期优先级；恢复 CH/QuestDB 入库主路径  

---

## 4. A 股优先实施路线

### P0 — 安全与进化闭环（约 1–2 周量级）

1. **Bias 硬门禁**  
   - 接线：`validate_backtest_data` / `LookAheadBiasDetector` → Tournament 入池 API / MCP `execute_backtest` 后置  
   - 失败：明确错误码，禁止 Paper 晋级  
2. **Risk Guard 加固**  
   - 日回撤/连亏态 → Redis；审计 `borderless_router` 与 QMT/CCXT 入口均调用  
   - Telegram：文档化必配项 + 一次联调清单  
3. **Tournament 运维默认路径**  
   - 文档推荐 `STRATEGY_TOURNAMENT_CELERY_BEAT=1`（仍可关）  
   - Paper 晋级写入真实指标摘要（Sharpe/MDD/样本区间）  

### P1 — 特征与执行深联调（约 2–4 周）

1. **Feature Pipeline v0**（FreqAI 形态、qlib 实现）  
   - Domain：`FeatureSpec` + 防 look-ahead 约定  
   - Task：日频训练 Job → 模型产物路径注册（可先启发式，再真 LightGBM）  
2. **QMT × Risk Guard × 订单持久化** 仿真/实盘验收清单  
3. **MCP → Tournament 候选** 自动写入（质量过滤：Bias + 最低样本量）  

### P2 — 可视化与扩展执行

1. Tournament 轻量 Dashboard（晋级表/淘汰原因；**不做**全套进化树） — **已落地**：观测台面板 + `GET/POST /strategy/tournament/*`  
2. IBKR/CTP：仿真 + dry-run + **真会话 placeOrder** — **已落地**：`broker_session` + CONFIRM_LIVE；A 股现货仍 QMT  
3. RL：可选研究旁路，默认不进 live — **已落地**：tabular Q + `/strategy/rl-research/*`；实盘仍禁止  

---

## 5. 与 DIF「三阶段」映射

| DIF 阶段 | Quant Atlas 现状 | 下一跳 |
|----------|------------------|--------|
| MVP（稳健回测+实盘） | 自研回测 + QMT 骨架 + 数据主链 ≈3.5–4 | QMT 联调验收 + Guard 持久化 |
| AI 增强（MCP+NL） | SPA 抽屉 + research + MCP ≈3.5 | Bias + MCP→候选池 |
| 自动化进化 | Tournament→Paper ≈2.5–3.5 | Beat 指标回写 + Feature Pipeline；RL 后置 |

---

## 6. 资产优先级回答（DIF 文末问题）

**优先覆盖：A 股（含 QMT 近中期执行）**。  
理由：数据主链（TDX→Timescale/CSV/qlib）、研究 Agent、Tournament/Paper、SRS D2 均已围绕 A 股收敛。Crypto（CCXT）保持第二轨；美股/IBKR、期货/CTP 为 P2。

---

## 7. 验收清单（本方案完成的定义）

- [x] Bias 失败策略无法进入 Paper / Tournament 晋级  
- [x] Risk Guard 重启后日态可恢复；关键下单路径有闸门测试  
- [x] 至少一次夜间 Tournament Beat 产出可审计 JSON/DB 记录（`instance/tournament_runs/`）  
- [x] Feature Pipeline v0：一份 FeatureSpec + 一次可重复训练任务  
- [x] `REFACTORING_LOG.md` 与本文件勾选同步；不宣称未达标的「10 年分钟 ≤10s」  

### 实施记录（2026-08-06）

| 优先级 | 落地 |
|--------|------|
| P0 Bias | `bias_detector` 硬门禁；Tournament `bias_passed`；MCP `execute_backtest` 扫描/报名 |
| P0 Guard | `RedisRiskGuardStore` + `risk_guard_factory`；QMT/CCXT/Borderless 共用 |
| P0 Tournament | Paper 指标回写；Beat 审计 JSON；`.env.example` 运维说明 |
| P1 Feature | `FeatureSpec` + 启发式 / **LightGBM（auto）** 训练任务 `feature_pipeline_tasks` |
| P1 MCP→池 | `enroll_tournament_candidate` + MCP `enroll_tournament` |
| P1 QMT | `docs/ops/QMT_RISK_GUARD_CHECKLIST.md` + executor 闸门 + **联调探针**（CLI/API/观测台） |
| P2 轻量 | `GET/POST /api/v1/strategy/tournament/*` + 观测台晋级/淘汰面板；IBKR/CTP 契约测试；RL 延期 |
---

## 8. 建议执行方式

1. 用户确认本方案优先级（默认 P0→P1→P2，A 股）  
2. 用 `writing-plans` 把 P0 拆成带测任务（或直接 `subagent-driven-development`）  
3. 每项落地后追加 `REFACTORING_LOG.md` 日期小节  

---

## 9. 收束状态（2026-08-07）

**P0–P2 已实施完毕**（RL 仅研究旁路；TradeMaster 全套/RL 实盘仍延期）。

| 项 | 状态 |
|----|------|
| Bias / Guard / Tournament / MCP / Feature Pipeline / 看板 / IBKR·CTP 契约+仿真 | 已完成 |
| 行情 SLO ↔ SmartDegrade 阈值对齐 + 观测台 actionable 提示 | 已完成（续） |
| Feature Pipeline Celery Beat（`FEATURE_PIPELINE_CELERY_BEAT`） | 已完成（续） |
| Feature Pipeline LightGBM + **真实 CN 日K 优先训练** + **推理打分** | 已完成（续） |
| RL **研究旁路**（tabular Q，默认不进 live） | 已完成（续） |
| TradeMaster 全套 / RL **实盘** | **仍延期** |
| SRS D6 合成 10y 分钟向量化基准 | 已完成（续）：`minute_engine` + `instance/backtest_minute_10y_vectorized.json`（~0.01s，非真实行情） |
| IBKR/CTP **仿真**（OrderRequest + Risk Guard + `sim_ready`） | 已完成（续） |
| IBKR/CTP **真对接最小里程碑**（TCP/SDK 探针 + live dry-run + 观测探针） | 已完成（续） |
| IBKR/CTP TWS/CTP **真会话报单接线** | 已完成（续）：`ib_insync` / 注入 trader + CONFIRM_LIVE 闸门 |

运维开关速查：`STRATEGY_TOURNAMENT_CELERY_BEAT`、`FEATURE_PIPELINE_CELERY_BEAT`、`RL_RESEARCH_CELERY_BEAT`、`RL_LIVE_ENABLED=0`、`RISK_GUARD_*`、`QUOTE_LATENCY_SLO_MS` / `QUOTE_DEGRADE_*`、`IBKR_*` / `CTP_*`。
