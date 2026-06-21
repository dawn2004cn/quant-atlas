# Refactoring & Development Log

This file is a consolidated chronological log of all major architecture refactorings, feature integrations, and bug fixes.

---

## 2026-06-21 (Flask → SPA 迁移：M1 + M2 批量完成)

### 背景
根据 [SPA 迁移设计文档](docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md)，将 Flask Jinja SSR 页面逐步迁移至 React SPA。本次完成 **M1（14 页）+ M2（27 页）+ 预迁（11 页）= 52 页**，覆盖设计文档中全部 M1/M2 以及部分已存在的页面。

### M1 — 核心工作流 (14 页)
新增 `pages/Portfolio.tsx`、`PortfolioDetail.tsx`、`HotSectors.tsx`、`GlobalRadar.tsx`、`SelfStocks.tsx`、`StockSelector.tsx`、`LongTermSelect.tsx`、`StrategyCompare.tsx`、`StrategySnapshots.tsx`、`DecisionSnapshot.tsx`、`NLStrategy.tsx`、`StrategyWizard.tsx`、`TdxBlocks.tsx`

- 每个页面使用 `useSWR` + `apiFetchV1` 数据获取
- 完整处理 loading (PageSkeleton)、error (alert)、empty (warning) 三种状态

### M2 — AI/流式/协作/数据类 (27 页)
| 分类 | 页面 |
|------|------|
| AI（8） | AIChat, AIAnalysis, AIResearchReport, AIHedgeFund, AICommitteeDashboard, AICommitteeSelection, AIInvestmentCommittee, WarRoom |
| 协作（10） | CollaborationWorkspace, MessageCenter, TaskCenter, TaskDetail, SwarmDashboard, SwarmDesigner, SignalObservations, VoiceBriefing, ResearchCanvas, ResearchPipeline |
| 数据（9） | AlertCenter, YanbaoHub, LonghuBang, SelectionResult, InvestmentManagers, InvestmentManagerDetail, ExpertTeams, AgentCenter, DecisionReplaySpace |

### 预迁页面（11 页）
Sprint 13/H 阶段已存在的 SPA 页面：Dashboard, Login, Backtest, MarketPanorama, RunHistory, ExperimentReport, Marketplace, StockDetail, AlphaFactory, SignalFlag, NotFound

### Flask 重定向
- 所有迁移页面对应的 Jinja 路由替换为 `redirect("/app/<path>", code=302)`（灰度阶段）
- 涉及文件：`pages_market.py`、`pages_stock.py`、`pages_ai.py`、`pages_admin.py`

### 构建指标
- `npm run build`：3.00s，194 模块
- JS bundle：404 KB (gzip 130 KB)
- CSS：123 KB (gzip 20 KB)
- 无 TypeScript 错误（仅剩预存 Layout.tsx 1 个）

### 剩余 M3 页面（~17 页待迁）
user_tiers_*, ui_showcase, shadow_account, feature_retired, architecture_roadmap, capabilities, observability, integration_hub, register, profile, users_manage, stocks_manage, factor_repository, factor_detail, factor_evolution, truth_droplet, zen_dashboard, zen_terminal, portfolio_resonance, optimize, retail_assistant, professional_workbench, user_spectrum_hub

## 2026-06-20 (UI/CSS 迁移收尾：auth 外置 + 计划文档)

### 交付
- **`static/css/pages/auth.css`**：`login.html` / `register.html` 内联 `<style>` 外置（~160 行），类名前缀 `login-*` / `auth-*` / `register-*` 避免与 `common.css` 冲突
- **`docs/UI_CSS_MIGRATION_PLAN.md`**：新增 §0 完成状态 + §0.1 保留 `style=` 清单；DoD 勾选更新

### 指标
| 指标 | batch10 后 | 收尾后 |
|---|---|---|
| 模板 `<style>` 块 | 2（login/register） | **0** |
| 静态 `style=` | 41 | **41**（均为动态/宏） |
| `pages/*.css` | 19 | **20** |

---

## 2026-06-20 (UI/CSS CI 门禁 + 双主题验收清单)

### 交付
- **`scripts/check_template_inline_styles.py`**：禁止非 `error_*` 模板含 `<style>`；`style=` 仅允许 19 个文件且计数不超过 baseline（合计 41）
- **`.github/workflows/ci.yml`**：`compile` job 增加 inline style gate
- **`docs/UI_CSS_THEME_VERIFICATION.md`**：导航 / 操盘台 / 个股 / 回测 双主题走查表
- **`tests/smoke/test_template_inline_styles.py`**：CI gate 的 pytest 封装
- **`tests/smoke/test_dual_theme_pages.py`**：四路径双主题结构验收（页级 CSS、壳层、token 文件）

---

## 2026-06-20 (深挖 batch4–7：Alpha/研究页 + 组件清扫)

### 交付
- **`scripts/deep_inline_cleanup_batch4.py`**：`alpha_factory`/`marketplace`/`ai_committee_dashboard`/`factor_evolution`/`moments` 静态 `style=` 清零
- **`scripts/deep_inline_cleanup_batch5.py`**：`ai_investment_committee`/`quant_lab`/`profile`/`global_radar`（热力图动态色保留）
- **`scripts/deep_inline_cleanup_batch6.py`**：`selection_result`/`research_pipeline`/`ai_hedge_fund`/`expert_teams` + `common.css` 工具类
- **`scripts/deep_inline_cleanup_batch7.py`**：`resonance_meter`/`shadow_account`/`nl_strategy`/`attribution_dashboard`/`swarm_dashboard`/`strategy_wizard`/`signal_observations`/`task_center`

### CSS 增补
- `research.css`：`comm-*`/`ql-*`/`rp-*`/`ahf-*`/`et-*`/`swd-*`/`sw-*`；`.ai-group-header { cursor: pointer }`
- `system.css`：`pf-*`/`sh-*`/`nl-*`
- `market.css`：`gr-*`
- `strategy.css`：`sr-*`
- `portfolio.css`：`ad-*`
- `stock-detail.css`：`rm-*`
- `common.css`：`flex-wrap-gap-*`/`grid-gap-16` 等

### 清扫后
| 指标 | batch3 后 | batch7 后 |
|---|---|---|
| 全模板 `style=` | 532 | **~198** |

---

## 2026-06-20 (深挖 batch10：收尾静态 + 演示宽度类)

### 交付
- **`scripts/deep_inline_cleanup_batch10.py`**：`zen_terminal`、`user_spectrum_hub`、`task_detail`、`strategy_compare`、`research_canvas`、`portfolio_resonance`、`experiment_reporter`、`evidence_replay`、`ai_research_report`、`ai_chat`、`agent_lab`、`agent_center`、`users_manage`、`yanbao_hub`、`hot_sectors`、`moments`、`voice_briefing`、`truth_droplet` 组件；投委会/集成中心演示 width 改 `w35`–`w62`/`w40` 类

### 清扫后
| 指标 | batch9 后 | batch10 后 |
|---|---|---|
| 全模板 `style=` | ~73 | **~41**（均为动态/宏/Pine 脚本） |
| 可清零静态页 | 20+ | 本批 **18 页/组件 → 0** |

### 仍保留 `style=`（有意）
- `skeleton.html`（8）：Jinja 宏随机宽
- `global_radar` / `self_stocks` / `portfolio_detail`：JS 动态色/宽/渐变
- `ai_investment_committee`：运行时冲突条/投票/气泡色（3）
- `evidence_card`：Alpine `animation-delay`
- `nl_strategy.html`：Pine Script `style=shape.*`（非 HTML）
- 各页单处动态柱/环/分配条等

---

### 交付
- **`scripts/deep_inline_cleanup_batch9.py`**：`run_history`、`long_term_select`、`ai_analysis`、`strategy_copilot`、`live_research_lab`、`swarm_designer`、`strategy_snapshots`、`jarvis_proactive_panel`、`factor_detail`、`decision_replay_space`、`observability`、`alert_center`、`stocks_manage`、`signal_flag`、`tdx_blocks`、协作组件 4 个

### CSS 增补
- `strategy.css`：`rh-*`/`lts-*`/`ssnap-*`/`sf-*`
- `research.css`：`aa-*`/`drs-legend-*`/`obs-*`
- `stock-detail.css`：`sc-*`/`lrl-*`
- `swarm.css`：`swd-*`（designer）
- `system.css`：`jpp-*`/`sm-*`/`ac-*`
- `factor.css`：`fd-*`
- `market.css`：`tdx-scroll`
- `common.css`：`ctb-*`/`ctp-*`/`collab-*`

### 清扫后
| 指标 | batch8 后 | batch9 后 |
|---|---|---|
| 全模板 `style=` | ~137 | **~73** |
| `run_history` / `long_term_select` / `ai_analysis` | 各 5 | **0** |
| `strategy_copilot` / `live_research_lab` | 各 5/4 | **0** |
| `factor_detail` | 4 | **1**（IC 柱动态 height） |

### 约定（仍保留）
- `skeleton.html` 宏宽度、`ai_investment_committee` 冲突条、`global_radar`/`self_stocks` JS 动态色宽、`integration_hub` 质量条等

---

### 交付
- **`scripts/deep_inline_cleanup_batch8.py`**：`signal_observations`、`zen_dashboard`、`task_center`、`investment_managers`、`investment_manager_detail`、`factor_repository`、`ai_committee_selection`、`professional_workbench`
- **CSS**：`strategy.css`（`obs-*`）、`zen-finance.css`（`zen-mt-20` 等）、`system.css`（`tc-*`/`im-*`/`pmd-*`/`pw-*`）、`factor.css`（`fr-*`）、`research.css`（`aics-*` 余量）

### 清扫后
| 页面 | batch7 后 | batch8 后 |
|---|---|---|
| `signal_observations` | 8 | **1**（柱状图动态 width） |
| `zen_dashboard` | 7 | **0** |
| `task_center` | 7 | **0** |
| `investment_managers` | 7 | **0** |
| `investment_manager_detail` | 7 | **0** |
| `factor_repository` | 6 | **0** |
| `ai_committee_selection` | 6 | **0** |
| `professional_workbench` | 5 | **0** |
| 全模板 `style=` | ~194 | **~142** |

---

## 2026-06-20 (深挖 batch3：stock_detail 清零 / retail / stock_selector)

### 交付
- **`scripts/deep_inline_cleanup_batch3.py`**：`stock_detail` 余量 **18→0**（Copilot/审计/财务表）；`retail_assistant` **20→0**（定价卡/JS 串）；`stock_selector` 静态区 **17→1**（漏斗 `width` 动态保留）
- **CSS**：`stock-detail.css`（`sd-copilot-*`）、`system.css`（`ra-card-*` 定价）、`strategy.css`（`ss-*` 选股器）

### 清扫后
| 页面 | batch2 后 | batch3 后 |
|---|---|---|
| `stock_detail` | 18 | **0** |
| `retail_assistant` | 20 | **0** |
| `stock_selector` | 18 | **1** |
| 全模板 `style=` | 587 | **532** |

---

## 2026-06-20 (深挖 batch2：message_center / backtest / stock_detail JS)

### 交付
- **`scripts/deep_inline_cleanup_batch2.py`**：`message_center` 静态+JS（**0** `style=`）、`backtest` 静态+交易表 JS（**0**）、`stock_detail` 流动性/主力/形态/审计/推理链 JS 块改 `sd-*` 类
- **`system.css`**：`mc-*` 工具类；**`strategy.css`**：`bt-*` 交易表/分区类；**`stock-detail.css`**：动态面板 `sd-grid-*` / `sd-chain-*` 等

### 清扫后
| 页面 | 深挖前 | batch2 后 |
|---|---|---|
| `message_center` | 18 | **0** |
| `backtest` | 35 | **0** |
| `stock_detail` | ~60 | **~25**（策略推荐/财务表等动态色） |
| 全模板 `style=` | ~682 | **587** |

---

## 2026-06-20 (深挖：workbench / portfolio / stock_detail / system 页内联清扫)

### 交付
- **`scripts/deep_inline_cleanup.py`**：批量外置 workbench / portfolio / stock_detail 静态区；重写 `feature_retired.html`；`zen_base` → `.zen-nav-spacer`
- **`common.css`**：`.link-block`、`.flex-wrap-gap-*`、`.empty-state-pad`、`.feature-retired-*`、`.zen-nav-spacer` 等共享工具类
- **`workbench.css` / `portfolio.css` / `stock-detail.css`**：页内工具类（hero、决策列表、组合图表行等）
- **手工补强**：`daily_workbench` JS 串改类名（健康度用 `text-positive/negative`）；`portfolio_detail` 图表/配置 JS 串；`capabilities` / `integration_hub` 静态区 + 部分 JS 串

### 清扫后
| 指标 | 剩余清扫后 | 深挖后 |
|---|---|---|
| `daily_workbench` `style=` | 23 | **0** |
| `feature_retired` `style=` | 6 | **0** |
| `capabilities` `style=` | 18 | **0** |
| `integration_hub` `style=` | 19 | **4**（质量条 `width` 动态） |
| `stock_detail` `style=` | ~87 | **~60**（JS 动态 HTML 为主） |
| 全模板 `style=` 合计 | ~830 | **~682** |

### 仍保留（约定）
- JS 模板字符串中的动态色/宽/渐变（`stock_detail`、`alpha_factory`、`marketplace` 等）
- `skeleton.html` 宏随机宽度
- 质量条 / 分配条等运行时 `style.width` / `style.background`

---

## 2026-06-20 (剩余清扫：errors / shell / display:none 批量清理)

### 交付
- **`errors.css`** + `error_404` / `error_500` 去内联；`minimal_base` 引入
- **`common.css` shell 段**：`.nav-user-avatar`、主题图标 `[data-theme]` 规则、Jarvis `#commandOrb` / `.jarvis-orb-*`；`base.html` **0 处 `style=`**
- **`base_app.js`**：Jarvis 用 `.is-open`；主题图标不再 JS 切 `display`
- **`system_health_indicator.js`**：健康 Banner 用 `qa-is-hidden`
- **`stock-detail.css`** 增补静态区工具类；证据链弹层 / 预检对话框改类名
- **`scripts/cleanup_inline_styles.py`**：31 个模板静态区 `display:none` → `qa-is-hidden`（**约 -72** 处 `style=`；JS 模板字符串保留）

### 清扫后
| 指标 | 迁移前（本批） | 现在 |
|---|---|---|
| `base.html` `style=` | 23 | **0** |
| 全模板 `style=` 合计 | ~900+ | **~830**（多为 JS 动态串与 skeleton 宏宽度） |

---

## 2026-06-20 (Phase 5/6 + 组件清扫：组合 / 用户 / Zen / 组件零 `<style>`)

### 交付
- **`portfolio.css`（8 页）**：`portfolio`、`portfolio_detail`、`shadow_account`、`run_history`、`selection_result`、`investment_managers`、`investment_manager_detail`、`expert_teams`
- **`user.css`（2 页）**：`moments`、`user_spectrum_hub`
- **`admin.css`（2 页）**：`users_manage`、`stocks_manage`
- **`zen-pages.css`（2 页）**：`zen_terminal`、`portfolio_resonance`；`head_extra` 死块改为 `extra_css` 外链
- **`strategy.css` +1**：`collaboration_workspace`
- **组件外置** `static/css/components/`：`evidence-card.css`、`skeleton.css`（`zen_base` 引入）、`trading-dna-spiral.css`、`wisdom-mesh-browser.css`（`base.html` 引入）
- **脚本** `scripts/migrate_phase5_6_batch.py`

### 里程碑
- `app/presentation/web/templates/` 下路由页与组件 **0 个 `<style>` 块**（错误页等豁免项待单独核对）

### `static/css/pages/`（18 个）
+ portfolio · user · admin · zen-pages

---

## 2026-06-20 (常用页优先：策略 / 市集 / 个股 / 系统中枢)

### 交付
- **`strategy.css`（10 页）**：`backtest`、`stock_selector`、`optimize`、`attribution_dashboard`、`signal_observations`、`signal_flag`、`long_term_select`、`strategy_compare`、`strategy_snapshots`、`professional_workbench`
- **`marketplace.css`** · **`alpha-factory.css`** · **`factor.css`（3 页）** · **`data-lake.css`** · **`strategy-wizard.css`**
- **`stock-detail.css`**：`stock_detail` 主样式 + `workspace_shell` 拖拽卡；`[x-cloak]` 升入 `common.css`
- **`system.css` +9 段**：`capabilities`、`integration_hub`、`message_center`、`profile`、`observability`、`task_center`、`task_detail`、`alert_center`、`retail_assistant`
- **脚本** `scripts/migrate_common_pages.py`

### 进度快照
| Phase | 状态 |
|---|---|
| 2 操盘台 | 11/11 ✅ |
| 3 研究 / AI | 22/22 ✅ |
| 4 策略 / 因子 | **~16/18 ✅**（剩 `collaboration_workspace` 等） |
| 5 系统 / 用户 | **9/16**（中枢页已迁） |
| 6 个股 / 组合 | **1/12**（`stock_detail` 已迁；`workspace_shell` 已清） |
| 仍含 `<style>` | **~14 路由页 + 4 组件** |

### `static/css/pages/`（14 个）
workbench · market · system · research · swarm · research-canvas · truth · strategy · marketplace · alpha-factory · factor · data-lake · strategy-wizard · stock-detail

---

## 2026-06-20 (Phase 3 完成：研究 / AI 域全量外置 CSS)

### 交付
- **`research.css` 扩展 +11 段**：`ai_investment_committee`、`ai_committee_dashboard`、`ai_committee_selection`、`ai_hedge_fund`、`quant_lab`、`ai_research_report`、`voice_briefing`、`decision_replay_space`、`experiment_reporter`、`nl_strategy`、`nl_strategy_v2`
- **新建 `swarm.css`**：`swarm_dashboard`、`swarm_designer`、`swarm_designer_flow`
- **新建 `research-canvas.css`**：`research_canvas`（保留 `xyflow.css` vendor link）
- **新建 `truth.css`**：`truth_droplet` 独立页（保留 `zen-finance.css`）
- **脚本** `scripts/migrate_phase3_batch2.py`：提取 + 模板 `<link>` 一键迁移

### Phase 3 进度
| 域 | 状态 |
|---|---|
| 研究 / AI（22 路由页） | **22/22 ✅**（`agent_lab` 本无 `<style>`） |

### 累计 `static/css/pages/`
`workbench.css` · `market.css` · `system.css` · `research.css` · `swarm.css` · `research-canvas.css` · `truth.css`

---

## 2026-06-20 (Phase 2 收尾 + Phase 3 首批：system.css / research.css)

### 交付
- **修复** `architecture_roadmap.html`：清理误删 `<style>` 后残留的 ~230 行孤儿 CSS；外链 `system.css`；Hero/自检区静态内联改 `.roadmap-hero-head`、`.roadmap-panel-actions`、`.roadmap-symbol-input`、`.roadmap-self-check`、`.market-freshness-strip--hero` + `qa-is-hidden`
- **新建** `static/css/pages/system.css`（架构演进页样式 + 共用工具类）；`scripts/extract_page_css.py` / `scripts/fix_architecture_roadmap.py` 辅助提取与修复
- **新建** `static/css/pages/research.css`：聚合 war_room / ai_analysis / ai_chat / agent_center / research_pipeline 页内样式；`.agent-center-page` scoped 避免与 `market.css` 的 `.tab-btn` / `.stat-card` 冲突
- **迁移** 5 页：`<style>` → `<link href="css/pages/research.css">`（`scripts/migrate_research_templates.py`）；`agent_center.html` 增加 `.agent-center-page` 包裹层

### 进度
| 域 | 页 | 状态 |
|---|---|---|
| Phase 2 操盘台 | architecture_roadmap | ✅ system.css |
| Phase 3 研究 | war_room / ai_analysis / ai_chat / agent_center / research_pipeline | ✅ research.css（首批 5/22） |

---

## 2026-06-20 (Phase 2 续：热点/通达信/龙虎榜/研报 → market.css)

### 交付
- `market.css` 扩展：`#sectorsTable` / `#blocksTable` 表格行态、龙虎榜卡片、研报 Tab 列表；共用 `.market-freshness-strip`、`.empty-hint` 等
- `hot_sectors.html`：`<style>` 从 `extra_js` 迁出，改 `extra_css` 外链
- `tdx_blocks.html` / `longhu_bang.html` / `yanbao_hub.html`：页内 `<style>` 外置；`#blocksTable .positive/.negative` 保留 A 股配色

### Phase 2 进度（操盘台域）
| 页 | 状态 |
|---|---|
| daily_workbench | ✅ workbench.css |
| index / global_radar / self_stocks / market_panorama | ✅ market.css |
| hot_sectors / tdx_blocks / longhu_bang / yanbao_hub | ✅ market.css |
| architecture_roadmap | ✅ system.css |

---

## 2026-06-20 (Phase 2 续：自选股 + 市场全景 → market.css)

### 交付
- `static/css/pages/market.css` 扩展：自选股（`.watch-page` 域）与市场全景（`.panorama-hero` / `.pano-table` / `.heat-dashboard`）样式；冲突类名 scoped（如 `.watch-page .stock-card`、`.watch-page .stat-grid`）
- `self_stocks.html`：移除 ~115 行 `<style>`，外链 `market.css`；Banner/鲜度条改 `qa-is-hidden`；影子操盘区与 JS 空状态模板去静态内联
- `market_panorama.html`：移除 ~77 行 `<style>`（含重复 `btn-brand` 定义），外链 `market.css`；叙事脉动/热度仪表/控制栏/分页去静态内联

---

## 2026-06-20 (Phase 2 UI 迁移：Dashboard + 全球雷达 → market.css)

### 交付
- 新建 `static/css/pages/market.css`：聚合 `index.html`（Dashboard）与 `global_radar.html` 页内样式，硬编码色改 token/`color-mix`
- `index.html`：移除 `<style>`（~160 行），外链 `market.css`；静态内联改类（`dash-*`、`list-shell--scroll`、`link-card`、`qa-is-hidden`）
- `global_radar.html`：移除 `<style>`（~100 行），外链 `market.css`；Hero 统计/特色区块/工具栏去静态内联；热力图卡片网格改 `heatmap-cards-grid`
- JS 动态样式保留：热力图 `background:${bg}`、观测卡/事件模拟等运行时色块（符合迁移计划例外）

### 验收
- `/dashboard` 与 `/global-radar` 双主题布局与交互无回归
- 两页模板内无 `<style>` 块

---

## 2026-06-20 (UI 设计关门 + Phase 0：workbench 外置 CSS)

### 设计关门
- `static/css/common.css`：`body` 径向渐变对齐 `tmp/design`；`btn-brand` 改 token 渐变；删除重复 `layout-ref/ref-*` 块；新增 `.qa-is-hidden`（无 `!important`，兼容 jQuery `.show()`）
- `static/css/quant-atlas-layout.css`：补 `tmp/design` 类名别名（`.app/.rail/.primary` 等）；修复批量替换导致的选择器损坏；追加 `.qa-task`/`.qa-dot`/drawer 响应式规则
- `components/ui_macros.html`：扩展 `qa_page_hero`、`qa_stat_grid`、`qa_panel`、`qa_detail_row`、`qa_task`
- `ui_showcase.html`：任务流改用 `qa_task` 宏，去除剩余内联结构

### Phase 0 试点
- 新建 `static/css/pages/workbench.css`：`daily_workbench.html` 页内 `<style>` 外置，颜色改 token/`color-mix`
- `daily_workbench.html`：`<link>` 引入 workbench.css；静态 `display:none` 改 `qa-is-hidden`
- `docs/UI_CSS_MIGRATION_PLAN.md`：全站 8 阶段迁移计划
- `scripts/fix_layout_css_aliases.py`：布局 CSS 别名修复工具（防子串误替换）

---

## 2026-06-20 (双主题 UI 设计系统：夜间终端 + 日间机构研究台)

### 交付
- `static/css/design-tokens.css`：对齐 `tmp/design` 双主题 token（深色荧光绿/蓝、日间机构白底绿信号蓝辅助）
- `static/css/quant-atlas-layout.css`：三栏机构工作台布局组件（桌面/平板/移动断点 1180/820/520px）
- `static/css/common.css`：修复 `.app-shell` 缺失选择器与 hero `::before` 空规则块
- `app/presentation/web/templates/ui_showcase.html` + `layouts/design_showcase_base.html`
- `static/js/ui-showcase.js`：模块网格、筛选、抽屉、资产条交互
- 路由：`GET /ui-showcase`（夜间）、`GET /ui-showcase/light`（日间），支持主题切换链接

### 访问
- 夜间：`/ui-showcase` 或 `/ui-showcase/dark`
- 日间：`/ui-showcase/light`


### 根因
- `app/infrastructure/database/orm.py` 中 `mysql_database_uri()` 函数体被误插入的 `_mysql_ssl_args` 定义截断，实际返回 `None` → `create_db_engine` 报 `database_uri is required`

### 修复
- 恢复 `mysql_database_uri()` 正确实现
- 修复 `mysql_client.py` 中损坏的 `**_mysql_ssl_args()` 调用
- `adapters.create_database_adapter()` 统一用 `settings.use_mysql`

### 测试
- `tests/infrastructure/test_mysql_database_uri.py`

---

## 2026-06-20 (控制台日志恢复按级别着色)

### 根因
- 日志重构时 `structlog.dev.ConsoleRenderer(colors=False)` 写死关闭颜色，且控制台与文件共用同一 formatter

### 修复
- 控制台：TTY 下默认启用 ANSI 颜色（`LOG_COLORS=1/0` 可强制）
- 文件：`instance/app.log` 始终无色
- stdlib 回退路径：`HumanReadableFormatter` 支持级别着色

---

## 2026-06-20 (信号旗 /signal-flag/pool 400：缺失 facade 模块)

### 根因
- `create_signal_flag_pool_repository()` 引用 `common.facades.signal_flag_pool_repository`，该模块不存在
- `signal_flag_service` 工厂在 `wire_to` 时被跳过 → API 返回 `signal_flag_service_unavailable` (400)

### 修复
- 新增 `app/infrastructure/repositories/common/facades/signal_flag_pool_repository.py`（经 `RepositoryRegistry` 选择 MySQL/SQLite）
- `wiring_market._make_signal_flag_service` 传入 `session_factory`
- `v1_context` 对 `signal_flag_service` 使用 `_bundle_service()` 延迟解析

---

## 2026-06-20 (启动后日志静默：Alembic fileConfig 覆盖根 logger)

### 根因
- `create_watchlist_repository()` → `bootstrap_schema()` → `alembic upgrade head` 加载 `alembic/env.py`
- `fileConfig(alembic.ini)` 将 root logger 重置为 WARNING、仅保留 stderr StreamHandler，丢失 `instance/app.log` 与 DEBUG 级别

### 修复
- `alembic/env.py`：root 已有 handlers 时跳过 `fileConfig`（CLI 独立运行仍正常配置）
- `app/bootstrap.py`：`create_services()` 后再次 `setup_logging()`
- `app/infrastructure/database/schema_bootstrap.py`：Alembic 升级后 `reassert_logging_config()`
- `app/core/logging_config.py`：新增 `logging_already_configured()` / `reassert_logging_config()`；`LOG_LEVEL<=INFO` 时 werkzeug 默认 INFO
- `app/core/middleware/request_context.py`：`app.http` 通道记录 HTTP 访问（不依赖 werkzeug）

### 测试
- `tests/core/test_logging_config.py`：clobber 恢复 + watchlist 仓库创建后 handlers/level 保持

---

## 2026-06-20 (日志系统：可配置等级 + SQL/异常/警告统一落盘)

### 变更
- 新增 `app/core/logging_config.py`：`LOG_LEVEL` / `LOG_SQL` / `LOG_SQL_LEVEL` / `LOG_FILE` / `LOG_STRUCTURED` / `LOG_WERKZEUG_LEVEL`
- `app/core/logger.py` + `structlogger.py`：structlog 改走 stdlib 同一套 console + `instance/app.log` handler；`captureWarnings` + 未捕获异常钩子
- `db_manager.py`：SQL 追踪走 `app.sql` 通道，受 `LOG_SQL_LEVEL` 控制
- `.env.example`：补充日志配置说明

---

## 2026-06-20 (run.py 环境加载：secret.cfg 密码被空占位符挡住)

### 根因
- `run.py` 使用 `python-dotenv` 的 `load_dotenv()` 先于 `secret.cfg` 加载，`.env` 中 `MYSQL_PASSWORD=` 空值写入 `os.environ`，后续 `secret.cfg` 因「键已存在」跳过 → MySQL 无密码 → `watchlist_service` / `stock_group_service` 工厂失败。

### 修复
- `run.py`：改为 `_load_dotenv_if_present()`（`secret.cfg` → `.env` 顺序与 bootstrap 一致）
- `app/core/runtime_config.py`：`_load_env_file` 仅保护**非空**已有环境变量；跳过文件中的空值；允许 `secret.cfg` 覆盖空占位符
- `tests/core/test_runtime_config_secret_cfg.py`：新增空占位符回归测试

---

## 2026-06-20 (自选股/行情服务恢复 + 日志回退)

### 根因
- `watchlist_routes.py` 在路由注册时把 `runtime.watchlist_service` / `market_service` 快照为局部变量；此时无 Flask 应用上下文，解析结果为 `None`，请求期一直用空服务 → 自选股与行情 503/空数据。
- `registry.wire_to()` 经 `hasattr` 触发动态 `__getattr__`，部分 REQUIRED 服务未物化到 `Services` 容器。
- structlog 路径仅 stdout JSON，未恢复 `instance/app.log` 文件 handler，表现为日志变少。

### 修复
- `app/presentation/api/v1/portfolio_users/watchlist_routes.py`：改为请求期 `_watchlist_svc()` / `_market_svc()` 延迟解析（与 stock_group 路由一致）。
- `app/presentation/api/route_deps.py`：`_ctx_service()` + `build_portfolio_user_route_deps` 支持 `ctx.market` 回退。
- `app/presentation/api/v1_context.py`：补 `logger`；`_bundle_service()` 显式解析并告警缺失 REQUIRED 服务。
- `app/bootstrap_components/services.py`：`_eager_resolve_required()` 在 readiness 校验前物化 REQUIRED 服务。
- `app/core/typed_registry.py`：`wire_to` 用 `__dict__` 判断，避免 `__getattr__` 干扰。
- `app/core/structlogger.py` / `logger.py`：恢复控制台 + `instance/app.log` 双输出。


### 修复
- `app/core/hybrid_rate_limiter.py`：新增 `is_blocked` / `retry_after` / `reset`，GET 检查不再误计数
- `app/presentation/web/auth.py`：仅失败密码 POST 计入限流；锁定页传递 `login_locked_seconds`；登录成功清除计数
- `app/presentation/web/templates/login.html`：锁定提示秒级倒计时，倒计时结束自动解锁表单

---

### 修复
- `app/presentation/web/auth.py`：密码/微信/OAuth 登录成功后写入 session 时 `user.id` → `user.user_id`（`UserAccount` 无 `id` 字段，导致 POST `/login` 500，进而 API 全 401）

---

### 修复
- `multi_level_cache.py`：补 `get_logger` import，去除重复 coalesce import
- `app/core/registry.py`：重导出 `registered_service_names`
- `tests/infrastructure/agent/backtest/conftest.py`：注册 legacy `backtest` 包别名
- `test_diagnosis_report_wiring.py`：wire 已移除时 skip
- `test_registry_baseline.py` / `test_service_loader.py`：对齐 TypedServiceRegistry API

### 实测
- 全量 pytest 可收集（原 9 个 collection ERROR 已消除）
- 全量覆盖率约 **20%**（`fail_under=50` 未达标；大量 smoke/legacy 测试仍失败）

---

## 2026-06-19 (集成测试：审计关键路径)

### 测试
- 新增 `tests/integration/test_audit_critical_paths.py`
  - 回测涨跌停 E2E：`simulate_single_backtest` 涨停日不买 / 关闭限制后可买
  - Panorama 缓存：二次 `get_panorama` 仅 1 次 provider 调用
  - Trade pipeline：合规→预检→审计全链路 / 合规失败短路预检

---

## 2026-06-19 (God Class 第三片续续：TdxDaykSyncService runner)

### 结构
- 新增 `tdx_dayk_sync_runner.py`：`sync_one_stock` + `run_tdx_dayk_sync`（~420 行编排）
- `tdx_dayk_sync_helpers.py` 新增 `qlib_instrument_for`
- `tdx_dayk_sync_service.py` 瘦身为 public API + thin delegate（~550 行）

### 测试
- `tests/modules/data/test_tdx_dayk_sync_runner.py`

---

## 2026-06-19 (God Class 第三片续：TdxDaykSyncService CSV/Timescale/复权)

### 结构
- 新增 `tdx_dayk_csv_writer.py`：`write_qlib_csv`
- 新增 `tdx_dayk_adjustment.py`：复权因子与前/后复权
- 新增 `tdx_dayk_timescale_writer.py`：Timescale session / package / matview
- `tdx_dayk_sync_service.py` 保留 thin delegate，对外方法签名不变

### 测试
- `tests/modules/data/test_tdx_dayk_csv_writer.py`
- 沿用 `test_timescale_dayk_dual_write.py`、`test_sync_service.py`

---

## 2026-06-19 (God Class 第三片：TdxDaykSyncService 首拆)

### 结构
- 新增 `tdx_dayk_sync_models.py`：`SyncResult` / `SyncStatus`
- 新增 `tdx_dayk_sync_helpers.py`：扫描、normalize、worker cap、瞬态连接错误判定
- `tdx_dayk_sync_service.py` 委托上述模块，保留 staticmethod 兼容面

### 测试
- 沿用 `tests/modules/data/test_sync_service.py`

---

## 2026-06-19 (God Class 第二片：tracing.py 退役)

### 结构
- 删除 `app/infrastructure/tracing.py`（3971 行空行膨胀，未被 import；与 `tracing/` 包冲突）
- Redis `DistributedTracer` 迁入 `tracing/distributed_tracer.py`
- 新增 `tracing/span_types.py`、`tracing/span_store.py`
- `tracing/__init__.py` 导出 OTEL + Redis tracer 双轨 API

### 测试
- `tests/infrastructure/test_tracing_span_store.py`

---

## 2026-06-19 (God Class 首片：redis_executor 拆分)

### 结构
- `redis_executor.py`：4022 行（空行膨胀）→ ~190 行门面；修复 `payload`/`key`/`result_key` 未定义、重复 `submit_order`、空 `_simulate_execute`
- 新增 `redis_stream_connection.py`：lazy client + consumer group
- 新增 `redis_executor_codec.py`：TradeRequest/Response 编解码与 Redis key 命名

### 测试
- `tests/infrastructure/test_redis_executor_codec.py`

---

## 2026-06-19 (AUDIT R14 batch-10：user_tiers 五层响应信封)

### R14 API 响应信封
- 新增 `v1/user_tiers/_http.py`：`tier_success()` / `tier_not_found()`
- `retail` / `boutique` / `investment` / `fund` / `institution` 共 ~70 条路由 → `success_response` / `error_payload`
- 404 场景（alt-data / federated node/model）统一 `ErrorCode.NOT_FOUND`

### 测试
- `tests/smoke/test_route_smoke_critical.py`：federated status 从 `data.total_nodes` 断言

---

### R14 API 响应信封
- `v1/optimization/` 四模块（dual_path / budget / compliance / evolution）共 18 条路由 → `success_response` / `error_payload`
- `v1/provenance/`：`truth-dashboard`、`fingerprint` 改标准信封；降级场景用 `meta.warning`

### 测试
- `tests/presentation/api/test_optimization_envelope.py`
- `tests/smoke/test_route_smoke_critical.py`：`factory_count` 改从 `data` 读取

---

### R14 API 响应信封
- `v1/lifecycle/` 四模块（simulation / data / research / execution）共 20 条路由：`jsonify({"ok": True})` → `success_response`
- `routes_v1_monitoring.py`：`/system/trace/<id>` 去除 data 内嵌 `status: success`，改标准信封

### 测试
- `tests/presentation/api/test_lifecycle_envelope.py`：canonical 信封断言 + panorama 缓存二次命中

---

### 行为
- `providers.py`：3 个 lazy provider 失败时 `logger.warning(..., exc_info=True)`，不再静默返回 None
- `MemoryDataStore`：`OrderedDict` LRU，`BACKTEST_MEMORY_STORE_MAX`（默认 64）超限驱逐最旧条目
- 缓存穿透：`coalesce.py` 单飞锁；`CacheManager` / `MemoryCache` / `GlobalCache` / `MultiLevelCache` 的 `get_or_set` 并发下 factory 只执行一次
- `MarketApplicationService.get_panorama`：`CacheManager` 缓存 45s（`MARKET_PANORAMA_CACHE_TTL`），减轻全市场扫描
- `query_limits.MAX_USERS=1000`：`mysql_repositories` / `async_mysql_repositories` 的 `list_users` 加 `.limit()`
- `AppError.__init__` 补全 `message/code/details`；Flask 注册 `CoreError` / `AppError` 错误处理器

### 文件
- `app/bootstrap_components/providers.py`
- `app/infrastructure/agent/backtest/data_store.py`
- `app/infrastructure/cache/coalesce.py`（新建）
- `app/infrastructure/cache/cache_manager.py`、`global_cache.py`、`multi_level_cache.py`
- `app/infrastructure/memory_cache.py`
- `app/modules/market_data/services/market_service.py`
- `app/core/query_limits.py`
- `app/infrastructure/repositories/mysql/mysql_repositories.py`、`async_mysql_repositories.py`
- `app/domain/exceptions.py`、`app/presentation/api/error_handlers.py`

### 测试
- `tests/infrastructure/agent/backtest/test_memory_data_store.py`
- `tests/infrastructure/test_cache_coalesce.py`
- `tests/presentation/api/test_domain_error_handlers.py`

### 仍待人工/大项（AUDIT_REPORT1）
- `.env` 凭证轮换（运维）
- God Class 拆分：`RedisStreamExecutor` / `DistributedTracer` / `TdxDaykSyncService`
- 全量 API 响应信封迁移、实测覆盖率 ≥50%、React SPA 全量迁移

---

## 2026-06-16 (P3 战略削减 batch-3：SPA + 模板扫尾)

### 行为
- 新增 `GET /api/v1/platform/strategic-features`：返回与 Jinja 一致的 `feature_*` 开关（无需登录，供 SPA 导航门禁）
- React SPA：`FeatureGate` / `FeatureRetired` + `usePlatformFeatures`；`/app/marketplace` 默认 410 式下线页；导航/回测治理链/MLflow 深链按 flag 隐藏
- `marketplace.html`：SPA 治理 Tab 链接按 `feature_alpha_marketplace` 隐藏
- `truth_droplet.html`：Mesh 对账按钮与 `cognitive-mesh` API 调用按 `feature_federated_mesh` 门禁；修复失效的 `/api/v2/phase17/mesh/*` 路径
- `wisdom_mesh_browser.html`：整块组件按 `feature_federated_mesh` 条件渲染

### 文件
- `app/presentation/api/routes_v1_platform.py`
- `frontend/src/hooks/usePlatformFeatures.ts`、`components/FeatureGate.tsx`、`FeatureRetired.tsx`
- `frontend/src/App.tsx`、`Layout.tsx`、`NotFound.tsx`、`Backtest.tsx`、`MlflowRunModal.tsx`

### 测试
- `tests/presentation/api/test_platform_features.py`

### 部署备注
- 修改 SPA 源码后需在 `frontend/` 执行 `npm run build` 更新 `frontend/dist/`

---

## 2026-06-16 (P3 战略削减 batch-2：API 扩展 + 模板 + Mesh 启动)

### 行为
- `api_path_sunset_feature` 新增门禁前缀：
  - `/alpha/tokens` → `alpha_marketplace`
  - `/decision-theater` → `decision_theater`
  - `/cognitive-mesh`、`/user-tiers/institution/federated` → `federated_mesh`
- `professional_workbench.html`：联邦 Tab/面板/节点统计按 `feature_federated_mesh` 隐藏；`loadMeta` 不再请求已下线联邦 API
- `research_pipeline.html`：决策剧场 3D 区块与 Three.js 脚本按 `feature_decision_theater` 条件渲染
- `user_spectrum_hub.html`：Alpha 市场链接按 `feature_alpha_marketplace` 隐藏
- `mesh/bridge.py`、`cluster_event_bus.py`：`MESH_ENABLED` 外须 `FEATURE_FEDERATED_MESH=1` 才启动联邦桥接

### 测试
- `tests/core/test_strategic_sunset.py`：补充 4 条 API 路径映射断言

---

## 2026-06-16 (P3 战略削减 batch-1：Feature Sunset 门禁)

### 行为（AUDIT_REPORT1 §八 P3）
- 新增 `app/core/strategic_sunset.py`：5 类膨胀能力默认 **关闭**，`FEATURE_*=1` 可显式启用
  - `FEATURE_WAR_ROOM` — War Room + Hyper 模拟器 API/页面
  - `FEATURE_ALPHA_MARKETPLACE` — Alpha 市场 / ZK 治理 / wallet / evolution-tournament
  - `FEATURE_DECISION_THEATER` — 决策剧场 3D、decision-replay
  - `FEATURE_SWARM_TOPOLOGY` — Swarm Designer / topology API（保留 agent-swarm 研究链路）
  - `FEATURE_FEDERATED_MESH` — `/mesh`、`/wisdom-mesh`；Celery 联邦心跳需与本 flag 同时开启
- `strategic_sunset_hooks.py`：API `before_request` 返回 **410** + `feature_retired`；页面 `feature_retired.html`
- 导航 `base.html` 隐藏已下线入口；Jarvis 路由不再推荐 War Room / Swarm Designer

### 文件
- `app/presentation/api/routes.py`、`bootstrap_components/presentation.py`
- `pages_admin.py`、`pages_ai.py`、`jarvis_semantic_router_service.py`、`celery_app.py`

### 测试
- `tests/core/test_strategic_sunset.py`

---

## 2026-06-16 (P2 #21 扫尾：策略模型 KDJ 统一)

### 行为
- 新增 `app/core/kdj.py`：`tdx_k_d()` / `tdx_k_d_j()`（通达信 K = ta `stoch_signal`，D = ta `stoch`）
- `app/models/`：`oscillation`、`panic_bottom`、`mean_reversion`、`extended_28` 改用 `tdx_k_d`
- `scripts/trading_strategies.py`、`scripts/web_app.py` 同步修正
- `indicators.py` 委托 `tdx_k_d`，去除重复 swap 逻辑

### 测试
- `tests/core/test_tdx_kdj.py`

---

## 2026-06-16 (P2 #18 + #21 补：jQuery/Bootstrap 升级 + stochastic KDJ)

### P2 #18 jQuery / Bootstrap 4 升级
- 自托管 vendor：`jquery-3.7.1.min.js`、`bootstrap-4.6.2.bundle.min.js`、`bootstrap-4.6.2.min.css`（保持 Bootstrap 4 API，`data-toggle` 等无需迁移）
- `app/presentation/web/templates/base.html` 引用新版本
- `scripts/templates/base.html`、`test_api.html` CDN → jQuery 3.7.1
- 旧 `4.5.2` / `3.5.1` 文件保留在 `static/` 以备回滚，主模板不再引用

### P2 #21 补 stochastic_selector
- `stochastic_selector.py`：K/D 与通达信对齐（`K=stoch_signal`，`D=stoch`）

### 测试
- `tests/presentation/test_frontend_vendor.py`

---

## 2026-06-16 (P2 #15 + #22e：Alembic 引导 + 选股脚本日志 batch-5)

### P2 #15 Alembic 优先于 create_all
- 新模块 `app/infrastructure/database/schema_bootstrap.py`：`alembic_enabled()`（`DB_SCHEMA_CREATE_ALL=1` 强制 create_all）、`run_alembic_upgrade_head()`、`bootstrap_schema(engine)`
- SQLite → `create_all`；MySQL 默认 `alembic upgrade head`，失败回退 `create_all`
- `orm.py`、`db_manager.py` 的 `bootstrap_schema` 委托上述模块

### P2 #22e 选股脚本日志 batch-5
- 新模块 `scripts/selector_logging.py`：`get_selector_logger` + 项目根路径注入
- `bollinger_rsi` / `dualma` / `ema_macd` / `tau` / `volume_breakout` / `long_term` / `enhanced_long_term` / `short_term`：`print` → `get_selector_logger`（`test_short_selector.py` 保留 CLI print）

### 测试
- `tests/infrastructure/test_schema_bootstrap.py`

---

## 2026-06-16 (P2 #22d：选股脚本日志化)

### P2 #22 日志 batch-4（scripts 选股链路）
- `scripts/stochastic_selector.py`：28 处 `print` / `traceback.print_exc` → `get_logger`（info/warning/debug/exception）
- `scripts/quant_screener.py`：`logging.getLogger` 统一为 `get_logger`，报告输出改 `logger.info`
- `scripts/advanced_indicators.py`：`StockScreenerEngine` 与 `__main__` 报告 → `logger.info`

---

## 2026-06-16 (P2 #22c：日志 batch-3 + 回测 stdout 契约)

### P2 #22 日志 batch-3
- `backtest/loaders/tushare.py`、`okx.py`：`print` → `get_logger`（含 `exc_info`）
- `backtest/process_runner.py`：Runner 进度 → `logger.info`
- `app/core/main.py`：圣杯选股脚本 → `logger.info`

### 回测子进程 stdout 契约
- 新模块 `backtest/stdio_json.py`：`write_stdout_json()` 集中 JSON stdout（非 logging）
- `engines/base.py`、`runner.py`、`validation.py`、`engines/options_portfolio.py` 改用 `write_stdout_json`

### 测试
- `tests/infrastructure/agent/backtest/test_stdio_json.py`

---

## 2026-06-16 (P2 #16c + #5：Panorama canonical + 回测涨跌停)

### P2 #16c Panorama / v2 行情 canonical
- `canonical_panorama_dict()`、`panorama_row_to_quote_dto()`：`app/domain/dto/quote_factory.py`
- `MarketApplicationService.get_panorama()` 榜单行统一 symbol/code/change_pct
- `MarketPanoramaDTO.from_service(..., market=)`、`MarketFacade.get_panorama`、v2 `/markets/panorama`、legacy `/market-rankings` 出口规范化

### 审计 #5 A 股涨跌停（回测）
- 新模块 `cn_backtest_rules.py`：停牌/一字板/涨跌停日频近似；`strategies._can_trade_cn` 委托复用
- `BacktestEngine` 买卖前 `_cn_trade_allowed()`；`RiskControlParams.apply_cn_price_limits`（`BT_APPLY_CN_LIMITS` 默认开）
- 测试：`test_cn_backtest_rules.py`、`test_backtest_price_limits.py`

---

## 2026-06-16 (P2 #16b + #7 + #8：Quote 批量 + ATR Wilder + 年化交易日)

### P2 #16b Quote DTO 扩展
- `canonical_quote_list()`；`MarketApplicationService._serialize_stock` 输出规范 code/symbol
- Legacy `/api/stocks`、`/api/stock/<symbol>` 走 canonical

### 审计 #7 ATR Wilder
- `compute_atr()`：`rolling mean` → Wilder `ewm(alpha=1/n)`
- `PreTradePreflightService._compute_atr_from_bars` 复用 `compute_atr`

### 审计 #8 年化收益率
- 默认 `BT_TRADING_DAYS_PER_YEAR=250`（numpy fallback）；`rust_core` 同步 250
- `calculate_annual_return` 指数基数由 365 改为可配置交易日

### 测试
- `tests/core/test_risk_metrics.py`；`tests/domain/test_quote_factory.py`（list）

---

## 2026-06-16 (P2 #22b + #16：日志 batch-2 与 Quote DTO 统一)

### P2 #22 日志 batch-2
- `strategies.py`、`core/engine.py`、`core/factory.py`
- `backtest/engines/base.py`（优化器加载告警）、`backtest/loaders/yfinance_loader.py`

### P2 #16 Quote DTO
- `canonical_quote_payload()`：`symbol`/`code`/`code6` 对齐，`change_pct` 兼容 `pct_chg`/`chenge`，`change_amount` 兼容 `change`
- 接入：`quote_factory.py`、`pytdx_quote_mapper.py`、`stock_route_helpers.enrich_quote_resource`

### 测试
- `tests/domain/test_quote_factory.py`

---

## 2026-06-16 (P2 #17 + #22：模板统一与生产日志)

### P2 #17 模板
- `layouts/minimal_base.html`：CSRF + 设计令牌，无主导航（404/500 使用）
- `layouts/zen_base.html` 继承 `minimal_base`，与错误页共享文档头契约
- `base.html` 拆出 `site_layout` / `overlay_chrome` / `core_scripts` 块，便于后续布局变体
- `error_404.html` / `error_500.html` → `minimal_base`（不再加载完整导航）

### P2 #22 日志（生产路径 batch-1）
- `print` → `get_logger`：`indicators.py`、`investment_committee_db.py`、`investment_committee_service.py`
- Bootstrap：`presentation.py`、`repositories.py`
- 数据：`timeseries_ohlcv_sync_service.py`（去重 print）、`qlib_pipeline_service.py`、`financial_market_data.py`
- `agents/config.py`

---

## 2026-06-16 (P2 #19：回测现金分红)

### 行为
- 未复权 K 线含 `Dividend` / `cash_div` 等列时，持仓日按股数 × 每股分红增加现金并记入 `metrics.dividend_income`
- 组合回测 `simulate_portfolio_backtest`、单标的 `simulate_single_backtest` 均在当日交易前入账
- `trades` 追加 `action=dividend` 记录；`BT_APPLY_CASH_DIVIDENDS=0` 可关闭

### 文件
- `app/infrastructure/providers/backtest_dividends.py`（新建）
- `app/core/risk_controls.py`：`TradeCostParams.apply_cash_dividends`
- `app/infrastructure/providers/backtest_engine.py`：`_apply_dividends_for_day`、主循环集成

### 测试
- `tests/infrastructure/providers/test_backtest_dividends.py`

---

## 2026-06-16 (P2 #21：KDJ K/D 通达信对齐)

### 行为
- `ta` 的 `stoch()`（原始 %K）与 `stoch_signal()`（平滑 %D）在对外命名上与通达信 K/D **对调**
- `TaIndicatorProvider` 实时指标 `kdj_k` / `kdj_d` 同步修正

### 文件
- `app/infrastructure/providers/indicators.py`
- `scripts/advanced_indicators.py`、`scripts/short_term_indicators.py`、`scripts/quant_screener.py`

### 测试
- `tests/infrastructure/providers/test_kdj.py`

---

## 2026-06-16 (Phase 33：全市场 Backfill + WebSocket 全景 + 回测 Rust)

### QuestDB 全市场 Backfill
- `describe_timeseries_backfill_status()`：行数 vs `TIMESERIES_BACKFILL_TARGET_ROWS`（默认 100 万）
- `timeseries_health_probe()` → `backfill` 字段；`GET /api/v1/data/timeseries-backfill-status`
- Celery `timeseries_ohlcv_full_backfill` + `POST /api/v1/system/timeseries-ohlcv-backfill`（async/sync）
- `run_timeseries_ohlcv_backfill` 默认 `all_market=True`；修复 sync `resolve_sync_symbols` 传参
- 集成中枢「全市场 Backfill」按钮；数据湖健康页 Backfill 进度条

### WebSocket 全站
- `market_panorama.html`：`quant:quote` 增量刷新可见行（自选页已有）

### Rust 回测热路径
- `calc_metrics()`：无风险利率为 0 时 Sharpe/MaxDD 走 `native_compute`（quant_core/numpy）

### 测试
- `test_describe_timeseries_backfill_status`；health probe 断言 `backfill`

---

## 2026-06-16 (Sprint 32：可选收尾 + Backlog 首批)

### Flask 操盘台 parity
- `daily_workbench.html`：`#wbBeatSyncMini` + `QAUserCenter.mountBeatSyncMiniPanel`；集成卡展示 `timeseries_beat` 摘要
- `base.html`：全局加载 `qa_user_center.js`（修复多页 `QAUserCenter` 未注入脚本）

### Backlog 首批（最小落地）
- `DailyWorkbenchService._integration_digest()` → `timeseries_beat`（复用 `describe_questdb_sync_beat`）
- 操盘台自选区监听 `quant:quote` WebSocket 事件增量刷新报价
- `MarketCode` 增加 `FX` / `FUTURES`（benchmark + currency 映射）
- `FastBacktestEngine` Sharpe 改走 `native_compute.calculate_sharpe_ratio`（Rust/numpy 统一 ddof=1）
- CI `REDIS_URL` → `redis://127.0.0.1:6379/0`（与 services.redis 对齐）

### 测试
- `test_market_code_extended.py`；`test_phase45_ui_opt_workbench` 断言 Beat digest + 页面脚本

---

## 2026-06-16 (Sprint 31：基础设施轨道收敛)

### 去重
- `architecture_roadmap.html`：移除重复的 `loadRoadmapInfrastructure` 芯片条，改用 `QAUserCenter.mountBeatSyncMiniPanel`

### 单一事实来源
- `refactor_status()` → `probes.timeseries.beat`（enabled、last_beat_run、history_count）

### 文档
- `docs/refacter.md` 增加 **Sprint 收敛说明**：本轨道 0 必做 Sprint；大 Phase 转入 Backlog

### 测试
- `test_refactor_status_has_pillars_and_probes` 断言 `probes.timeseries.beat`

---

## 2026-06-16 (Sprint 30：capabilities Beat 迷你面板 + React 操盘台时序卡)

### QAUserCenter (`qa_user_center.js`)
- `loadBeatSyncOps` / `renderBeatSyncMini` / `mountBeatSyncMiniPanel`：并行拉 health + history，可复用于多页面

### 能力总览 (`capabilities.html`)
- 新增「基础设施 · Beat 同步」区块（`#capBeatSyncMini`）

### React 操盘台 (`frontend/`)
- `types/timeseries.ts`；`api.ts` 增加 `fetchTimeseriesHealth` / `fetchTimeseriesSyncHistory`
- `TimeseriesOpsCard` 嵌入 `Dashboard.tsx`（Beat / QuestDB / QMT + 近 5 次 Beat）

### 文档
- `docs/refacter.md` 更新 `/capabilities` 入口说明

---

## 2026-06-16 (Sprint 29：观测台 Beat 历史 + 决策自检探针)

### 决策链路自检
- 新增探针 `timeseries_sync_history` → `GET /api/v1/data/timeseries-sync-history?limit=5&source=celery_beat`

### 集成栈探针
- `timeseries_ohlcv` 层增加 `beat_history_count`、`recent_beat_runs`

### 观测台 (`observability.html`)
- 统计卡「Beat 同步」；面板「Beat 同步历史」时间线（并行拉 health + history）
- `loadIntegrationStack()` 优先展平 `layers`（qlib/timeseries/execution 等）

### 测试
- `test_phase62_ux_contract` 扩展探针与 history API；`test_integration_stack_probes` 断言历史字段

---

## 2026-06-16 (Sprint 28：Beat 同步历史 JSONL + refacter 快速验证 API)

### 时序同步历史 (`sync_snapshot.py`)
- `record_timeseries_sync_snapshot()` 追加写入 `instance/timeseries_sync_history.jsonl`（保留最近 365 条）
- 新增 `get_timeseries_sync_history(limit, source)`；`describe_questdb_sync_beat()` 附带 `recent_beat_runs`

### API
- `GET /api/v1/data/timeseries-sync-history?limit=20&source=celery_beat`

### 文档与 UI
- `docs/refacter.md`：基础设施说明、页面入口、快速验证 API（`stack-status` / `qmt-status` / `timeseries-sync-history`）
- `data_lake_health.html`、`integration_hub.html`：展示 Beat 近次执行

### 测试
- `test_sync_history_source_filter_and_trim`；扩展 snapshot / beat 测试

---

## 2026-06-16 (Sprint 27：Beat 上次执行时间 + 架构路线图基础设施探针)

### 时序同步快照 (`sync_snapshot.py`)
- 修复缺失的 `from pathlib import Path`
- `describe_questdb_sync_beat()` 附带 `last_sync`、`last_beat_run_at`/`last_beat_run_ok`（`source=celery_beat` 时）、`sync_in_progress`/`sync_progress`

### 架构路线图 (`architecture_roadmap.html`)
- Hero 区新增 `#roadmapInfraProbe`：并行拉取 `timeseries-health`，展示 Beat 上次执行、QMT 模式、QuestDB 在线状态
- 15s 自动刷新；重构状态面板副标题注明 `timeseries-health` 数据源

### 集成中枢 / 数据湖健康
- Beat 状态行展示上次 Beat 执行时间与同步中进度（与 Sprint 26 探针字段对齐）

### 测试
- `test_describe_questdb_sync_beat_last_run`（快照 + 进行中进度）

---

## 2026-06-16 (Sprint 26：数据湖健康页 Beat/QMT + 决策自检集成栈探针)

### 时序健康 API
- `timeseries_health_probe()` 增加 `celery_beat`、`execution.qmt`（与集成中枢同源）

### 数据湖健康页 (`data_lake_health.html`)
- QuestDB 区：Celery Beat 调度、QMT simulation/live、最近同步（source/mode/写入行数）
- WebSocket 区：`alerts` 房间、`origins_configured` 提示

### 决策链路自检
- 新增探针 `integration_stack` → `GET /api/v1/integration/stack-status`

### 测试
- `test_timeseries_health_infrastructure.py`；扩展 `test_timeseries_health_probe`、`test_phase62_ux_contract`

---

### 集成栈探针
- `describe_questdb_sync_beat()`：Beat 任务、16:35 调度、`QUESTDB_SYNC_BEAT` 开关
- `IntegrationStackService`：`layers.execution_gateway`（QMT simulation/live）；`celery_tasks.questdb_beat`；`timeseries_ohlcv` 增加 `celery_beat` 与最近同步详情字段

### 集成中枢 UI (`integration_hub.html`)
- 状态卡：QMT 执行网关、Celery Beat 日K 标注
- 运行时行：Celery Beat 日K、QMT 执行、WebSocket 订阅数、最近同步（mode/行数/失败样本）
- 修复 `timeseriesSyncState` 的 `if (syncEl)` 语法

### 配置
- `.env.example`：`QUESTDB_SYNC_BEAT=1`

### 测试
- `test_describe_questdb_sync_beat_defaults`、`test_integration_stack_probes.py`

---

### QMT 执行网关
- `QMT_LIVE_SUBMIT`（默认 `0`）：`0` = 仅本地记账 simulation；`1` = 尝试 xtquant 实盘提交
- `qmt_executor_status()` / `QMTExecutor.execution_mode` / pending order `simulation` 字段
- `GET /api/v1/execution/qmt-status`；`GET /api/v1/execution/manifest` 增加 `qmt` 块
- 成交反馈 `execution_data` 携带 `simulation` / `execution_mode`

### 决策链路自检
- `DecisionFlowContractService._self_check_probes` 新增：
  - `timeseries_health` → `/api/v1/data/timeseries-health`
  - `realtime_status` → `/api/v1/realtime/status`
  - `execution_manifest` → `/api/v1/execution/manifest`（含 `qmt.execution_mode`）

### 测试
- `test_qmt_executor_simulation.py`；`test_phase62_ux_contract` 探针断言

---

### WebSocket 全站推送
- `base_app.js`：连接后同时订阅 `market`（`quote_update`）与 `alerts`；记录 `connected` / `lastQuoteAt`
- `GET /api/v1/realtime/status`：增加 `origins_configured`、`base_subscriptions`、`rooms.alerts`

### Retail Assistant Hub（修复断裂 shim）
- `retail_assistant_hub_service.py`：实现 `RetailAssistantHubService`（`quick_actions` / `overview` / `refactor_status` 等）
- `refactor_status`：对照 `docs/refacter.md` 四维 pillars，并嵌入 WebSocket / QuestDB / THS 实时探针

### THS / 热点板块
- 单测：`get_ths_session_from_settings` 有/无凭证分支；`HotSectorService._init_ths_session` 经 Port 初始化

### 测试
- `test_websocket_quote_subscription.py`、`test_retail_assistant_hub_service.py`

---

### 同步进度
- `sync_snapshot.py`：`set/get/clear_timeseries_sync_progress`（JSON 文件 + 可选 Redis `quant:timeseries_sync_progress`）
- `run_timeseries_ohlcv_sync`：运行中每 20 标的更新进度，结束后清除

### 健康探针
- `timeseries_health_probe` 增加 `sync_progress`

### 前端
- `data_lake_health.html`：修正 SQLite 湖 API 字段；新增 QuestDB/同步进度条、`/realtime/status` WebSocket 卡
- `integration_hub.html`：WebSocket 状态卡；最近同步行展示进行中百分比

### 测试
- `test_sync_progress_roundtrip`

---

## 2026-06-16 (Sprint 21：集成中枢 × QuestDB 可观测 + 同步快照)

### 时序同步快照
- `sync_snapshot.py`：`instance/timeseries_sync_snapshot.json` 记录最近同步结果
- `run_timeseries_ohlcv_sync` / `run_scheduled_questdb_sync` / backfill 结束时写入快照
- `timeseries_health_probe` 增加 `last_sync` 字段

### 集成栈
- `IntegrationStackService` 新增 `layers.timeseries_ohlcv`（QuestDB 连通、行数、warnings、最近同步）

### 集成中枢 UI
- `integration_hub.html`：QuestDB 状态卡、历史分层 QuestDB/ClickHouse/最近同步、数据新鲜度计入时序健康
- 侧边栏「QuestDB 增量同步」按钮 → `POST /api/v1/system/timeseries-ohlcv-sync`

### 测试
- `test_timeseries_sync_snapshot.py`

---

## 2026-06-16 (Sprint 20：因子演化闭环 UI + QuestDB 探针 + 实验报告 IC)

### Alpha Factory API
- `POST /api/v1/alpha-factory/experiment/submit`：提交实验并可 `save_to_vault`
- `POST /api/v1/alpha-factory/experiment/analyze`：分析实验并 patch vault
- 血缘图节点增加 `factor_id` / `experiment_id` / `status`

### 前端
- `factor_evolution.html`：展示 Factor/实验元数据；「提交入库」「同步分析」「定向演化」；成功后自动刷新拓扑
- `ExperimentReport.tsx`：展示 `preset_name`、IC 指标列（4 列指标卡）

### 基础设施
- `probe_ohlcv_tables`：增加 `questdb_sample_sh600519`
- `timeseries_health_probe`：低行数/样本稀疏时返回 `warnings`（`questdb_backfill_recommended` 等）

### 测试
- `test_timeseries_health_probe.py`、`get_lineage_graph` 元数据断言

---

## 2026-06-16 (Sprint 19：THS 会话统一 + Factor Vault 实验闭环)

### 热点板块 / THS
- `CnSectorBoardPort` + `CnSectorBoardPortAdapter`：新增 `get_ths_session_from_settings()`
- `HotSectorService._init_ths_session`：改经 Port 读取 `THS_USERNAME`/`THS_PASSWORD`，去除重复 settings 逻辑

### Alpha Factory / Factor Vault
- `submit_factor_experiment(save_to_vault=True)`：metadata 写入 `status=submitted`、`data_scope`；响应含 `factor_id`
- `analyze_experiment_result`：按 `experiment_id` 合并更新已有 vault 记录（避免 submit→analyze 双份因子）
- `FactorVaultStorage.patch_factor()`：InMemory + MySQL 实现元数据/回测结果合并更新

### 测试
- `test_alpha_factory_orchestrator.py`：`test_submit_then_analyze_updates_same_vault_factor`

---

## 2026-06-16 (Sprint 18：THS 板块 Provider 硬化 + Experiment API 契约)

### 同花顺板块 (`cn_ths_sectors.py`)
- `ths_login`：不再记录响应 body；区分 `RequestException` 与未知异常
- 新增 `get_ths_session_from_settings()`：从 `ThsConfig` 读取凭证
- AkShare 回退路径：`kind` 字段对齐 `sector_kind`（与页面抓取一致）

### Experiment 实体
- `Experiment.resolved_metrics()` / `resolved_equity_curve()` / `to_api_summary()` / `to_api_detail()`
- `routes_v1_experiments.py`：列表与详情改调用实体方法（详情新增 `preset_name`）

### 测试
- `test_cn_ths_sectors_fetch.py`：HTML 解析、`is_ths_sector_code`、涨跌幅解析
- `test_experiment_entity_api.py`

---

## 2026-06-16 (Sprint 17：UserKnowledge 去 Stub + IC 入库 + SPA 实验报告)

### UserKnowledge
- `stub_concrete_user_knowledge_service.py`：改为 `UserKnowledgeService` 别名，移除硬编码 Mock 画像
- `test_concrete_user_knowledge_service.py`：改用隔离 JSON 存储 + 真实 `record_decision` 断言

### Alpha Factory IC
- `alpha_factory_orchestrator.py`：`_extract_ic_from_payload`；`analyze_experiment_result` 将 IC/权益曲线写入 vault `metadata`

### 前端 SPA
- `ExperimentReport.tsx` + `types/experiment.ts` + `fetchExperiments`/`fetchExperiment`
- 路由 `/app/experiments`，导航「实验」

### API
- `routes_v1_experiments.py`：`equity_curve` 同时从 `metadata` 读取

---

## 2026-06-16 (Sprint 16：Alpha Factory 真投递 + 图表真实行情 + Stub 清理)

### Alpha Factory
- `alpha_factory_orchestrator.py`：`evolve_factor_targeted` 投递 RD-Agent（Celery/线程）；血缘图 IC 优先读 `metadata`/`backtest_result`，Sharpe 仅作 `ic_proxy` 回退
- `factor_evolution.html`：按 `ic_proxy` 切换 IC / Sharpe 标签

### 去 Mock
- `chart_generator_tool.py`：AkShare 后复权 K 线绘图，无数据时明确报错
- `venues.py`：`RedisShadowVenue` 缺价时用最近收盘价，100 仅最后回退
- `qmt_executor.py`：标注 simulation 模式（未实单提交）
- `memory_fabric_stub.py`：修复语法/导入，确定性 embedding，标记为 deprecated stub

### 测试
- `test_alpha_factory_orchestrator.py`、`test_chart_generator_tool.py`

---

## 2026-06-16 (Sprint 15：去 Mock + 实验报告曲线 + 配置文档)

### 前端
- `factor_evolution.html`：修复 `addToBacktest` 缺 `}` 的语法错误；回测标的改用户输入/全局焦点/URL，日期滚动近 12 个月
- `integration_hub.html`：质量分由集成层 `ok/enabled` 加权计算，移除 42/68/82 等魔法数
- `experiment_reporter.html`：`artifacts.equity_curve` 渲染 SVG 折线，无数据时明确提示

### API
- `routes_v1_experiments.py`：指标/描述/曲线从 `metadata`/`artifacts` 读取（对齐 `Experiment` 实体）

### 配置
- `.env.example`：补充 `AKSHARE_BACKTEST_ADJUST=hfq` 说明

---

## 2026-06-16 (Sprint 14：Phase 14 DI + WisdomMesh 修复 + 确定性裂纹)

### DI / v1_context
- `wiring_system.py` / `wiring_trading.py` / `wiring_market.py`：注册 `risk_companion_service`、`wisdom_mesh_service`、`one_click_service`、`evolution_arbiter_service`、`active_job_tracker_service`；`strategy_synthesizer_service` 注入 `ai_adapter`
- `v1_context.py`：Phase 14 改从 `TypedServiceRegistry` 读取，移除大块 try/import 构造

### Wisdom Mesh
- `wisdom_mesh_service.py`：修复循环 shim，实现 JSONL 存储（list/upload/get/vote/leaderboard）

### 前端去随机
- `trading_dna_spiral.html`：裂纹绘制改用确定性 `pseudo(seed)`，避免 `Math.random` 闪烁

---

## 2026-06-16 (Sprint 13：前视偏差收尾 + SPA 回测历史)

### 量化 / 前视偏差
- `cn_akshare_history.py`：抽取 `fetch_cn_daily_adjust`；新增 `fetch_cn_daily_hfq`
- `investment_committee_db.py`：指数/行情拉取改后复权 `hfq`（与回测默认一致）
- 测试：`test_cn_akshare_history_adjust.py`、`test_yfinance_loader_adjust.py`（`auto_adjust=False`）

### 前端 SPA
- `RunHistory.tsx`：`GET /api/v1/mlflow/runs` 列表、多选跳转 `/backtest?duel=1`
- `App.tsx` / `Layout.tsx`：路由 `/app/runs`、导航「历史」

---

## 2026-06-16 (Sprint 12：API 限流 + 微信告警脱敏)

### API 限流
- `api_rate_limit.py`：`/api/*` 全局限流（HybridRateLimiter）；健康检查豁免；`bootstrap` 接入

### 微信告警
- `alert_notification_adapters.py`：access_token / appsecret 改 query 参数传递；日志仅记录 base URL（不含 token）

### 文档
- `docs/redis.md`：补充 API 限流与 `KEY_ENCRYPTION_SALT` 轮换说明

---

## 2026-06-16 (Sprint 11：Qlib SQL + 认证限流 Redis + 命令安全)

### SQL
- `mysql_qlib_sync_status.py` / `qlib_pipeline_service.py`：表名白名单 + `validate_identifier` + `quote_identifier`

### 认证限流
- `hybrid_rate_limiter.py`：Redis INCR/EXPIRE，无 Redis 时内存回退；`auth.py` 登录/注册接入

### 命令执行
- `command_safety.py`：禁止 `python -c`/`--command`、参数路径穿越、逐参数 shell 元字符检查

### 文档
- `docs/redis.md`：补充 `AUTH_RATE_LIMIT_REDIS_URL`

---

## 2026-06-16 (Sprint 10：密钥派生 + Cookie + TDX SQL 加固)

### 密钥加密
- `key_encryption.py`：修复 Fernet 密钥未使用 PBKDF2 派生结果的 bug；salt 可配置 `KEY_ENCRYPTION_SALT`（默认保持兼容）

### Session
- `bootstrap.py`：`SESSION_COOKIE_SECURE` 默认 `not settings.debug`，可用环境变量覆盖

### SQL
- `mysql_tdx_dayk_repository.py`：`list_history_stock_codes` 增加 `validate_identifier` + 反引号；日历查询同步反引号

---

## 2026-06-16 (Sprint 9：P0 安全与上下文修复)

### 安全 / SQL
- `sql_utils.py`：新增 `quote_identifier()`；`sentinel.py` 白名单表名加反引号引用
- `investment_committee_db.py`：表名经 `validate_identifier` + `_TABLE_SQL` 引用，值仍参数化

### API 上下文
- `v1_context.py`：优先 `strategy_synthesizer_service` 工厂；导入路径改为 `modules/strategy/...`

### 前端
- `moments.html`：自动笔记优先 `GET /api/v1/briefing/smart-daily`，失败时用按日轮换模板（无 `Math.random`）

---

## 2026-06-16 (Sprint 8：回测历史接 MLflow + Redis 文档)

### 回测历史页
- `run_history.html`：删除 `mockRuns`，改用 `GET /api/v1/mlflow/runs`；筛选/对比跳转 `strategy-compare`（同标的多策略）

### 文档
- `docs/redis.md`：移除硬编码内网 IP，改为环境变量占位说明

### 因子演化
- `factor_evolution.html`：节点初始布局改为黄金角螺旋，移除 `Math.random`

---

## 2026-06-16 (Sprint 7：经典页 Mock 清理 III)

### 信号观察单
- `signal_observations.html`：`analyzeTradingPattern()` 改用 `/signal-observations/stats` + 已关闭观察单聚合，移除 `Math.random`

### 策略对比
- `strategy_compare.html`：调用 `POST /api/v1/strategies/backtest/compare`；收益曲线改为按总收益线性插值（非随机游走）

### 个股详情
- `stock_detail.html`：`loadLiquidityAnalysis` / `loadWhaleTracker` 基于 `/api/v1/stocks/...` 与龙虎榜接口，移除随机分与假资金数

### 迷你走势图
- `market_panorama.html`、`global_radar.html`：迷你 sparkline 按涨跌幅确定性绘制，移除 `Math.random`

---

## 2026-06-16 (Sprint 6：去 Mock + DTO + 回测配置文档)

### BacktestResultDTO
- 新增 `annual_return`、`max_drawdown_pct`；`from_service` 由负小数 `max_drawdown` 推导百分数

### 组合详情
- `detail_routes._compute_portfolio_risk()`：由持仓推导风险指标，移除硬编码 mock
- `portfolio_detail.html`：调用 `/api/v1/portfolio/<id>` 展示真实 risk；删除 `Math.random` 回撤/Beta

### NL 策略页
- `nl_strategy.html`：Step 3 调用 `POST /api/v1/nl-strategy/preview`，结果区展示真实/估计回测指标

### 文档
- 新增 `docs/backtest_config.md`（费率、滑点、无风险利率、API）
- `docs/redis.md` 增加回测配置交叉引用

### 测试
- `test_facade_dtos.py`（`max_drawdown_pct` 推导）

---

## 2026-06-16 (Sprint 5：tick 滑点 + 无风险利率 + 回撤展示)

### A 股滑点
- `cn_market_rules.cn_apply_tick_slippage()`：比例滑点与 0.01 元 tick 取较大值
- `ChinaAEngine.apply_slippage` 接入 tick-aware 模型

### Sharpe 无风险利率
- `backtest/risk_free_rate.py`：`BT_RISK_FREE_SOURCE=auto` 时尝试 AkShare `bond_china_yield` 10 年期国债；`fixed`/`BT_RISK_FREE_ANNUAL` 可覆盖

### 最大回撤约定
- `calc_metrics` 输出 `max_drawdown`（负小数）+ `max_drawdown_pct`（正百分数）
- SPA `backtestMetrics` / 经典 `backtest.html` 统一为 `-X.XX%` 展示

### 测试
- `test_sprint5_market_metrics.py`
- `test_calc_metrics.py`（`max_drawdown_pct`）

---

## 2026-06-16 (Sprint 4：策略对决 API + RSI Wilder)

### 策略对决（真实回测对比）
- `BacktestFacade.compare_strategies()`：同一标的/区间并行回测 2–5 个策略，按总收益选 winner
- `POST /api/v2/strategies/backtest/compare`（SPA JWT）
- `POST /api/v1/strategies/backtest/compare`（经典页 session）
- `backtest.html` / `frontend/Backtest.tsx`：对决表格 UI

### 量化指标
- `RSIReversionStrategy`：RSI 改为 Wilder EWM 平滑（与行业标准一致）

### DTO
- `BacktestCompareRequestDTO`（`strategies` 2–5 项）

### 测试
- `tests/facade/test_backtest_facade_compare.py`
- `tests/modules/strategy/test_rsi_wilder.py`

---

## 2026-06-16 (Sprint 3：SPA 回测可视化 + 金融指标增强)

### 前端（`/app/backtest`）
- `EquityCurveChart`：权益曲线叠加真实买卖 `ReferenceDot`（绿买/红卖）
- `backtestMetrics.extractTrades()`：解析 API `trades`（兼容 BUY/SELL、profit/pnl）
- `Backtest.tsx`：交易明细表

### 后端
- `metrics.calc_metrics`：Sharpe 扣除 `BT_RISK_FREE_ANNUAL`（默认 0，可配置年化无风险利率）
- `cn_market_rules.cn_stamp_tax_rate_for_date`：印花税分段（2023-08 / 2024-10 节点）
- `china_a.calc_commission`：卖出印花税按 `_trade_ts` 交易日历分段
- `base.py`：`_trade_ts` 供子引擎费率计算

### 测试
- `test_china_a_market_rules.py`（印花税分段 + 历史日期）
- `test_calc_metrics.py`（无风险利率 Sharpe）

---

## 2026-06-16 (Sprint 2：A 股交易规则与费率校准)

### T+1（交易日历语义）
- 新增 `engines/cn_market_rules.py`：`a_share_t1_blocks_sell()` 基于 `entry_bar_idx` 判断，替代日历日比较
- `china_a.py` / `composite.py`：停牌复牌后不再因跨自然日误放行 T+0 卖出

### 费率默认值（与现行规则对齐）
- 印花税默认 `0.00025`（万2.5，2023-08-28 起）
- 过户费默认 `0.00002`（万2 双边）
- `core/risk_controls.TradeCostParams` + `BT_STAMP_DUTY` / `BT_TRANSFER_FEE` 等 env 键同步

### 可观测性
- `base.py`：缩仓后不足一手时记录 `warning`（原静默失败）

### 测试
- `tests/infrastructure/agent/backtest/test_china_a_market_rules.py`
- `tests/core/test_trade_cost_defaults.py`

---

## 2026-06-16 (Sprint 1：量化引擎加固 + 回测图表数据)

### 金融指标
- `rust_core` / `wasm_core`：`calculate_sharpe_ratio` 改为样本标准差（ddof=1），与 NumPy 回退路径一致
- `infrastructure/agent/backtest/metrics.py`：Sharpe 显式 `ddof=1`；Sortino 下行偏差按全样本期计算；输出 `sharpe_ratio` 别名
- `infrastructure/providers/backtest_engine.py`：`_compute_metrics` 改用 `native_compute` 的 Sharpe/MDD/年化收益，替换错误的 `total_return/max_dd` 伪 Sharpe

### 回测 API / 图表
- `BacktestEngine`：`simulate_single` / `simulate_portfolio` 返回 `stock_data`（dates/closes）与 `equity_curve`
- `domain/entities.BacktestReport`：新增 `to_dict()`，修复 provider `backtest()` 无法序列化报告的问题

### 测试
- `tests/infrastructure/agent/backtest/test_calc_metrics.py`
- `tests/infrastructure/test_native_compute_sharpe.py`
- `tests/infrastructure/providers/test_backtest_engine_chart_payload.py`
- `tests/domain/test_backtest_report_to_dict.py`

---

## 2026-06-16 (Sprint 0：AUDIT 止血 — 量化可信 + 安全 + 去 Mock)

### 量化引擎
- `modules/strategy/logic/factor.py`：momentum 突破改为 `rolling(lookback).max().shift(1)`，消除自比较假信号
- `infrastructure/agent/backtest/engines/base.py`：补 `MarketDataQualityGate` import；benchmark 字段在 `calc_metrics` 之后写入，修复 `m` 未定义
- `infrastructure/agent/backtest/loaders/akshare_loader.py`：回测默认 `hfq`（`AKSHARE_BACKTEST_ADJUST` 可覆盖），替代 `qfq` 前视偏差

### 安全
- `infrastructure/auth/jwt_token_service.py`：`API_JWT_SECRET` 最短 32 字符

### 前端可信
- `presentation/web/templates/backtest.html`：图表使用真实 `trades`/`equity_curve`；删除 `Math.random` 假交易与策略对决 mock

### 测试
- `tests/modules/strategy/test_momentum_alpha_strategy.py`
- `tests/infrastructure/agent/backtest/test_akshare_loader_adjust.py`
- `tests/infrastructure/agent/backtest/test_backtest_engine_base_imports.py`
- `tests/infrastructure/test_jwt_token_service.py`（短 secret 拒绝 + fixture 加长）

---

## 2026-06-16 (今日操盘台数据修复)

### 问题
- 涨跌家数仅 ~101（扫描缓存小样本），与 A 股 5000+ 全市场不符
- `recommendation_service` 工厂无参构造失败 → Top 3 不可用
- `news_provider` / `task_message_store` 未注册到 ServiceRegistry → 快讯与任务消息为空

### 修复
- `market_service.get_sentiment`：缓存样本 <1500 或过期时，AkShare `stock_zh_a_spot_em` 全市场统计并回写缓存
- `wiring_ai._make_recommendation_service`：注入 selection / trade_plan / ai_evidence 等依赖
- `wiring_market`：注册 `news_provider`、`task_message_store` 工厂；操盘台改用 `get_or_none`
- `daily_workbench_service`：将 sentiment 广度合并进 panorama；推荐空态中文提示
- `daily_workbench.html`：任务消息未连接时的文案优化

### 测试
- `tests/modules/market_data/test_market_service_sentiment.py`

### 追加修复（验证阶段）
- `recommendation_service._candidate_rows` 恢复（此前方法体误挂在 `daily_top` return 之后）
- `create_signal_observation_repository(sf)` 参数修正，解除 `daily_workbench_service` 工厂级联失败
- `bootstrap.register_blueprints` 注入 `task_message_store`；操盘台可选依赖改为 `get_or_none`

---

## 2026-06-16 (Phase A：止血与可信)

### A1 架构 — Critical 服务启动冒烟
- `service_readiness.py`：新增 `CRITICAL_RESOLVE_SERVICES` + `resolve_all_critical_services()`
- `services.py`：引导完成后 eager resolve（workbench / market / recommendation / task_message_store）
- 测试：`tests/unit/test_service_readiness_critical.py`

### A2 量化 — DataLake API 闭合
- `data_lake_manager.py`：`get_data()` / `save_data()` / `get_system_health()`；SQLite 桥 + 行情回退 + P95 延迟
- `fast_backtest_engine.py`：返回 `data_source`（lake/market/synthetic）与中文降级警告
- `unified_data_lake.py`：补 `Tuple` 导入、`ffill` 弃用 API 修复
- 测试：`tests/unit/test_data_lake_manager.py`

### A3 量化 — Alpha Factory 演示标注
- `alpha_factory.py`：`/alpha-factory/simulate` 响应增加 `meta.demo` + `disclaimer`
- `quant_lab.html`：演示模式 toast 提示

### A4 安全 — CSRF 分路径
- `csrf_protection.py`：尊重 `@with_csrf_exempt`；已登录 API 继续校验 `X-CSRF-Token`
- `bootstrap.py`：注明 `WTF_CSRF_ENABLED=False` 由自定义中间件承担
- 测试：`tests/unit/test_secrets_scan.py`（禁止 `AdminPassword123!` / `root123` / 硬编码 Redis IP）

### A5 前端 — 统一 API 客户端
- `base.html` 全局加载 `api_client.js`（`QCApi` + `unwrap`）
- `daily_workbench.html` / `quant_lab.html` / `stock_detail.html` 主路径改用 `QCApi`

---

## 2026-06-16 (Phase B：产品收敛)

### B1 导航 IA 瘦身（6 → 4）
- `base.html` 顶栏：**操盘台 / 研究 / 策略 / 我的**
- 投委会三入口合并为单一「AI 投委会」；系统/因子/工作台收敛进「我的」折叠组
- 策略向导、数据湖健康纳入「策略」菜单

### B2 零售路径合并
- `/user-tiers/retail` → 302 `/retail-assistant`
- 导航仅保留「零售 AI 助手」

### B3 Truth Badge 统一
- `static/js/truth_badge_client.js`（`QCTruthBadge.load`）
- `evidence_card.html`、`qa-truth-badge.js` 共用 API 路径

### B4 契约测试
- `tests/presentation/test_phase_b_nav_contract.py`

---

## 2026-06-16 (Phase C：架构还债)

### C1 兼容 shim 收敛策略
- `app/application/services/_shim_policy.py`：按模块单次 `DeprecationWarning`
- `strategy_service.py` 等高流量 shim 接入警告（未批量删除 90+ 文件，避免破坏旧 import）

### C2 v1 API 弃用头
- `app/presentation/api/v1_deprecation.py`：`Deprecation` / `Sunset` / `Link` / `X-API-Version`
- `bootstrap.py` 注册 `register_v1_deprecation_headers`

### C3 测试分层
- `pyproject.toml` 新增 `nightly` marker
- `conftest.py`：`flask_app` / `client` 使用者自动标 `slow`
- `tests/smoke|api|bootstrap/conftest.py` 模块级 `slow`
- CI 默认 `pytest -m "not slow"`；`.github/workflows/nightly.yml` 跑 slow + 架构门禁

### C4 模块依赖环门禁
- `scripts/check_module_cross_imports.py`：6 对跨模块 import 基线计数，只增不减

### C5 Qlib 回测单轨
- `qlib_backtest_service.py`：委托 `QlibPipelineService` / `QlibService`；失败时 `meta.demo` + 中文 disclaimer

### 测试
- `tests/architecture/test_phase_c_gates.py`
- `tests/unit/test_qlib_backtest_service.py`

---

## 2026-06-16 (Phase D：商业化准备)

### D1 合规文案统一
- `app/domain/compliance/retail_manifest.py`：投资免责 / 隐私说明 / Beta SLA 常量
- `GET /api/v1/compliance/manifest`（`routes_v1_compliance.py`）
- `static/js/compliance_footer.js` + `base.html` 页脚动态加载

### D2 SLA 对外契约
- `docs/SLA.md`：Beta 可用性、数据新鲜度、复核 SLA
- `GET /api/v1/system/sla`

### D3 权限策略修复
- 修复 `UserAccessPolicyService` 循环 import；实现 Free/Pro/Admin 快照（`snapshot_for_user`）

### D4 决策复核产品化
- `DecisionReviewQueue`：`priority` / `review_by` / `product_summary()`
- `GET /api/v1/decision/review-queue/summary`
- 预交易 `preflight` 未通过或风险分 < 45 自动入队（`review_queued` 字段）
- 操盘台「待复核决策」卡片（`daily_workbench.html`）

### 测试
- `tests/architecture/test_phase_d_commercial.py`

---

## 2026-06-16 (Phase E：可观测性与测试修复)

### E1 观测快照 API
- `ObservabilitySnapshotService`：聚合 pulse / health_banner / SLA / critical_services / decision_review
- `GET /api/v1/system/observability/snapshot`（需登录）

### E2 观测台 UI
- `observability.html`：Beta SLA、Critical Path 指标卡；`loadObservabilitySnapshot()` 统一拉取

### E3 计费占位
- `retail_billing.py` + `GET /api/v1/billing/status`（Stripe Beta 占位，未启用扣费）

### E4 CI 收集修复
- 删除 `tests/test_config_minimal.py`（非 pytest、硬编码路径）
- 新增 `tests/unit/test_app_settings_minimal.py`

### 测试
- `tests/architecture/test_phase_e_observability.py`

---

## 2026-06-16 (Phase F：依赖与配置治理)

### F1 可选依赖 extras
- `pyproject.toml`：`[compute]`（polars、vectorbt）、`[qlib]`（pyqlib）、`[test]`；`setuptools` 可编辑安装
- `requirements-compute.txt` / `requirements-qlib.txt`：标注 canonical `pip install -e ".[...]"`；qlib 文件移除与主依赖重复的 `rdagent`

### F2 漂移门禁与前端 lock
- `scripts/check_dependency_drift.py`：校验主依赖 + optional extras 与 requirements-*.txt 对齐
- CI：`frontend-security` job 执行 `npm ci` + `npm audit --audit-level=high`
- `docs/dependencies.md`：统一 extras 安装说明与 CI 扫描项

### 测试
- `tests/architecture/test_phase_f_dependencies.py`

---

## 2026-06-16 (Phase G：可观测性增强)

### G1 业务指标与 HTTP 中间件
- `app/core/metrics.py`：`BACKTEST_COMPLETED`、`AI_CALLS_TOTAL` 计数器
- `app/core/metrics_helpers.py`：`record_http_request` / `record_ai_call` / `record_backtest_completed` / `instrument_chat_model`
- `app/core/middleware/prometheus_middleware.py`：Flask 请求延迟与 QPS 采集
- `fast_backtest_engine`：预览成功时递增回测计数
- `llm_user_config` / `LLMFactory.get_model`：LLM invoke 自动打点
- `deploy/grafana/dashboards/quant-atlas-overview.json`：回测/AI 面板 + 修正 errors 指标名

### G2 结构化日志
- `resilience.init_context` 同步 `set_request_id`；`structlogger` 注入 `request_id` / `user_id`
- `bootstrap.py` 注册 `init_request_context_middleware` + `init_prometheus_middleware`

### 测试
- `tests/architecture/test_phase_g_observability.py`

---

## 2026-06-16 (Phase H-1：前端 SPA 脚手架)

### H1 React + Vite 工程
- 新增 `frontend/`：React 19 + TypeScript + Vite 6 + Tailwind + DaisyUI
- 页面：`Login` / `Dashboard`（v2 health + panorama）/ `Backtest`（占位）
- `src/lib/api.ts`：v2 响应解包 + JWT Bearer 存储
- `useTheme`：亮/暗主题切换（玻璃拟态卡片样式）

### H1 Flask 托管
- `pages_spa.py`：`/app` 与 `/app/<path>` 托管 `frontend/dist`（未构建时 404 提示）

### CI
- `frontend-security` job 改为在 `frontend/` 执行 `npm ci` + `npm run build` + `npm audit`

### 测试
- `tests/presentation/test_phase_h_spa_scaffold.py`

### 本地开发
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173/app/
npm run build                               # 产出 dist，Flask /app 可访问
```

---

## 2026-06-18 (登录 CSRF：经典页 + SPA Session 登录)

### 问题
- `POST /login` 返回 403：`CSRF validation failed`

### 修复
- `login.html`：表单内 `{{ csrf_html() }}`，`<meta name="csrf-token">` 供 SPA 读取
- `loginWithSession()`：先 GET `/login` 取 token，再随表单/header 提交
- 测试：`tests/presentation/test_login_csrf.py`

---

## 2026-06-18 (Bootstrap：恢复 wiring 模块 side-effect 导入)

### 问题
- `run.py` 启动报 `ImportError: wire_recommendation_service`
- `watchlist_service` / `stock_group_service` / `daily_workbench_service` / `auth_service` 等未注册，路由与登录蓝图失效

### 修复
- `service_wiring.py` 增加 `wiring_market` / `wiring_ai` / `wiring_system` / `wiring_trading` 侧效导入，注册 `register_factory`
- 补回 `wire_recommendation_service()`，在模块初始化后解析 `recommendation_service`
- `wiring_trading.py`：`trade_plan_service` 改为注入 `market_service`（修复 zero-arg 覆盖导致工厂返回 None）

---

## 2026-06-16 (Phase H-15：治理时间线 + MLflow↔提案双向关联 + 配置状态条)

### H15 治理 DAO
- `find_proposals_by_mlflow_run()`：按 run_id 反查治理提案
- `build_proposal_timeline()`：提交 → 投票 → 计票/激活 时间线
- `get_proposal()` 响应增加 `timeline`

### H15 API
- `GET /mlflow/runs/<id>` 增加 `linked_proposals`
- `GET /mlflow/models` 各版本增加 `linked_proposals`（经 run_id）
- `GET /alpha/governance/workbench` 的 `mlflow.config` 附带 `get_tracking_config()`

### H15 SPA / 经典版
- `GovernanceTimeline`：提案详情审批时间线
- `MlflowConfigBar`：Runs / 治理 Tab 展示 tracking URI、实验名、自动注册开关
- `MlflowRunModal`：展示关联提案并可跳转提案详情
- Model Registry 表增加「治理」列（关联提案数）
- 经典版 MLflow 详情弹窗展示关联提案 ID

### 测试
- `test_find_proposals_by_mlflow_run` / timeline 断言
- `test_mlflow_run_detail_includes_linked_proposals`
- scaffold 增加 `GovernanceTimeline`、`MlflowConfigBar`

---

## 2026-06-16 (Phase H-14：MLflow UI 深链 + 可选模型注册 + 治理投票流)

### H14 MLflow Registry
- `ModelRegistry.get_tracking_config()` / `build_run_ui_url()`：为 run 生成 MLflow UI 外链
- `log_backtest()` 返回 `{run_id, experiment_id, ui_url, model_name?, model_version?}` 字典
- `MLFLOW_REGISTER_MODELS=1|true|yes` 时回测后自动 `register_model`（pyfunc）
- `list_recent_runs()` / `get_run()` 响应附带 `ui_url`
- `GET /api/v1/mlflow/status` 使用 `get_tracking_config()`（含 tracking_uri / register_models）

### H14 回测与治理
- `attach_mlflow_run_id` 写入 `mlflow_model_name` / `mlflow_model_version`
- `BacktestResultDTO` 增加模型注册字段
- `AlphaGovernanceDAO.stats()` 增加 `thresholds.majority` / `thresholds.quorum`

### H14 SPA / 经典版
- `GovernanceVoteFlow`：步骤条 + 通过率进度条
- `GovernanceProposalModal` / Marketplace 治理 Tab 集成投票流与阈值展示
- `MlflowRunModal`、Runs/治理 MLflow 表增加「MLflow UI」外链
- `Backtest` 结果展示已注册模型名/版本
- 经典版 `marketplace.html`：治理阈值标签、MLflow 详情弹窗 UI 外链

### 测试
- `test_mlflow_registry.py`：`build_run_ui_url` / `get_tracking_config`
- `test_backtest_log_hook.py`：dict 返回值与模型字段
- `test_v1_mlflow_routes.py`：`test_mlflow_status`
- `test_v1_alpha_governance_routes.py`：stats thresholds 断言

---

## 2026-06-16 (Phase H-13：模型注册表 + MLflow 深链 + 经典版详情)

### H13 Model Registry API
- `ModelRegistry.list_registered_models()`：`search_model_versions` + 关联 run 指标
- `GET /api/v1/mlflow/models`：模型名/版本/阶段/Sharpe

### H13 SPA 深链与详情
- `MlflowRunModal`：Runs / Model Registry 点击 run → 详情弹窗；可一键填入治理提案
- URL 深链：`?proposal_id=`、`?run_id=`、`#runs`；治理预填仍用 `mlflow_run_id`（与 `run_id` 查看分离）
- Runs Tab 拆为「回测实验」+「模型注册表」两表

### H13 经典版 Marketplace
- 提案详情 / MLflow run 详情弹窗；治理表提案 ID、MLflow 行可点「详情」

### 测试
- `test_v1_mlflow_routes.py` 增加 `test_mlflow_registered_models`
- `test_phase_h_spa_scaffold.py` 增加 `MlflowRunModal`

---

## 2026-06-16 (Phase H-12：MLflow 详情 + 提案详情 + 异步回测闭环)

### H12 MLflow 运行详情
- `ModelRegistry.get_run(run_id)`；`GET /api/v1/mlflow/runs/<run_id>`

### H12 治理提案详情
- SPA `GovernanceProposalModal`：点击提案 ID 展示投票审计、绩效、MLflow/挖掘血缘及关联 run 指标

### H12 回测 MLflow 统一钩子
- `attach_mlflow_run_id()` 供 `BacktestFacade` 与 Celery `run_strategy_backtest` 共用；异步任务完成后同样带回 `mlflow_run_id`

### H12 异步回测轮询
- `runBacktest(async=1)` 自动轮询 `GET /api/v1/system/celery/task/<id>` 直至 SUCCESS；回测页展示轮询提示

### 测试
- `test_v1_mlflow_routes.py`、`test_backtest_log_hook.py`；`test_phase_h_spa_scaffold.py` 增加治理详情组件

---

## 2026-06-16 (Phase H-11：治理血缘关联 + 挖掘运行 + 回测→治理预填)

### H11 提案血缘字段
- `FactorProposal` / `submit_proposal()` 新增可选 `mlflow_run_id`、`mining_factor_id`；持久化至 `instance/alpha_proposals.json`
- `POST /api/v1/alpha/governance/proposals` 接受上述字段；`propose_to_dao()` 自动写入 `mining_factor_id`

### H11 回测 → MLflow run_id
- `BacktestResultDTO.mlflow_run_id`；`BacktestFacade.run_backtest()` 在 MLflow 记录成功后回填响应

### H11 前端闭环
- SPA：`runAlphaMining()` + 治理 Tab「运行挖掘」；提案表单携带 MLflow/挖掘关联；提案表展示血缘列
- `BacktestPage`：回测成功后「提交治理提案」跳转 `/marketplace?strategy&symbol&sharpe&mlflow_run_id#governance`；移除冗余登录守卫（`ProtectedRoute` 已覆盖）
- 经典版 `marketplace.html`：运行挖掘、URL 预填、提案提交携带关联 ID

### 测试
- `test_v1_alpha_governance_routes.py`：`test_submit_proposal_with_lineage_ids`、`test_alpha_governance_proposal_api_accepts_lineage`

---

## 2026-06-16 (Phase H-10：治理工作台 + 挖掘提案 + SPA 体验)

### H10 治理工作台 API
- `GET /api/v1/alpha/governance/workbench`：聚合 stats、提案、投票、MLflow runs、挖掘因子

### H10 挖掘 → DAO 一键提案
- SPA 治理 Tab：`proposeMiningFactorToDao` → `POST /alpha-mining/factors/<id>/propose`
- 经典版 `marketplace.html` 同步挖掘表 + MLflow 表 + 一键提案

### H10 SPA 体验
- `PageSkeleton` 统一加载骨架；`NotFoundPage` 404
- `ProtectedRoute` / 操盘台 / 治理 Tab 使用骨架屏

### 测试
- `test_v1_alpha_governance_workbench.py`
- `test_phase_h_spa_scaffold.py` 扩展 NotFound / PageSkeleton

---

## 2026-06-16 (Phase H-9：提案持久化 + 经典版治理 + SPA 路由守卫)

### H9 提案 JSON 持久化
- `AlphaGovernanceDAO`：`instance/alpha_proposals.json` 读写提案；启动时从 JSONL 投票历史 `_reconcile_vote_counts()`；`_rebuild_active_factors()`
- `submit_proposal` / `vote` / `tally_votes`（通过）后自动 `_save_proposals()`

### H9 经典版 Marketplace 治理
- `marketplace.html`：「因子治理」Tab + 提案/投票/审计表；支持 `#governance` 深链；「SPA 治理」跳转 `/app/marketplace#governance`

### H9 SPA 路由守卫
- `ProtectedRoute`：未登录重定向 `/app/login`，保留 `state.from` 回跳
- `LoginPage` 登录成功后回到来源页
- `App.tsx` 业务路由包裹在 `ProtectedRoute` 内

### 测试
- `test_alpha_governance_vote_history.py` 新增 `test_proposal_persists_and_reloads`
- `test_phase_h_spa_scaffold.py` 增加 `ProtectedRoute.tsx`

---

## 2026-06-16 (Phase H-8：因子治理 API + Socket AI 广播 + SPA 登录)

### H8 因子治理 REST
- `AlphaGovernanceDAO.list_proposals()` / `get_proposal()` 序列化内存提案
- `routes_v1_alpha_governance.py`：`GET/POST /alpha/governance/proposals`、`POST /vote`、`GET /votes`、`GET /stats`
- Marketplace SPA「因子治理」Tab：提案列表、投票、JSONL 审计历史

### H8 AI Socket.IO 镜像
- `broadcast_ai_analysis_chunk()` → room `ai_analysis` / event `ai_analysis_chunk`
- `ai_analyze_stream` SSE 每 chunk 同步广播
- `useRealtime` 订阅 `ai_analysis`；操盘台 `RealtimeBar` 显示最近 AI 流步骤

### H8 SPA 登录体验
- `Layout`：登录态 / 退出（`logoutSession` → `/logout`）
- `Login`：经典登录页链接
- `api.ts`：`fetchGovernance*`、`castGovernanceVote`、`logoutSession`

### 测试
- `tests/presentation/test_v1_alpha_governance_routes.py`
- `test_alpha_governance_vote_history` 仍覆盖 JSONL 持久化

---

## 2026-06-16 (Phase H-7：MLflow 列表 + AI 流式诊股 + 经典版 SPA 入口)

### H7 MLflow 实验列表
- `ModelRegistry.list_recent_runs()` + `GET /api/v1/mlflow/runs`
- Marketplace SPA「回测实验」Tab 展示 run 指标

### H7 AI 流式诊股
- `useAnalysisStream`（EventSource → `/api/v1/ai/analyze/stream`）
- 个股页 `AiInsightPanel`：步骤时间线 + 决策摘要

### H7 经典版导航
- `base.html` 操盘台/策略菜单增加 SPA 回测、因子市场入口

### 测试
- `test_v1_mlflow_routes.py`、`test_mlflow_registry` 扩展 list runs

---

## 2026-06-16 (Phase H-6：个股详情 + MLflow 桩)

### H6 个股 SPA
- 修复 v2 `GET /stocks/<symbol>`：改用 `get_stock_detail`（原错误调用不存在的 `get_stock_info`）
- `StockQuoteCard` + `PriceHistoryChart`（收盘线 + 成交量）
- `fetchStockHistory` → `/api/v2/stocks/<symbol>/history`
- Recharts 图表懒加载（个股 / 回测分包）

### H6 MLflow（可选）
- `app/infrastructure/mlflow/registry.py`：`ModelRegistry.log_backtest`，未安装 mlflow 时 no-op
- `BacktestFacade.run_backtest` 成功后自动打点（total_return / sharpe / max_drawdown / win_rate）
- `pyproject.toml` 新增 optional `mlops` extra（`mlflow>=2.12`）

### 测试
- `tests/infrastructure/test_mlflow_registry.py`
- `tests/presentation/test_v2_stock_detail.py`

---

- `recharts` 权益曲线 `EquityCurveChart`（解析 `equity_curve` / `metrics`）
- 回测页指标卡片 + 可折叠原始 JSON

### H5 Alpha Marketplace SPA
- `Marketplace.tsx`：浏览 / 订单 / 上架 / 声誉四 Tab
- `api.ts`：声誉余额、listings、orders、contribute、list、cancel、credit
- 导航增加「因子市场」→ `/app/marketplace`

### H5 操盘台 polish
- AI 推荐卡片链接至 SPA 个股详情

### 测试
- `test_phase_h_spa_scaffold.py` 扩展 Marketplace / EquityCurve 文件清单

---

## 2026-06-16 (Phase H-3/H-4：SPA 实时行情与回测页)

### H3 Socket.IO 实时
- `socket.io-client` + `useRealtime` hook（`quote_update` / `subscribe` alerts）
- `RealtimeBar` 操盘台连接状态与最新行情条
- Vite dev 代理 `/socket.io`（WebSocket）

### H4 回测页
- `Backtest.tsx`：完整回测（`POST /api/v2/strategies/backtest`）+ 向导快速预览（`POST /api/v1/strategy/wizard/preview`）
- `api.ts`：`listStrategies` / `runBacktest` / `fetchWizardTemplates` / `previewStrategy`
- `types/backtest.ts` 类型定义

### 测试
- `test_phase_h_spa_scaffold.py` 扩展 H-3 文件清单

---

## 2026-06-16 (Phase H-2：操盘台 SPA 迁移 MVP)

### H2 操盘台数据层
- `fetchDailyWorkbench` 对接 `GET /api/v1/daily-workbench`（Session Cookie）
- `loginWithSession`：表单 POST `/login`，与经典版共用会话
- `useAuth`：自动探测 JWT / Session 登录态

### H2 UI 组件
- 市场天气、涨跌家数、宏观指数、决策面板、自选股、AI 推荐、待复核决策
- `StockDetail` 页：v2 `/stocks/<symbol>` + 经典版 fallback 链接
- `base.html` 导航增加「SPA 操盘台」入口

### 测试
- `test_phase_h_spa_scaffold.py` 扩展文件清单

---

### 问题
- `quant_lab.html` 中 ECharts `<script src>` 未闭合，内联 `handleQlAction` 被浏览器忽略，按钮点击无响应

### 修复
- 正确加载 `echarts.min.js`；事件委托与模拟逻辑合并到同一 `nonce` 脚本块
- `runSimulation` 兼容 `success`/`ok`/`status` 响应格式，并处理 401 等错误提示

---

## 2026-06-16 (CSP 内联事件 Batch-4 — 全站清零)

### 范围（80 → 0）
- **4 处页面**：`ai_analysis`、`ai_investment_committee`、`attribution_dashboard`、`observability`
- **user_tiers 五档**：`investment` / `fund` / `institution` / `boutique` / `retail`
- **3 处页面**：`factor_evolution`、`integration_hub`、`shadow_account`、`signal_flag`
- **2 处及小组件**：`ai_committee_dashboard`、`capabilities`、`decision_brief_strip`、`factor_detail`、`longhu_bang`、`yanbao_hub`、`tdx_blocks`、`task_detail`、`selection_result`、`research_pipeline`、`portfolio_resonance`、`truth_droplet` 等
- **1 处收尾**：`zen_terminal`（`onchange` → `addEventListener`）
- **宏**：`partials/macros.html` `btn` 宏移除 `onclick` 参数，改用 `data-ui-action`
- **导航**：`strategy_compare` 返回按钮改为 `<a href>`

### 测试
- `test_csp_inline_handlers.py` baseline **0**；新增 `test_all_templates_have_no_inline_handlers`

---

## 2026-06-16 (CSP 内联事件 Batch-3)

### 范围（-83 处，163 → 80）
- **工作台/策略**：`professional_workbench.html`(17)、`nl_strategy.html`(16)、`nl_strategy_v2.html`(8)
- **用户/组合/消息**：`user_spectrum_hub.html`(8)、`run_history.html`(8)、`portfolio_detail.html`(8)、`message_center.html`(7)
- **编排/报告**：`swarm_dashboard.html`(6)、`experiment_reporter.html`(5)
- **模式**：`data-*-action` 文档级委托；`select` 改 `addEventListener('change')`；动态 HTML 同样用 `data-action`（如 `data-rh-action`、`data-copy-id`）

### 测试
- `test_csp_inline_handlers.py` baseline **80**；固定零内联页面扩展至 **27** 个

---

## 2026-06-16 (CSP 内联事件 Batch-2)

### 范围（-164 处，327 → 163）
- **大块页面**：`ai_hedge_fund.html`(39)、`alpha_factory.html`(33)、`expert_teams.html`(31)、`global_radar.html`(18)
- **中块页面**：`retail_assistant.html`(13)、`agent_center.html`(10)、`quant_lab.html`(9)、`backtest.html`(5)、`stock_selector.html`(6)
- **工具**：`scripts/csp_migrate_batch.py` 批量替换 + 各页 `data-*-action` 事件委托
- **修复**：`backtest.html` 误插入 echarts `<script>` 标签问题已纠正

### 测试
- `test_csp_inline_handlers.py` baseline **163**；固定零内联页面扩展至 **18** 个

---

### 范围
按优先级移除 HTML `onclick` / `onchange` 等内联处理器（`script-src` 仅 nonce，属性内联被拦）。

### P0 页面
- **`stock_detail.html`**：`data-stock-action` + 文档级 `handleStockDetailAction`（含动态 HTML 拼接）
- **`index.html`**：`data-index-action`；股票卡片改为 `<a href>` 导航
- **`signal_observations.html`**：`data-obs-action` + 模态 `modal-backdrop` 委托

### P1 页面
- **`daily_workbench.html`**：`data-wb-action`（焦点、市场切换、采纳观察单等）
- **`marketplace.html`**：`data-mp-action`（贡献、披露、取消订单等）
- **`strategy_wizard.html`**：`data-wizard-action`（步骤/预览/创建）

### static/js 快速修复
- **`agent_app_da_ban_radar.js`**、**`qa-truth-badge.js`**、**`components/qa-truth-badge.js`**：`innerHTML` 关闭按钮改 `addEventListener`

### 测试
- **`tests/presentation/test_csp_inline_handlers.py`**：模板 baseline **327**（原 402）；`static/js` baseline **0**；固定页面清单扩展至 9 个核心模板

---

### 全景 `qcWatchlistButton is not defined`
- **`base.html`**：全局引入 `static/js/watchlist_quick_actions.js`（与 `base_app.js` 同序加载）
- **`market_panorama.html`**：`renderTable` 内对 `window.qcWatchlistButton` 做存在性判断，脚本未就绪时不报错

### 自选 `groups.map is not a function`
- **`self_stocks.html`**：`extractData()` 兼容 `data` 为数组、`data.groups`、顶层 `groups`；非数组时回退 `[]`
- **`index.html`**：`loadGroups()` 与 API 契约对齐（`ok_collection` 返回 `data: items[]`）

---

## 2026-06-16 (信号旗扫描 CSRF 403)

### POST `/api/v1/signal-flag/scan` → 403 CSRF validation failed
- **根因**：`base_app.js` 仅 patch `fetch` 注入 CSRF；`signal_flag.html` 等页面用 `$.ajax`/`$.post` 未带头
- **修复**：`base_app.js` 增加 `jQuery.ajaxPrefilter` 统一注入 `X-CSRF-Token`；移除依赖 `.js-nav-bell-badge` 的脆弱判断
- **`api_client.js`**：`QCApi` 变更请求同样附带 CSRF 头

---

## 2026-06-17 (自选 Agent 500 + 全市场纵览仅 249 条)

### `GET /api/v1/watchlist/experience` → 500 `'str' object has no attribute 'get'`
- **根因**：`config/stock_groups.json` 为旧版 `{groups, items}` 按用户嵌套；`JsonStockGroupRepository.list_groups()` 把整个 dict 当列表迭代，键名 `"groups"`/`"items"` 变成 str
- **修复**：`JsonStockGroupRepository` 统一 canonicalize 新旧两种格式，读取时自动迁移为 `[{id, name, symbols}]`；`WatchlistAgentService._safe_groups` 过滤非 dict 项

### 自选股「查看详细对比」点击无效（2026-06-17）
- **根因**：同 CSP，`self_stocks.html` 大量 `onclick` 被拦截（含影子操盘、新增/导入、卡片操作）
- **修复**：统一 `data-watch-action` + `bindWatchPageActions()` 事件委托；模态框 backdrop 用 `addEventListener`

---
- **根因**：CSP `script-src` 仅允许 nonce 脚本，分页/排序/刷新使用 `onclick`/`onchange` 内联处理器被浏览器拦截
- **修复**：`market_panorama.html` 改为 `#pagination` 事件委托 + `data-page`；表头 `data-sort`；刷新/分组用 `addEventListener`

---
- **根因**：`MarketApplicationService._list_cn_quotes` 缓存有任意行数即提前返回，未校验是否达到全市场规模
- **修复**：全市场请求缓存不足 `_CN_FULL_MARKET_MIN_ROWS`（1500）时走 AkShare 实时刷新；抽取 `_fetch_live_cn_snapshot()` 便于测试

### 股票详情页多接口 500（2026-06-17）
- **parse_market / ok_response**：拆分 `routes_stock` 后 11 个子路由文件漏导入；`decorators.service_fallback` 漏 `ok_response`
- **industry_chain / tdx blocks**：`preload_service_modules()` 中 `@register_service` 覆盖 factory，registry 把类当实例返回；`TypedServiceRegistry.register/resolve` 保留 factory 并实例化 class
- **K 线 history 400**：误用响应 DTO `StockHistoryDTO` 校验 query；改为 `domain.dto.stock_request_dto.StockHistoryRequest`
- **续**：补 `MarketCode`/`logger`/`build_sector_context`/`ok_resource`/`ValidationError`/`parse_int_param` 等拆分漏导入

---

### 自选应走 MySQL 却用了 JSON（2026-06-17 续）
- **根因**：`wiring_market._make_watchlist_service` / `_make_stock_group_service` 硬编码 `Json*Repository`；`create_services` 未注入 `session_factory`
- **修复**：`resolve_registry_session_factory()` 从 `db_manager` 解析 MySQL session；`use_mysql` 时用 `create_watchlist_repository` / `create_stock_group_repository`
- **全市场 249 续**：AkShare 失败时增加 Tencent 分批拉取（`stock_info_a_code_name` + `_fetch_fresh_quotes_dict`）

---

### 根因 · 几乎所有页面 JS 不执行
- **`scripts/patch_csp_script_nonces.py`** 批量补 nonce 时**漏写闭合 `>`**，导致 `<script nonce="...">` 变成非法标签，内联脚本整块失效
- 表现：首页情绪/股票列表/四榜、全市场纵览「正在同步…」、全球资产透视塔等全部停留在 loading

### 修复
- **新增** `scripts/fix_csp_script_tag_closing.py`：修复 **99** 个模板内联 `<script>` 标签
- **修正** `patch_csp_script_nonces.py` 替换逻辑，补回 `>`
- **回归** `tests/presentation/test_csp_script_tags.py`：扫描全部模板，防止复发
- **`market_service.get_sentiment`**：naive/aware datetime 混用导致 stale 判断告警，统一为 UTC aware

### 路由 svc 未定义 + sentiment 404
- **`routes_v1_jarvis.py`**：`body = getattr(...)` 误写，改为 `svc`；`semantic-route` 请求体改名为 `req_body`
- **`routes_v1_ai_evidence.py` / `routes_v1_collaboration.py` / `routes_v1_arbiter.py` / `v1/trade_plan/plan_routes.py`**：同类 `svc`/`arbiter` 未定义修复
- **`routes_market_sentiment.py`**：注册 `/market/sentiment/diary` 与 `/pulses` 别名（前端路径）
- **`routes_v1_system_health.py`**：移除返回空数据的 diary stub，避免覆盖真实实现

---
- **`RiskConfigDTO` / `PositionSizingDTO`**：`app/domain/dto/analytics_dto.py`
- **`PreTradePreflightService`**：preflight 拆为 `_collect_issues` / `_compute_position_sizing`；补 `get_logger`
- **单测** `tests/domain/test_pre_trade_dto_e1.py`

---

## 2026-06-16 (.env 中 MySQL / TDX 配置未生效)

### 根因
- Pydantic Settings 仅从 `.env` 绑定**顶层**字段（`DATABASE_BACKEND` 可读）；嵌套 `DatabaseConfig` / `TdxConfig` 的 `MYSQL_*`、`TDX_ROOT_PATH` 未注入
- `DatabaseConfig.use_mysql` 误读硬编码 `backend=sqlite`，忽略 `DATABASE_BACKEND=mysql`
- `Field(validation_alias=...)` 未开 `populate_by_name`，validator 合并的 `mysql_host` 等字段名被 Pydantic 丢弃

### 修复
- `DatabaseConfig` / `TdxConfig`：`model_validator` 从 `os.environ`（经 `_load_dotenv_if_present`）合并扁平 env；`ConfigDict(populate_by_name=True)`
- `DatabaseConfig.use_mysql` 正确解析 `DATABASE_BACKEND`
- `AppSettings.use_mysql` 与顶层 `database_backend` 对齐
- `get_settings()` 首次加载前调用 `_load_dotenv_if_present()`
- 单测 `tests/unit/test_database_env_binding.py`

---

## 2026-06-16 (导航二级菜单无法展开)

### 根因与修复
- **根因** Bootstrap 4 在 `.dropdown-menu` 内 `stopPropagation()`；`onclick` 无效；**`common.css` 中 `.nav-search-wrapper .dropdown-item:not(.nav-search-match)` 默认 `display:none`，页面未搜索时二级项全部被隐藏**
- **修复** 搜索过滤仅在 `.nav-search-filtering` 时生效；`base_app.js` 同步切换该类；capture 阶段折叠/展开；`versioned_url` 注册于 `bootstrap.py`

---

## 2026-06-16 (CSP 导致全站样式被浏览器拦截)

### 界面仍混乱根因
- **根因** `security_headers.py` 的 `style-src` 含 `'nonce-…'` 时，CSP3 浏览器会拦截：① 78 个无 nonce 的 `<style>` 块；② 86 个模板内 991 处 `style=""` 属性 → 页面布局/配色大量失效（与 CSS 文件内容无关）
- **修复** `style-src` 改为 `'self' 'unsafe-inline'`（不再对 style 使用 nonce）；内联 `<script>` 批量补 `nonce="{{ csp_nonce() }}"`（99 个模板，`scripts/patch_csp_script_nonces.py`）
- **单测** `tests/bootstrap/test_security_headers.py` 新增 `test_style_src_allows_inline_styles`

---

## 2026-06-16 (CSS 加载顺序修复 + Codex hooks 解绑)

### 界面混乱根因与修复
- **根因** `design-tokens.css` 在 `common.css` **之后**加载，用冲突的 token 值（圆角/涨跌色/`--surface` 等）部分覆盖原样式；且 tokens 文件缺少 `ui_macros.html` 依赖的 `.qa-card` / `.qa-badge` / `.qa-toast`
- **修复** `design-tokens.css` 作为唯一 token 源（与 `common.css` 原值对齐）；`common.css` 移除重复 `:root` / coherence 块
- **加载顺序** `base.html` / `strategy_wizard.html` / `data_lake_health.html`：bootstrap → **design-tokens** → common

### Codex 工具调用 `unsupported call`（修 hook 时误改全局配置）
- **用户观察** 修 Cursor shell hook **之前** Codex 正常，**之后** 全部 `unsupported call`（同期改动，非 Cursor hook 本身导致）
- **对比备份** `~/.codex/backups/codex-plus-live-1781594818969/`（hook 仍在、Codex 正常）：`model=gpt-5.3-codex`，`base_url=http://127.0.0.1:15721/v1`，`hooks.state` 信任 graphify
- **修 hook 后误改** 全局 `model=ep-20260616112244-98tvr`，`base_url=http://192.168.8.11:8080/v1` → 代理返回 `function_call.name=""` → `unsupported call`；部分线程还固定为 `@cf/deepseek-*`
- **保留** `.codex/hooks.json` 为空（graphify hook-check 每条 Bash ~72min，不恢复）；`.cursor/hooks.json` 仅拦 git commit/push
- **恢复** `~/.codex/config.toml` 模型/代理；`.codex/config.toml` 去掉 `hooks=false`；`scripts/install_codex_quant_atlas.ps1` 一键恢复

---

## 2026-06-16 (登录页样式 + B-4 Facade 入口 + CSP 修复)

### 登录页无样式修复
- **根因** `security_headers.py` CSP 中 `nonce-{value}` 未加单引号，浏览器不认可 nonce → 内联 `<style>` 被拦截
- **修复** 改为 `'nonce-{value}'` 标准格式；`login.html` 内联 `style=""` 改为 CSS 类（CSP 合规）
- **CSRF** `csrf_html()` 返回 `Markup`（修复注册页等表单字段被 Jinja 转义成可见文本）；登录页移除冗余 hidden 字段（`/login` 已 CSRF 豁免）
- **单测** `tests/bootstrap/test_security_headers.py`

### A-1 · 测试收集修复 + 第五批
- **修复** `app/agents/research/nodes/__init__.py` 错误相对导入（`app.core` / `app.tools` / 父级 `state`/`debate_bus` 等）
- **重命名** `test_runtime.py` → `test_quant_ai_runtime.py` / `test_trade_plan_runtime.py`（消除模块名冲突）
- **新增** `tests/facade/test_facade_dtos.py`、`tests/presentation/test_v2_backtest_async.py`

### B-3 · AIFacade 结构化 DTO
- **DTO** `AIAnalysisRequestDTO` / `AIAnalysisResultDTO`（conclusion/confidence/evidence/risk_flags/prompt_trace）
- **Facade** `observe_facade` 埋点；`sanitize_user_prompt` 保留；结果经 DTO 归一化并附带 `raw`
- **接线** `service_wiring` → `from app.application.facade import AIFacade`
- **v2** `POST /api/v2/backtest?async=1` 支持 `run_backtest_async`

### B-2 · BacktestFacade 结果 DTO 与异步回测
- **DTO** `BacktestResultDTO`（sharpe/max_drawdown/win_rate/equity_curve + 字段别名归一）
- **Facade** `observe_facade` 埋点；`run_backtest_async()` Celery 排队，无 worker 时同步降级
- **任务** `app/tasks/backtest_tasks.py`：`run_strategy_backtest` + `submit_strategy_backtest`
- **接线** `service_wiring` → `from app.application.facade import BacktestFacade`

### B-1 · MarketFacade DTO 与指标
- **DTO** `app/facade/dto/market_facade_dto.py`：`HistoryBarsQueryDTO`、`MarketQuotesQueryDTO`、`MarketPanoramaDTO`
- **校验** symbol/日期格式/日期区间；Pydantic 错误映射为 `ValidationError`
- **指标** `FACADE_CALL_DURATION` / `FACADE_ERRORS` + `observe_facade()` 上下文管理器
- **接线** `service_wiring` 改为 `from app.application.facade import MarketFacade`

### B-4 · Application Facade 统一入口
- **新增** `app/application/facade/__init__.py` 重导出 `MarketFacade` / `BacktestFacade` / `AIFacade`

---


### A-1 续 · 测试基线修复（登录 / 路由 / 覆盖率）
- **JsonUserRepository** 受保护演示账号密码在 `_read()` 中校准为固定凭据（`admin123` 等），消除跨测试污染
- **auth.login** 测试模式下跳过模块级 `_login_limiter`，避免全局限流导致登录 200
- **UserDecisionContextService** 路由在 `ctx.user_decision_context_service` 为类时回退实例化
- **AttributionCompareService** `list_quotes` 按 `code` 匹配标的，修复 peer 名称错误
- **v1/stock/routes_*.py** 修复拆分后缩进错误；`route_loader` 预加载 `v1/**/routes_*.py`；`stock_route_helpers` 在 DI 注入类时自动实例化
- **coverage** `pyproject.toml` 移除 `app/modules/**` omit，纳入模块覆盖率统计

### A-2 · execution / portfolio_risk 异常收窄
- **portfolio_risk**：`fund_tier_service.py`、`portfolio_service.py`、`portfolio_trade_service.py`、`portfolio_market_service.py`、`module.py` — `except Exception` 改为 `SQLAlchemyError`、`_MARKET_FETCH_ERRORS`、`OSError`/`json.JSONDecodeError` 等具体类型
- **execution**：`pre_trade_preflight_service.py`、`trade_execution_pipeline_service.py`、`trade_outcome_review_service.py` — 合规预检、ATR 拉取、合规日志、复盘持久化等路径收窄异常类型
- **行为**：边界层仍记录日志并降级；不再吞掉 `KeyboardInterrupt`/`SystemExit` 等

---

## 2026-06-16 (Gemini 审计重构 — 阶段 D OAuth 路由)

### D · OAuth 登录接入
- **路由** `GET /auth/oauth/start`、`GET /auth/oauth/callback`（state 校验 + Keycloak code 交换）
- **用户** `JsonUserRepository.link_or_create_oauth_user` + `UserApplicationService.provision_oauth_user`
- **工具** `extract_subject_from_token_response()` 从 introspect 提取 `sub`/email
- **注入** `presentation.py` → `create_auth_blueprint(oauth_provider=...)`
- **UI** `login.html` 在配置 Keycloak 时显示「Keycloak 登录」
- **单测** `test_oauth_user_repository.py`、`test_auth_oauth_routes.py`

### D · API JWT 鉴权
- **服务** `jwt_token_service.py`（HS256，`API_JWT_SECRET` / `API_JWT_TTL_SECONDS`）
- **守卫** `auth_guard.api_auth_required`：Session 或 `Authorization: Bearer` 二选一
- **路由** `POST /api/v2/auth/token`、`GET /api/v2/auth/me`
- **v2 模块** `market/strategy/ai/data/user/trading` 改用 `@api_auth_required`
- **LoginManager** `request_loader` 支持 Bearer JWT
- **单测** `test_jwt_token_service.py`、`test_v2_jwt_auth.py`

---

### A-4 · 关键服务补测
- **新增** `tests/modules/data/test_sync_service.py`：`TdxDaykSyncService` 扫描/规范化/`SyncResult`
- **新增** `tests/modules/portfolio/test_portfolio_service.py`：快照/再平衡/优化/记忆降级
- **新增** `tests/modules/execution/test_trade_pipeline.py`：`TradeExecutionPipelineService` 合规→预检→执行

---

### 根因
- `.claude/settings.local.json` 的 `PreToolUse` + `matcher: Bash` 对**每条** Shell 命令都跑 `validate-commit.sh` / `validate-push.sh`
- 脚本只 `exit 0/2`，**未向 stdout 输出 Cursor 要求的 JSON** → `returned invalid JSON` → Agent Shell 全部被拦

### 修复
- **移除** `settings.local.json` 中全局 `PreToolUse` Bash 钩子（quant 项目不需要每条命令都校验 commit）
- **清空** `.claude/settings.json` 内联 graphify PreToolUse（规则已在 `.cursor/rules/graphify.mdc`）
- **新增** `_cursor_hook_json.sh` + 更新 `validate-commit.sh` / `validate-push.sh` 始终输出 `{"permission":"allow|deny"}`
- **新增** `.cursor/hooks.json`：仅 `beforeShellExecution` + `git commit|git push` 匹配时校验
- **附带** 修复 `test_rate_limiter` / `test_market_facade` 两个失败用例

### 启动警告修复（同日）
- **修复** `routes_v2.py`：`ApiV2Context(...)` 重复传入 `market_facade` → v2 蓝图注册失败

---

## 2026-06-16 (Phase 2: UI/UX Improvements — Tasks #9, #10, #11)

### P9: 导航精简 — 5 个下拉菜单 → 6 个分类 + 分组折叠
- **`app/presentation/web/templates/base.html`** — 导航重构：
  - 拆分 "因子" 下拉菜单：因子工具（4 项）和用户工作台（7 项）分离为独立下拉
  - "AI 投研" → "AI"（缩短名称）
  - 新增 "👤 工作台" 下拉（5 个用户层级 + 禅意终端 + 3D 共鸣场）
  - AI 和系统下拉添加可折叠子分组（智能分析/策略工具/研究工作流；平台管理/协作）
  - 新增 `nav_workbench` Jinja 变量
- **`static/css/common.css`** — 新增 `.nav-group-header` / `.nav-group-body` 折叠样式 + 箭头动画
- **`static/js/base_app.js`** — 新增 `toggleNavGroup` 交互逻辑 + 搜索时自动展开分组 + 当前激活分组自动展开

### P10: CDN 自托管 — 移除 jsdelivr 外部依赖
- **`static/js/vendor/echarts.min.js`** — **新建** (1 MB) ECharts 5.3.2
- **`static/js/vendor/alpine.cdn.min.js`** — **新建** (44 KB) Alpine.js 3.14.8
- **`static/js/vendor/three.min.js`** — **新建** (670 KB) Three.js 0.160.0 UMD
- **`static/js/vendor/three.module.js`** — **新建** (1.27 MB) Three.js 0.160.0 ESM
- **`static/js/vendor/OrbitControls.min.js`** — **新建** (26 KB) OrbitControls r128
- **`static/js/vendor/mermaid.min.js`** — **新建** (3.3 MB) Mermaid 10
- **`static/css/vendor/xyflow.css`** — **新建** (17 KB) XFlow React CSS
- 以下模板从 CDN 改为自托管路径：
  - `ai_research_report.html`, `backtest.html`, `attribution_dashboard.html`, `quant_lab.html`, `strategy_compare.html` — ECharts
  - `decision_replay_space.html`, `stock_detail.html` — Alpine.js
  - `portfolio_resonance.html` — Three.js + OrbitControls
  - `research_pipeline.html` — Mermaid
  - `research_canvas.html` — Socket.IO (冗余 CDN 引用移除)
  - `swarm_designer_flow.html` — XFlow CSS
- Three.js ES Module importmap 保留 jsdelivr（依赖树过深，自托管 impractical）

### P11: 统一 API 错误处理
- **`static/js/api_client.js`** — 增强 `QCApi`：HTTP 错误自动调用 `window.showToast(msg, 'error')`，含 2 秒冷却防刷屏
- **`static/js/base_app.js`** — 新增 `window.qcLogError(msg, err)` 全局函数：同时展示 toast + 记录 console.error
- **`static/js/components/AiResearchReport.js`** — 新增 `notify()` 辅助函数；15 处 `alert()` 替换为 `notify()`（成功/警告/错误类型区分）
- 27 个模板文件共 46 处 `console.error()` 替换为 `window.qcLogError()`

---

### D · OAuth Port（可选 Keycloak）
- **新增** `app/domain/ports/oauth_port.py`：`OAuthProviderPort` 协议
- **新增** `app/infrastructure/auth/oauth_provider.py`：`KeycloakOAuthProvider` + `NullOAuthProvider` + `build_oauth_provider()`
- **注册** `oauth_provider` factory（`wiring_system.py`）；未配置 env 时自动降级为 Null，不破坏 Flask-Login
- **单测** `tests/infrastructure/test_oauth_provider.py`

---

## 2026-06-16 (Gemini 审计重构 — 阶段 B-3 + A + C)

### B-3 · 扩展 Facade 路由
- **MarketFacade** 新增 `get_history_bars()`（`get_history` 回退 + count 截断）
- **BacktestFacade** 新增 `select_stocks()`（`SelectionRequestDTO` 校验）
- **接入** v2：`GET /stocks/<symbol>/history`、`GET /markets/history/<market>/<symbol>`、`GET /strategies/select`
- **修复** `MarketApplicationService.get_history_bars()` 别名（修复 v2 回退路径预存 bug）

### A · 测试补全（批次）
- **新增** `tests/modules/market_data/test_market_service_core.py`（panorama/history）
- **新增** `tests/modules/strategy/test_backtest_service_core.py`（`StrategyApplicationService.backtest`）
- **新增** `tests/core/test_rate_limiter.py`（TokenBucket / RateLimiter）
- **扩展** facade 单测：history bars、select stocks、dataclass 字段顺序
- **扩展** `test_auth_service.py`：PBKDF2 实哈希校验

### C · 兼容层清理
- **删除** `app/services/archetypes/cluster_manager.py`、`app/services/visualization/user_dna_service.py`（逻辑已在 `app/modules/ai_agent/services/`）

---

## 2026-06-16 (Gemini 审计重构 — 阶段 B-2 + E-2)

### B-2 · BacktestFacade / AIFacade
- **充实** `app/facade/backtest_facade.py`：Pydantic `BacktestRequestDTO` 校验 + 委托 `strategy_service.backtest()`
- **充实** `app/facade/ai_facade.py`：`sanitize_user_prompt()` 防注入 + 委托 `ai_analysis_service.analyze()`
- **抽取** `app/facade/_helpers.py`：`parse_market()` 供 Market/AIFacade 共用
- **注册** `backtest_facade` / `ai_facade` factory（`service_wiring.py`）
- **接入** v2 路由：`POST /api/v2/strategies/backtest`、`POST /api/v2/analysis/ai`（含 deep 回退）
- **修复** `ApiV2Context` / `routes_v2` 注入 `backtest_facade`、`ai_facade`
- **新增** `tests/facade/test_backtest_facade.py`、`tests/facade/test_ai_facade.py`

### E-2 · 因子投票审计持久化
- **扩展** `AlphaGovernanceDAO`：投票写入 `instance/alpha_vote_history.jsonl`，启动时加载
- **新增** `list_vote_history(proposal_id)` API
- **新增** `tests/core/test_alpha_governance_vote_history.py`

---

## 2026-06-16 (Redis URL 配置修复)

### 根因
- `app/core/runtime_config.get_runtime()` 在 `_ensure_loaded()` 加载 `.env` 后未重新读取 `os.environ`，导致 `REDIS_URL` 等变量返回空字符串。

### 修复
- **修复** `get_runtime()`：dotenv 加载后二次读取环境变量
- **新增** `resolved_redis_url()`：`REDIS_URL` → `TASK_MESSAGE_REDIS_URL` → `CELERY_BROKER_URL` 回退链
- **更新** `QuoteCache` 使用 `resolved_redis_url()`，空 URL 时明确降级日志
- **扩展** `AppSettings.redis_url` / `resolved_redis_url` + `_FIELD_CACHE["REDIS_URL"]`
- **配置** `.env`：`REDIS_URL=redis://192.168.8.103:6380/0`
- **新增** `tests/core/test_runtime_config_redis.py`

---

## 2026-06-16 (Gemini 审计重构 — 阶段 C + B 试点)

### 阶段 C · `app/services` 逻辑迁移
- **迁移** `ClusterManager` → `app/modules/ai_agent/services/archetypes/cluster_manager.py`
- **迁移** `UserDNAService` → `app/modules/ai_agent/services/visualization/user_dna_service.py`
- **更新** `jarvis_semantic_router_service` 及关联测试 import 路径
- **保留** `app/services/*` 为 1 行 re-export shim（向后兼容）

### 阶段 B · MarketFacade 试点
- **充实** `app/facade/market_facade.py`：`market_service` 注入、市场校验、`get_panorama()` 统一序列化
- **注册** `market_facade` factory（`service_wiring.py`）
- **接入** `GET /api/v2/markets/panorama/<market>` 优先走 Facade（`market_facade` 不可用时回退 `market_service`）
- **扩展** `ApiV2Context.market_facade`（置于可选字段区，修复 dataclass 字段顺序）+ `presentation.py` 注入
- **新增** `tests/facade/test_market_facade.py`

---

## 2026-06-16 (Phase 7: 领域逻辑修复 — 4 tasks)

### P7-1 · 统一事件总线
- **删除** `app/domain/events/event_bus.py`（旧简单 EventType 枚举）
- **重写** `app/domain/events/__init__.py` — 用 `_LegacyEventType` 兼容 shim 替代旧文件导入，`emit`/`on` 转发到 bridge
- **修复** `app/tasks/event_tasks.py` — 移除引用不存在的 EventType 值的死代码（`SIGNAL_TRIGGERED`/`TRADING_ORDER_PLACED` 等），改为字符串键映射
- **保留** `app/application/events/event_bus.py` 作为过渡层，通过 bridge 转发到 core/event_bus.py
- 14 个 core event bus 测试全部通过

### P7-2 · 填充交易工作流真实信号/风控/执行逻辑
- **重写** `app/application/workflows/trading_workflow.py`：
  - Step 1 `generate_signal`：通过 CapabilityRegistry fetch bars → 计算技术指标（MA5/MA20/MA60/RSI）→ `SignalGenerationService` 生成信号
  - Step 2 `risk_check`：`TradingPolicyService` 检查（持仓限制、单笔限额、市场时段、熔断器）；hold 信号跳过
  - Step 3 `execute_order`：尝试真实执行 → 失败回退到模拟；发射带 `provenance_id` 的 `TradeExecutedEvent`
- **新增** `tests/application/test_trading_workflow.py`：14 个用例覆盖信号生成/风控/执行全链路

### P7-3 · ai_research_service 动态工具发现
- **重写** `app/modules/ai_agent/services/ai_chat_service.py`：
  - 新增 `_resolve_tools()` 异步函数：从 CapabilityRegistry 动态发现工具
  - 优先使用 `get_agent_capabilities()` + `CapabilityRegistry.get().handler` 解析
  - 降级到硬编码默认工具列表（registry 为空或异常时）
- **新增** `tests/ai_agent/test_ai_chat_service_dynamic_tools.py`：4 个用例

### P7-4 · LLM 可观测性 — token/延迟采集
- **重写** `app/infrastructure/adapters/llm_universal_adapter.py`：
  - 新增 `_ObservabilityCallbacks`：包装 `ainvoke` 捕获延迟和 token
  - 新增 `_extract_usage()`：多策略提取 LangChain usage（usage_metadata / response_metadata / usage）
  - 新增 `_normalize_usage()`：统一转换为 `{prompt_tokens, completion_tokens, total_tokens}`
  - `_call_direct()` 返回 `ChatResponse(usage=...)` 而非空 dict
- **重写** `app/application/services/llm_fallback_service.py`：
  - 同上 observability 逻辑应用到 fallback router 的 `_call_single_provider`
  - 每个 provider 调用记录 `{provider, model, elapsed_ms, tokens}`
- **新增** `tests/core/test_llm_observability.py`：13 个用例

---

## 2026-06-16 (Stage C: Security Hardening — Gemini Audit Action)

### C-1: 硬编码密钥/HMAC fallback 修复
- **`app/bootstrap.py:63`** — Flask SECRET_KEY fallback `"dev-secret-key"` → `secrets.token_hex(32)` 动态生成
- **`app/modules/system/services/ui/decision_snapshot_service.py:40,93`** — HMAC share token fallback `"quant-atlas-share"` → 强制使用 `current_app.secret_key`（缺失时抛异常而非静默降级）
- **`app/modules/collaboration/services/cross_team_meta_learning_service.py:28`** — team fingerprint secret `"quant-atlas-cross-team"` → 读取 `settings.resolved_cross_team_secret`
- **`app/config/app_settings.py`** — 新增 `cross_team_secret` 字段 + `resolved_cross_team_secret` 属性（从 FLASK_SECRET_KEY 派生）

### C-3: API 路径 CSRF 保护
- **`app/presentation/csrf_protection.py`** — 重构 `/api/*` CSRF 策略：有活跃 Flask-Login session 的 API 请求需携带 `X-CSRF-Token`/`X-CSRFToken` 头；无 session 的公开 API 仍豁免
- **`static/js/base_app.js`** — 新增 `fetch` 包装器，对 `/api/*` 的 POST/PUT/DELETE/PATCH 自动注入 CSRF token
- **`app/presentation/web/templates/base.html`** — 新增 `<meta name="csrf-token">` + JS 初始化代码

### C-4: Secret 管理
- **`.env.example`** — 补充所有遗漏的 secret 字段：`CROSS_TEAM_SECRET`、`FMP_API_KEY`、`TAVILY_API_KEY`、`TUSHARE_TOKEN`、`LLM_API_KEY`、`THS_USERNAME/PASSWORD`、`RDAGENT_API_KEY`、`TASK_MESSAGE_REDIS_URL`、WeChat OAuth、Feature toggles

### C-5: 密码变更 API 死代码修复
- **`app/modules/user/services/user/user_service.py`** — 新增 `change_password()` 方法（支持 admin 绕过原密码验证、PBKDF2 哈希、8 字符最小长度）
- **`app/bootstrap_components/wiring_system.py`** — `_make_user_application_service` 注入 `auth_service`
- **`app/bootstrap_components/services_bootstrap.py`** — `init_user_services` 两处更新注入 `auth_service`

### 验证
```
python -m pytest tests/smoke/test_route_smoke_critical.py -q → 5 passed
grep -rn "quant-atlas-share\|quant-atlas-cross-team\|dev-secret-key" app/ → 0 hits
```

---

---

---

## 2026-06-15 (Gemini 审计校准 — 阶段十七 P17-1–P17-3)

### P17-1 · 巨型路由拆分（swarm_topology / alpha_marketplace / mesh）
- **`routes_v1_swarm_topology.py`**：211 行 → 20 行；`v1/swarm_topology/`（topology + adaptive，15 端点）。
- **`routes_v1_alpha_marketplace.py`**：229 行 → 18 行；`v1/alpha_marketplace/`（`_helpers` + trade / reputation，12 端点）。
- **`routes_v1_mesh.py`**：186 行 → 18 行；`v1/mesh/`（gateway + perception，12 端点）。

### P17-2 · 测试与 T-5 / 覆盖率评估
- **`tests/presentation/api/test_v1_dispatchers.py`** 扩展 phase 17 用例。
- T-5：`smoke_benchmark.py` 新增 `--in-process`（test_client，无需 live server）；见 `docs/perf_baseline.md`。
- 覆盖率 gate：**维持 60%**（`pyproject.toml` / CI）；待全仓 `pytest --cov=app` 实测 ≥65% 后再上调至 65%。

---

## 2026-06-15 (Gemini 审计校准 — 阶段十六 P16-1–P16-2)

### P16-1 · 巨型路由拆分（ai_hedge_fund / attribution / decision_provenance）
- **`routes_v1_ai_hedge_fund.py`**：133 行 → 22 行；`v1/ai_hedge_fund/`（`runtime` + analyze / query，4 端点，嵌套 `/ai-hedge-fund`）。
- **`routes_v1_attribution.py`**：161 行 → 24 行；`v1/attribution/`（`_helpers` + analyze / whatif，4 端点）；**修复** `register_attribution_routes` 内 `_attribution_ctx = ctx` 未写入模块全局导致 `compare` 永远拿不到 `market_service` 的 bug，改为 `AttributionRuntime` 闭包注入。
- **`routes_v1_decision_provenance.py`**：296 行 → 22 行；`v1/decision_provenance/`（sequence_chain / evidence_graph / decision_lifecycle，9 端点）。

### P16-2 · 测试与文档
- **`tests/presentation/api/test_v1_dispatchers.py`** 扩展 phase 16 用例。
- **`docs/重构.md`** §二点五进度表追加阶段十六。

---

## 2026-06-15 (Gemini 审计校准 — 阶段十五 P15-1–P15-2)

### P15-1 · 巨型路由拆分（strategy_synthesis / one_click / risk_companion）
- **`routes_v1_strategy_synthesis.py`**：192 行 → 24 行；`v1/strategy_synthesis/`（pipeline + evidence，4 端点）。
- **`routes_v1_one_click.py`**：149 行 → 24 行；`v1/one_click/`（action + evidence，3 端点）。
- **`routes_v1_risk_companion.py`**：133 行 → 24 行；`v1/risk_companion/`（detect + profile，3 端点）。
- 三域均移除无效的 `request._api_ctx`，改为注册时 `ctx` 闭包注入。

### P15-2 · 测试
- **`tests/presentation/api/test_v1_dispatchers.py`** 扩展 phase 15 用例。

---

## 2026-06-15 (Gemini 审计校准 — 阶段十四 P14-1–P14-4)

### P14-1 · 巨型路由拆分（provenance）
- **`routes_v1_provenance.py`**：191 行 → 22 行 dispatcher；保留 `blueprint`/`bp` 向后兼容别名。
- **`v1/provenance/`**：`models.py`、`fingerprint_routes`、`dashboard_routes`、`blueprint.py`（2 端点）。

### P14-2 · 巨型路由拆分（wisdom_mesh）
- **`routes_v1_wisdom_mesh.py`**：197 行 → 24 行 dispatcher。
- **`v1/wisdom_mesh/`**：`runtime.py`、`strategy_routes`、`leaderboard_routes`（5 端点）。
- 修复：路由改用注册时注入的 `ctx`，不再依赖无效的 `request._api_ctx`。

### P14-3 · 测试合并
- **`tests/presentation/api/test_v1_dispatchers.py`** 合并 phase8–14；删除 `test_phase*_dispatchers.py`。

### P14-4 · T-5 文档
- **`docs/重构.md`** 补充 smoke_benchmark 填表命令与阶段十四进度。

---

## 2026-06-15 (Gemini 审计校准 — 阶段十三 P13-1–P13-3)

### P13-1 · 巨型路由拆分（retail_assistant）
- **`routes_v1_retail_assistant.py`**：339 行 → 24 行 dispatcher；保留裸 `@register_routes`。
- **`v1/retail_assistant/`**：`runtime.py`、`hub_routes`、`insight_routes`、`psychology_routes`、`shadow_routes`（11 端点）。

### P13-2 · 巨型路由拆分（data_optimizer）
- **`routes_v1_data_optimizer.py`**：190 行 → 26 行 dispatcher；保留 `deps: DataOptimizerRouteDeps`。
- **`v1/data_optimizer/`**：`_helpers.py`、`scenario_routes`、`tdx_routes`、`write_routes`（6 端点）。

### P13-3 · 文档与测试
- **`tests/presentation/api/test_phase13_dispatchers.py`**
- **`docs/重构.md`** 追加巨型路由拆分进度表（阶段八–十三）

---

## 2026-06-15 (Gemini 审计校准 — 阶段十二 P12-1–P12-2)

### P12-1 · 巨型路由拆分（signal_flag + market_aux）
- **`routes_v1_signal_flag.py`**：266 行 → 22 行 dispatcher；保留裸 `@register_routes` 注册名 `register_signal_flag_routes`。
- **`v1/signal_flag/`**：`runtime.py`、`_helpers.py`、`query_routes`、`scan_routes`、`backfill_routes`（4 端点）。
- **`routes_v1_market_aux.py`**：210 行 → 24 行 dispatcher。
- **`v1/market_aux/`**：`runtime.py`、`feed_routes`、`pulse_routes`、`refresh_routes`（4 端点）。

### P12-2 · 测试
- **`tests/presentation/api/test_phase12_dispatchers.py`**

---

## 2026-06-15 (Gemini 审计校准 — 阶段十一 P11-1–P11-2)

### P11-1 · 巨型路由拆分（optimization）
- **`routes_v1_optimization.py`**：286 行 → 27 行 dispatcher；保留嵌套 `Blueprint(url_prefix="/optimization")`。
- **`v1/optimization/`**：`runtime.py`、`dual_path_routes`、`compliance_routes`、`budget_routes`、`evolution_routes`（共 18 端点）。

### P11-2 · 测试
- **`tests/presentation/api/test_phase11_optimization_dispatchers.py`**

---

## 2026-06-15 (Gemini 审计校准 — 阶段十 P10-1–P10-2)

### P10-1 · 巨型路由拆分（tdx_base）
- **`routes_v1_tdx_base.py`**：332 行（含异常空行）→ 30 行 dispatcher；统一 `app.*` 绝对导入。
- **`v1/tdx_base/`**：`runtime.py`（`TdxBaseRuntime.from_deps`）、`ingest_routes`、`block_routes`、`watchlist_routes`、`finance_routes`（共 9 端点）。
- ingest：`finance_max_symbols` 解析收窄为 `TypeError`/`ValueError`。

### P10-2 · 测试
- **`tests/presentation/api/test_phase10_tdx_base_dispatchers.py`**

---

## 2026-06-15 (Gemini 审计校准 — 阶段九 P9-1–P9-2)

### P9-1 · 巨型路由拆分（lifecycle）
- **`routes_v1_lifecycle.py`**：368 行 → 28 行 dispatcher；保留嵌套 `Blueprint(url_prefix="/lifecycle")` 注册方式。
- **`v1/lifecycle/`**：`runtime.py`（服务工厂）、`data_routes`、`research_routes`、`simulation_routes`、`execution_routes`、`monitoring_routes`（共 26 端点）。

### P9-2 · 测试
- **`tests/presentation/api/test_phase9_lifecycle_dispatchers.py`**

---

## 2026-06-15 (Gemini 审计校准 — 阶段八 P8-1–P8-3)

### P8-1 · 巨型路由拆分（hot_sectors）
- **`routes_v1_hot_sectors.py`**：340 行 → 30 行 dispatcher；去除异常空行格式。
- **`v1/hot_sectors/`**：`runtime.py`、`list_routes`、`ingest_routes`、`member_routes`；ingest 路径 `except Exception` 收窄。

### P8-2 · 巨型路由拆分（task_ops）
- **`routes_v1_task_ops.py`**：365 行 → 22 行 dispatcher。
- **`v1/task_ops/`**：`celery_routes`（监控/流式/SSE）、`sync_routes`（OHLCV 同步）、`batch_routes`（元学习/心理/IC 巡检）。

### P8-3 · 测试
- **`tests/presentation/api/test_phase8_dispatchers.py`**

---

## 2026-06-15 (Gemini 审计校准 — 阶段七 P7-1–P7-4)

### P7-1 · 巨型路由拆分（portfolio_users）
- **`routes_v1_portfolio_users.py`**：531 行 → 30 行 dispatcher。
- **`v1/portfolio_users/`**：`runtime.py`、`watchlist_routes`、`stock_group_routes`、`user_routes`；`group_stocks` 等路径 `except Exception` 收窄。

### P7-2 · factor 路由拆分
- **`routes_v1_factor.py`**：188 行 → 18 行 dispatcher。
- **`v1/factor/`**：`_helpers.py`、`ortho_routes`、`self_correction_routes`。

### P7-3 · 部署与压测样例
- **`docker-compose.yml`**：`ENABLE_ASYNC_MARKET_QUOTES` 环境变量（默认 `0`）。
- **`docs/sidecar.md`**：异步行情开关说明。
- **`instance/perf/smoke_benchmark.example.json`**：基线 JSON 样例。

### P7-4 · 测试
- `tests/presentation/api/v1/portfolio_users/test_runtime.py`
- `tests/presentation/api/test_portfolio_users_dispatcher.py`
- `tests/presentation/api/v1/factor/test_helpers.py`

---

## 2026-06-15 (Gemini 审计校准 — 阶段六 P6-1–P6-4)

### P6-1 · 巨型路由拆分（trade_plan）
- **`routes_v1_trade_plan.py`**：363 行 → 24 行 dispatcher。
- **`v1/trade_plan/`**：`runtime.py`、`plan_routes`、`review_routes`、`decision_routes`；修正 decision 路由 `app.modules` 导入。

### P6-2 · T-5 可选异步行情（env 门控）
- **`quote_fetch_policy.py`**：`ENABLE_ASYNC_MARKET_QUOTES` 开关。
- **`market_service._fetch_fresh_quotes_dict`**：缺失 CN 行情时可选 `get_quotes_async` + `run_async`，否则走同步 `get_quotes`。

### P6-3 · 覆盖率 gate
- CI + `pyproject.toml`：`fail_under` → **60**。

### P6-4 · 测试
- `tests/modules/market_data/test_quote_fetch_policy.py`
- `tests/modules/market_data/test_market_service_fetch.py`
- `tests/presentation/api/v1/trade_plan/test_runtime.py`
- `tests/presentation/api/test_trade_plan_dispatcher.py`

---

## 2026-06-15 (Gemini 审计校准 — 阶段五 P5-1–P5-3)

### P5-1 · 巨型路由拆分（quant_ai）
- **`routes_v1_quant_ai.py`**：541 行 → 35 行 dispatcher。
- **`v1/quant_ai/`**：`runtime.py`（`QuantAiRuntime` 共享依赖）、`strategy_routes`、`prediction_routes`、`selection_routes`、`analysis_routes`、`llm_routes`。

### P5-2 · T-5 压测基线工具链
- **`scripts/perf/update_baseline_doc.py`**：读取 `smoke_benchmark.json` 自动更新 `docs/perf_baseline.md` 结果表。
- **`docs/perf_baseline.md`**：补充 update 脚本说明。

### P5-3 · 测试
- **`tests/presentation/api/v1/quant_ai/test_runtime.py`**
- **`tests/presentation/api/test_quant_ai_dispatcher.py`**
- **`tests/perf/test_update_baseline_doc.py`**

---

## 2026-06-15 (Gemini 审计校准 — 阶段四 P4-1–P4-3)

### P4-1 · 巨型路由拆分（portfolio）
- **`routes_v1_portfolio.py`**：542 行 → 28 行 dispatcher。
- **`v1/portfolio/`**：`core_routes`（snapshot/optimize/rebalance/attribution/risk-budget）、`detail_routes`（detail/import）、`trade_routes`（trades/holdings/performance）；共享 `_helpers.py`。
- **`trade_routes.py`**：`except Exception` 收窄为具体异常类型（T-6 延续）。

### P4-2 · 覆盖率 gate
- CI + `pyproject.toml`：`fail_under` 50 → **55**。
- **`tests/presentation/api/v1/portfolio/test_helpers.py`**、**`test_portfolio_dispatcher.py`**。

### P4-3 · 文档
- **`docs/api_routing_convention.md`**：补充 portfolio 子包说明。

---

## 2026-06-15 (Gemini 审计校准 — 阶段三续 P3-6–P3-8)

### P3-6 · wiring_trading DI 收尾
- **`wiring_trading.py`**：9 处 `lambda _: __import__(...)` 迁移为 `zero_arg_service`；`_make_selection_source_service` 改用 `reg.get_or_none()`，移除宽泛 `except Exception`。

### P3-7 · 压测 smoke 脚本
- **`scripts/perf/smoke_benchmark.py`**：stdlib HTTP 探针，输出 `instance/perf/smoke_benchmark.json`；含 P99/错误率决策字段。
- **`docs/perf_baseline.md`**：补充「方式 A smoke」说明。
- **`tests/perf/test_smoke_benchmark.py`**。

### P3-8 · 测试补强
- **`tests/bootstrap/test_factory_helpers.py`**：`zero_arg_service` 冒烟。
- **`tests/core/test_application_event_forwarded.py`**：事件 envelope 往返。

---

## 2026-06-15 (Gemini 审计校准 — 阶段三 P3-1–P3-5)

### P3-1 · 性能基线
- **`scripts/perf/locustfile.py`**：health / market quotes / qlib / data-lake 压测任务。
- **`docs/perf_baseline.md`**：执行说明与 P99 决策门槛。

### P3-2 · VectorBT 并行对比
- **`vectorbt_adapter.py`**：可选 vectorbt buy-hold，不替换 `FastBacktestEngine`。
- **`strategy_wizard_service.preview_strategy`**：附加 `backend_compare` 字段。
- **`requirements-compute.txt`**：可选 `vectorbt`。
- **`tests/modules/strategy/test_vectorbt_adapter.py`**。

### P3-3 · FastAPI 行情侧车
- **`sidecar/market/`**：`/health`、`/price/{symbol}`，httpx 代理 Flask。
- **`docs/sidecar.md`**；`docker-compose.yml` profile `sidecar`。

### P3-4 · 关键页 Design System
- **`strategy_wizard.html`**：引入 `design-tokens.css`，色板/圆角/响应式 metric grid。

### P3-5 · 覆盖率 gate
- CI + `pyproject.toml`：`fail_under` 40 → **50**。

---

## 2026-06-15 (Phase 2 — Claude 审计报告 Phase 2 实施)

Per `docs/claude审计报告.md`, Phase 2 items completed:

### P2-2: 拆分 routes_v1_user_tiers.py (959行 → 6个文件)
- **`app/presentation/api/routes_v1_user_tiers.py`**: 瘦身为 12 行 dispatcher（仅 import 子包触发 `@register_routes` 装饰器）
- **`app/presentation/api/v1/user_tiers/__init__.py`**: 子包初始化
- **`app/presentation/api/v1/user_tiers/retail.py`** (154行): Retail tier — NL→Strategy, Mentor, Copy Trade, Psychology
- **`app/presentation/api/v1/user_tiers/boutique.py`** (185行): Boutique tier — Backtest, Alt Data, Collab, Factor Mining
- **`app/presentation/api/v1/user_tiers/investment.py`** (130行): Investment tier — Optimization, Macro, Tax, Multi-Asset
- **`app/presentation/api/v1/user_tiers/fund.py`** (240行): Fund tier — Attribution, Compliance, Audit, Master-Slave, Trade Pipeline
- **`app/presentation/api/v1/user_tiers/institution.py`** (351行): Institution tier — Impact, Execution Algos, Federated, RBAC
- 各子模块使用 `@register_routes(name="retail"/"boutique"/...)` 独立注册，通过 `blueprint.register_blueprint(_bp, url_prefix="/user-tiers")` 挂载

### P2-3: base.html 内联 JS 提取
- **`static/js/base_app.js`**: **新建** — 332 行，涵盖主题切换、Toast、确认对话框、Jarvis 指令球、消息/预警轮询、移动端导航切换
- **`app/presentation/web/templates/base.html`**: 515行 → 297行；移除 ~210 行内联 JS，改为 `<script src="{{ url_for('static', filename='js/base_app.js') }}">`

### P2-4: 导航搜索功能
- **`app/presentation/web/templates/base.html`**: 5个导航下拉菜单各添加 `<input type="search" data-nav-search>`；所有链接添加 `data-nav-label` 属性
- **`static/css/common.css`**: 添加 `.nav-search-input` 样式 + 搜索结果过滤 CSS
- **`static/js/base_app.js`**: 导航搜索 JS（实时过滤 `data-nav-label`，无匹配时显示"无结果"提示）

### P2-5: Socket.IO CDN 自托管
- **`static/js/vendor/socket.io.min.js`**: **新建** (49,993 字节) — Socket.IO v4.7.5 UMD 版
- **`static/js/vendor/socket.io.esm.min.js`**: **新建** (40,315 字节) — ESM 版
- **`app/presentation/web/templates/base.html`**: 移除 `https://cdn.socket.io/...` 外部 CDN 引用，改为自托管路径

---

## 2026-06-15 (Gemini 审计校准 — 阶段二 R6–R11)

### R6 · 巨型路由拆分
- **`routes_v1_qlib_rd.py`**：711 行拆为 dispatcher + `v1/qlib_rd/{qlib_pipeline,rd_agent,alpha_factory}.py`。
- 注：`routes_v1_stock.py` 此前已拆分为 dispatcher。

### R7 · 前端 Design System 基线
- **`static/css/design-tokens.css`**：HSL tokens + `.qa-card` / `.qa-badge` / `.qa-toast`。
- **`templates/components/ui_macros.html`**：Jinja 宏（card、badge、empty state）。
- **`base.html`** / **`data_lake_health.html`**：引入 tokens；data lake 页 `lang="zh-CN"`。

### R8 · 错误处理统一
- **`error_handlers.py`**：新增 `APIException` → 标准 `{status, error, request_id}` 映射。
- **`api_errors.py`**：`register_error_handlers` 改为 deprecation shim，委托 `register_api_error_handlers`。

### R9 · 事件桥接语义
- **`ApplicationEventForwardedEvent`**：保留 app 层 event type + payload。
- **`bridge.py`**：`SCAN_COMPLETED` / `SIGNALS_*` 等不再全部降级为 `MarketDataUpdatedEvent`；`MARKET_REGIME_CHANGED` → 专用事件。
- **`tests/core/test_event_bridge.py`**：3 用例。

### R10 · Prompt 版本化 trace
- **`prompt_trace.py`**：`attach_prompt_trace` / `prompt_hash` / `resolve_prompt_version`。
- **`ollama_prompt_adapter.py`**：analyze/generate 输出含 `prompt_version` + `prompt_hash`。
- **`tests/modules/ai_agent/test_prompt_trace.py`**。

### R11 · Grafana 可观测性
- **`docs/grafana.md`** + **`deploy/prometheus/prometheus.yml`** + **`deploy/grafana/dashboards/quant-atlas-overview.json`**。
- **`docker-compose.yml`**：可选 `observability` profile（prometheus + grafana）。

---

## 2026-06-15 (Gemini 审计校准 — 阶段一 R1–R5)

依据 `docs/gemini审计报告.md` 合理性分析，落地阶段一「夯实基础」：

### R1 · 关键路径单测
- **`tests/domain/test_trade_outcome_review_service.py`**：11 用例覆盖 `TradeOutcomeReviewService`（录单、平仓 PnL、复盘卡片、持久化、singleton）。

### R2 · CI 覆盖率 gate
- **`.github/workflows/ci.yml`**：`--cov-fail-under=40`；修复 `REDIS_URL` 为 `redis://127.0.0.1:6379/0`（原硬编码内网地址）。
- **`pyproject.toml`**：`fail_under = 40`（与 CI 对齐；60 为下一阶段目标）。

### R3 · 依赖约定
- **`docs/dependencies.md`**：`requirements.txt` 为运行时权威源；`pyproject.toml` 增加 `[project]` 元数据。

### R4 · DI 收敛
- **`app/bootstrap_components/factory_helpers.py`**：`zero_arg_service()` 替代 `lambda _: __import__(...)`。
- **`wiring_system.py`**：19 处 `__import__` 工厂全部迁移。
- **`docs/di_conventions.md`**：DI 约定文档。

### R5 · API 路由规范
- **`docs/api_routing_convention.md`**：文件命名、前缀、v2 收敛计划。

---

## 2026-06-13 (P0 Infrastructure — Expert Evolution Guide Survival Line)

Per `docs/06_Expert_Evolution_Guide.md`, P0 priorities: RBAC → Audit Chain → Key Encryption → Compliance Pre-check.

### 1. RBAC 持久化与统一
- **`models/auth.py`**: 移除 `User.role` 字符串列，新增 `UserRoleAssignment` 表（user_id→role_id FK，scope）。`Role` 表新增 `permissions_json` 列。
- **`institution_tier_service.py`**: `RBACService` 从 JSONL 文件存储迁移为 SQLAlchemy ORM 操作；删除 dataclass `Role` 和 `UserRoleAssignment`；默认角色注册改为幂等 INSERT OR IGNORE。
- **`rbac_guard.py`**: 统一 `require_rbac` 装饰器，依赖 ORM-backed RBACService。
- **`TradeExecutionPipelineService`**: RBAC 校验兼容 session-less 降级。

### 2. 审计链 DB 持久化（保留 hash chain）
- **`models/audit.py`**: **新建** `AuditEvent` 表，含 `content_hash` + `chain_hash` 字段维持 tamper-evident 链。
- **`fund_tier_service.py`**: `AuditTrailService` 从 JSONL 迁移到 DB；保留 hash chain 生成和验证逻辑；`get_snapshots()` 改为 DB 查询。
- **`audit_query_service.py`**: **新建** 审计事件查询、分页、导出服务。

### 3. 密钥加密存储
- **`key_encryption.py`**: **新建** Fernet 加密层，从 `KEY_ENCRYPTION_KEY` 或 `FLASK_SECRET_KEY` 派生密钥，支持版本化 token 和密钥轮转。
- **`models/trading.py`**: `GatewayConfig.api_key_hash` → `api_key_encrypted`（Fernet token）。
- **`models/advanced.py`**: `OpenBBProviderConfig.api_key_hash` → `api_key_encrypted`。
- **`key_management_service.py`**: **新建** 密钥 CRUD 服务，安全地设置/读取/列出加密密钥。

### 4. 合规预检持久化 + 管线集成
- **`models/compliance.py`**: **新建** `ComplianceRule` + `ComplianceViolationLog` 表。
- **`fund_tier_service.py`**: `ComplianceGuardrailService` 从内存规则迁移到 DB 规则加载 + 缓存刷新。
- **`compliance_rule_service.py`**: **新建** 合规规则 CRUD 服务。
- **`compliance_query_service.py`**: **新建** 违规日志查询服务。
- **`trade_execution_pipeline_service.py`**: 合规检查强制集成（无静默失败）；违规自动写入 `ComplianceViolationLog`。

### 数据库迁移
- **`alembic/versions/p0_infrastructure.py`**: 新增 `audit_events`, `user_role_assignments`, `compliance_rules`, `compliance_violations` 表 + `roles.permissions_json` 列。
- **`alembic/versions/encrypt_api_keys.py`**: `api_key_hash` → `api_key_encrypted` 列重命名。

### 测试
- **`tests/unit/test_p0_infrastructure.py`**: 17 个单元测试（密钥加密、合规规则、合规守卫、审计链、管线结果）。
- **`tests/integration/test_p0_infrastructure.py`**: 4 个集成测试（完整管线、合规拦截、审计链 DB 验证、密钥管理）。


## 2026-06-14 (Phase VIII：路由卫生 / 联邦集群定时扫描)

### 交付
- **路由卫生**: 移除 `decision_provenance` 末尾 dummy Blueprint 挂载。
- **Blueprint 前缀**: `tokenized_alpha` / `provenance` 去掉重复 `/api/v1`；`blueprint = bp` 向后兼容别名。
- **Boot 去重**: 删除 bootstrap 对 Tokenized/Provenance 的二次 `register_blueprint`（已由 `@register_routes` 自动发现）。
- **集群扫描**: `scan_cluster_health()` + Celery `federated.cluster_health_scan`（`FEDERATED_CLUSTER_BEAT`）。
- **测试/CI**: `test_phase69_route_boot.py`；CI 冒烟加入 Phase 69。

## 2026-06-14 (Phase VII & Final Polish)

### Phase VII 收尾：多实例路由注册 + 冒烟测试隔离
- **嵌套 Blueprint 前缀**: `optimization` / `user_tiers` / `lifecycle` / `phase18` 子 Blueprint 去掉重复的 `/api/v1`，修正双重前缀 404。
- **路由注册**: 每次 `create_api_blueprint()` 重置 `_registered_routes`；`ai_hedge_fund` 子 Blueprint 改为函数内创建。
- **冒烟登录**: 测试 fixture 写入隔离 `users.json` (admin123)，不依赖仓库 `config/users.json` 密码。
- **CI**: 单条 pytest 命令跑 Phase 66–68 + smoke。

### Phase VII：联邦心跳 / FedAvg 闭环 / CI 冒烟
- **节点心跳**: `heartbeat()`、`list_nodes()` 含 stale 标记；注册 upsert。
- **FedAvg 轮次**: `run_fedavg_round()` + 持久化 aggregated model；eligible 更新过滤。
- **集群状态**: `get_cluster_status()`；API status/heartbeat/round/model。
- **专业工作台**: 联邦 Tab：心跳、提交更新、FedAvg、集群状态。
- **可选依赖**: `requirements-compute.txt` (Polars)。
- **CI**: GitHub Actions 冒烟：Phase 66–68 + 关键 API。
- **测试**: `test_phase68_federated.py`, `test_route_smoke_critical.py`。
- **新 API**: `GET /institution/federated/status`；`POST /institution/federated/nodes/<id>/heartbeat`；`POST /institution/federated/aggregate/<model>/round`；`GET /institution/federated/models/<model>`。

### Phase VI：复杂度治理 / 向量化计算 / ZK 披露增强
- **Wiring 冒烟**: `validate_wiring(registry)` 解析工厂；启动日志输出 resolved 数。
- **路由冒烟测试**: 启动 ≥500 路由 + 关键 factory 可解析。
- **向量化回测**: NumPy/Polars 双后端；`backend` 参数；结果含 `backend` 字段。
- **ZK 证明修复**: `verification_nonce` 持久化；`verify_stored_proof`；`public_dict()`。
- **上架自动证明**: `list_token` 创建 ZK proof；listing 含 `zk_proof_hash`。
- **Marketplace UI**: 分级披露弹窗 + ZK 验证按钮。
- **API**: `POST /compliance/zk-proof/verify`；`POST /alpha/marketplace/proof/verify`。

### Phase V：用户频谱闭环 — 审计哈希链 / Hub UI / 因子挖掘
- **审计哈希链**: `DecisionSnapshot` 增加 `content_hash` / `chain_hash`；订单级与全链验证。
- **审计 API**: `GET /fund/audit/<order_id>/verify`；`GET /fund/audit/chain/verify`。
- **精品店挖掘**: `POST /boutique/factor-mining/run` 桥接遗传因子挖掘。
- **用户频谱 Hub**: 五层 Tab SPA + 快捷链接。
- **测试**: 哈希链完整性 / 篡改检测 / Tick 状态 / 因子挖掘。

### Phase IV：接口层 / 部署层 — Tick 推送 / Docker·K8s / 预检 UI
- **Tick 推送**: `subscribe_ticks` / `tick_update` 事件；Tick 广播线程 + EventBus 桥接。
- **Realtime API**: `GET /realtime/status`、`GET /realtime/ticks/status`。
- **预检 UI**: 个股页 POST `/trading/preflight` (ATR/合规)；专业工作台「预检→流水线」。
- **私有化部署**: Docker Compose (web + worker + redis)；K8s Deployment + Redis。
- **配置**: `ENABLE_TICK_WS`、`WS_TICK_INTERVAL_SEC`。

### Phase III：机构壁垒期 — 执行算法 / RBAC / 联邦部署 / 专业工作台
- **执行算法**: VWAP / TWAP / Iceberg / POV 统一切片调度。
- **RBAC**: 角色持久化 + `require_rbac` 装饰器 + 流水线权限校验。
- **联邦部署**: 节点注册、部署配置、FedAvg 聚合。
- **专业工作台**: 6 Tab SPA：组合优化/归因/合规/执行/流水线/联邦。
- **服务工厂**: `rbac_service`, `execution_algo_service`, `federated_deployment_service`, `market_impact_model_service`。

### Phase II/III：专业与信任期 + 机构执行链路
- **交易流水线**: `TradeExecutionPipelineService` (Compliance $\rightarrow$ PreTrade $\rightarrow$ Impact $\rightarrow$ Audit)。
- **Fast Path 扩展**: 新增 `compliance_guardrail_check`、`trade_pipeline_execute`。
- **Phase II 投资**: Black-Litterman 组合优化 API。
- **Phase II 基金**: `POST /fund/trade/pipeline`、`GET /fund/audit/<order_id>`；主从账户镜像。
- **预检增强**: `PreTradePreflightService` 集成 `ComplianceGuardrailService`。

### 可行性审核 + 全用户频谱重构
- **合规隔离**: Alpha Marketplace 去金融化；声誉积分替代 Wallet 货币；分级披露 API。
- **双路径分离**: Bootstrap 注册 Fast Path (Execution/Risk) 与 Slow Path (Cognitive/AI)。
- **复杂度治理**: 注册 `compliance_service` / `complexity_budget_service` / `anti_decay_evolution_service` 工厂；启动时 wiring 校验。
- **Alpha 抗衰减**: 上架时计算 `diversity_bonus`；奖励低相关性因子。
- **Phase I 散户**: NL $\rightarrow$ Strategy 自动附加向量化回测预览。
- **Phase I 镜像交易**: Copy-Trading 信号经 DualPathRouter Fast Path 分发。

---

## 2026-06-08 (Phase 2 & 4 Sprints)

### Phase 4 Sprint 0：去中心化启动 + DecisionFeedback + SSE 推理流
- **Registry**: `topological_service_order()`；`wire_to` 按依赖拓扑注入。
- **`initialize_all_modules`**: 传入 `session_factory`；优先调用模块 `initialize()`。
- **Collaboration**: `wire_module` 自主装配；`services.py` 不再单独 wire collaboration。
- **主动智能**: `health_aware.py` Jarvis 降级提示；`DecisionFeedback` 实体 + `POST /api/v1/decision/feedback`。
- **SSE**: `AiAnalysisService.analyze_stream()` + `GET /api/v1/ai/analyze/stream`。

### Phase 2 Sprint 12：register_factory 复杂服务 + infra 重绑 + legacy modules 下线
- **`register_factory`**: `data_infrastructure_service`、`factor_*`、`research_report_rag_service` 等。
- **`rewire_infra_dependent_services()`**: `bind_application_infrastructure` 后重绑 gpcw/memory/task_pipeline/rdagent。
- **删除 wire**: `wire_gpcw_service` 等 inline wire 移除。
- **`core/modules.py`**: 瘦身为 `context_module_manifest()` 兼容 shim。
- **`GET /api/v1/system/microkernel`**: 仅返回 v2 `modules`。

### Phase 2 Sprint 11：Registry name 收尾 + EvidenceGraph + ContextModule manifest
- **`evidence_graph_service` / `user_access_policy_service`**: 修正 `name=`；删除 `wire_optional` 内联 wire。
- **`context_module_manifest()`**: `GET /api/v1/system/microkernel` 返回 `context_modules` (v2) + `legacy_modules` (v1)。

### Phase 2 Sprint 10：_uid 全量迁移 + rdagent Registry + TDX 熔断
- **`rdagent_run_service`**: 修正 `name`；删除 `wire_rdagent_run_service` 改由 registry `wire_to` 注入。
- **`legacy_tdx_adapter.py`**: `tdx_legacy` 熔断机制；OPEN 时返回 `None`。
- **路由 `_uid()` 迁移**: `legacy_routes`、`simulation` 等 12 个文件完成迁移。

### Phase 2 Sprint 9：Registry 服务 preload + Tencent 熔断 + _uid 路由迁移
- **`preload_route_modules()`**: 在 `discover_routes()` 前扫描 `routes_v1_*`，使装饰器先生效。
- **`memory_optimization_service`** 等: 修正 `name=`；删除 inline wire，改为 `wire_to`。
- **`tencent_quote_gateway.py`**: 引入熔断，OPEN 时降级为空。
- **路由 `_uid()` 迁移**: `quant_ai`、`tdx_base`、`trade_plan` 等完成迁移。

### Phase 2 Sprint 0–1：单轨引导 + 拆除 Service Locator
- **单轨 DI**: `routes_v1_ai_hedge_fund` 等改为 `ctx` 或 `app.extensions` 注入，移除 `Container()` 直调。
- **Service Locator**: 移除 11 处 `@service` 装饰器；`bootstrap` 停止调用 `register_services()`。
- **`service_wiring.py`**: 新增显式装配逻辑。

### Phase 2 Sprint 2–3：AI DecisionContext + OpenBB 熔断
- **`AiAnalysisService.analyze()`**: 返回 `DecisionContextDTO`，包含 `decision_id`。
- **`openbb_adapter.py`**: 为 `get_realtime_quotes` 等添加 `@circuit_breaker`。

### Phase 2 Sprint 4：模块驱动 wire + DecisionTrace + ContextVar
- **`wire_context_modules()`**: 按 `discover_modules(config)` 调用各模块 `wire()`。
- **`DecisionTraceService`**: 记录决策链路 $\rightarrow$ `GET /api/v1/decision/trace/<decision_id>`。
- **`request_context`**: 注入 `request_id` / `user_id` ContextVar。

### Phase 2 Sprint 5：Risk 收敛 + Redis Trace + ContextVar 路由迁移
- **`TradingRiskFacade`**: 统一 `check_order` / Kelly / vol-target。
- **`DecisionTraceService`**: 引入 Redis 持久化 (TTL 7d)。
- **`app/modules/portfolio_risk/`**: 正式成为物理 ContextModule。

### Phase 2 Sprint 6：portfolio_risk 拆分 + Ollama 熔断 + 投委会 DecisionContext
- **`PortfolioContextModule`**: 仅保留 watchlist/signal_flag；其余迁至 `portfolio_risk`。
- **`OllamaPromptAdapter`**: 添加 `@circuit_breaker`。
- **`AICommitteeSelectionService`**: 结果写入 DecisionTrace。

### Phase 2 Sprint 7：Degraded 响应头 + Wiring 去重 + FinGPT 熔断
- **`degraded_context.py`**: 实现 `X-System-Degraded` 响应头注入。
- **Wiring**: 移除 legacy 中重复的 `wire_risk_alert_service` 等。

---

## 2026-06-07 & 2026-06-06 (V7-V9 & Data Sync)

### V9-V7 核心交付
- **V9 分布式智能集群**: `DistributedEventBus` + `MeshNodeRegistry` + `NATSMeshTransport`。
- **V8 无界执行**: `BorderlessExecutionRouter` + `RedisMarketExecutionDriver` (CN/US/HK/CRYPTO)。
- **V7 叙事智能与拓扑**: `NarrativeSynthesisService` (因果研报) + `SwarmTopologyService` (JSON 驱动拓扑)。
- **数据真值守卫**: `UnifiedDataTruth` $\rightarrow$ `DataTruthGuardianService` (拜占庭共识)。
- **决策剧场**: `DecisionTheaterService` (Three.js 3D 回溯)。

### 基础设施与同步
- **时序同步管道**: 实现 CH $\rightarrow$ Timescale $\rightarrow$ MySQL $\rightarrow$ qlib 的串行同步 pipeline。
- **QuestDB 适配**: PG 线协议 (8813) 优先，支持 `DEDUP` 与 `LOB` 读写。
- **TDX 检查点**: `tdx_sync_checkpoint` 增加增量落盘，防止进程中断后全量重跑。
- **一致性验证**: `run_full_data_consistency.py` 提供全链路对账。

---

## 2026-06-05 (V1-V4 & Infrastructure)

- **API 修复**: 修正诊股 `DiagnosisReportService` 400 错误，规范化 lday l-code。
- **数据湖**: 引入 `LegacyDataMigrationService` 自动化迁移 `.db` $\rightarrow$ MySQL。
- **基础数据同步**: 增加东财研报 API 抓取 (五类分类)，增强 AkShare 龙虎榜稳健性。
- **Redis 调整**: 统一 Celery / 消息中心到统一 Redis 节点。

---

## 2026-04-25 (Architecture Refactoring - HIGH Priority)

### TODO-004: Complete Dependency Injection in Application Services
- **问题**: Application services 使用 inline imports，违反依赖反转原则。
- **方案**: 引入 `IndustryProvider` 端口 $\rightarrow$ `CnIndustryProvider` 实现 $\rightarrow$ 构造函数注入。

### TODO-005: Split Fat MarketDataProvider Interface (ISP)
- **问题**: 单一接口包含 6 个数据方法，违反接口隔离原则 (ISP)。
- **方案**: 拆分为 `MarketOverviewPort`、`QuotePort`、`HistoryPort`、`ChipDataPort`。

### 职责重叠清理 (services/ vs application/services)
- **统一工具门面**: 新建 `ToolFacadeService` 封装 Market/Fundamental/News/Strategy 工具，消除冗余目录。
- **模块迁移**: `services/data/market_access.py` $\rightarrow$ `ToolFacadeService`。
- **领域分析**: 新建 `domain/analysis/` 存放纯分析逻辑 (e.g. `TechnicalTrendService`)。

### TODO-007: Fix Presentation $\rightarrow$ Infrastructure Violations
- **问题**: API 路由在模块级直接 import 基础设施模块。
- **方案**: 依赖项移至 `ApiV1Context` $\rightarrow$ 由 `bootstrap` 注入。

### TODO-008: Add Market Configuration Mapping
- **方案**: `domain/enums.py` 新增 `MARKET_BENCHMARKS` 与 `MARKET_CURRENCIES` 映射。

---

## 2026-04-24 (Service & Domain Decomposition)

- **Pydantic DTO 体系**: 建立 `app/application/dto/` 协议，消除 `dict[str, Any]` 传递。
- **职责拆解**: `EastmoneyParser` (解析) / `ManagerGenerator` (生成) 从上帝服务中剥离。
- **充血模型**: `Trade` 增加 `duration_minutes` / `is_profitable`；`StockQuote` 增加 `is_up` / `is_down`。
- **分布式任务切片**: `ScannerApplicationService` 分片处理 $\rightarrow$ `process_quote_batch_task`；信号旗扫描引入 Celery Chord 模式。

---

## 2026-04-23 (SQLAlchemy & Database Hardening)

- **SQLAlchemy 集成**: 建立 `Base` 基类 $\rightarrow$ 全量模型映射 $\rightarrow$ Alembic 迁移骨架。
- **连接池调优**: 引入 `pool_size=10, max_overflow=20`；修复 `StockCache` 连接泄露。
- **仓库范式重构**: 全站 MySQL 仓库迁移至 SQLAlchemy Session 模式。

---

## 2026-04-22 (Core Integration: Freqtrade, Hyperswitch, Kronos, OpenBB, QuantML)

- **Freqtrade**: 移植交易生命周期 (ROI/Stoploss) $\rightarrow$ `MySQLTradingRepository` $\rightarrow$ `BotEngine`。
- **Hyperswitch**: 支付编排引擎 $\rightarrow$ `PaymentGatewayPort` $\rightarrow$ `MySQLPaymentRepository`。
- **Kronos**: Transformer OHLCV 预测 $\rightarrow$ `kronos_predictions` 表 $\rightarrow$ 推理流水线。
- **OpenBB**: 全品种行情适配器 $\rightarrow$ 多源数据编排 $\rightarrow$ `openbb_data_cache`。
- **QuantML**: Factor Zoo 同步 $\rightarrow$ `quantml_factors` 表 $\rightarrow$ 结构化因子检索。
- **QuantML-Agent**: 智能洞察引擎 $\rightarrow$ 研报深度解读 $\rightarrow$ `agent_market_insights` 持久化。

---

## 2026-04-18 (Foundation: MySQL & Celery)

- **MySQL 迁移**: SQLite $\rightarrow$ MySQL 全量迁移；引入读写分离 (Master/Slave)。
- **Celery 化**: Scanner、数据回填等高 I/O 任务全面剥离至 Worker。
- **RD-Agent 闭环**: 本地模型支持 $\rightarrow$ 量化专用 Prompt $\rightarrow$ 挖掘-验证闭环。
- **Qlib 流水线**: MySQL $\rightarrow$ Qlib 二进制同步；补全全市场历史行情与基准指数。
- **规范化**: 确立 `{MARKET}:{CODE}` (e.g. `CN:000001`) 为全系统统一 UID。

---

## 2026-04-14 (MVP Features & UX)

- **信号旗回填**: `signal_flag_pool_backfill` 异步任务。
- **UX 优化**: 涨跌颜色中/美版切换、个股 K 线定位最新、朋友圈附件 MIME 补全。
- **投资经理模拟**: 模拟只读信号旗库 $\rightarrow$ `simulate_day` $\rightarrow$ 收益榜 $\rightarrow$ Celery 快跑。
- **朋友圈 (Moments)**: 基础信息流 $\rightarrow$ 收盘自动战报 $\rightarrow$ 互动（点赞/评论） $\rightarrow$ Agent 自动回复。
- **个股/研报 UI**: 研报中心分类 Tab $\rightarrow$ 投资经理人设与 SVG 头像 $\rightarrow$ 朋友圈时间统一东八区。

## 2026-06-16 — A-1 测试收集修复（第二批）

- **服务 shim**：补全 `app/application/services/` 扁平重导出（`factor_catalog_service`、`basic_market_data_service`、`scanner_service`、`watchlist_service`、`qlib_pipeline_service`、`model_predict_lab_service`、`prediction_service`、`selection_source_service`、`strategy_service`、`research_pipeline_snapshot`），修复迁移后测试仍引用旧路径导致的 `ModuleNotFoundError`。
- **运行时修复**：`quote_aggregator.py` 中 `core.runtime_config` → `app.core.runtime_config`；`cn_xueqiu_news.py` 的 `DEFAULT_UA` 改为从 `providers` 包导入。
- **quant_tools**：新增 `list_quant_tool_names()`，`quant_tools_agent_system_suffix()` 返回市场与工具名列表。
- **遗留测试**：新增 `tests/test_hold_to_end_strategy.py`、`tests/unit/conftest.py`（注入 `scripts/`）；移除/跳过破坏 pytest capture 的 `sys.stdout` 劫持与手工集成测试；重命名同名测试文件消除 import mismatch。
- **诊断脚本**：`scripts/check_test_imports.py` 可批量检测测试模块导入错误（344 文件，0 error）。

---
## 2026-06-16（继续）— API 契约/鉴权/错误提示/测试隔离一致性

### API 健康契约与 legacy 路由
- **`/api/v1/health`**：改为返回顶层 `{"status":"ok"}`（匹配 `tests/api/test_api_contract.py`）。
- **Phase-27 legacy alias**：在 `app/presentation/api/routes_v1_system_health.py` 补齐：
  - `/api/v1/system/events`
  - `/api/v1/system/test-event`
  - `/api/v1/market/sentiment/diary`
  - `/api/v1/ai-hedge-fund/analyze`

### Flask-Login & Werkzeug 测试兼容
- **`werkzeug.__version__` shim**：在 `app/bootstrap.py` 的 `create_app()` 内补齐 Werkzeug 3 测试兼容字段。
- **测试环境不再隐式认证**：`app/bootstrap_components/presentation.py` 移除 `request_loader` 的测试回退用户，避免匿名请求误被当作已登录。
- **API 路由 unauthorized 返回 401**：在 `create_app()` 中调用 `register_api_error_handlers()` + `setup_flask_login_errors()`，确保 `@login_required` 对 `/api/*` 返回 JSON 401。

### 错误提示（hints）一致性
- **ValidationError hints**：在 `app/presentation/api/error_handlers.py` 中统一对 `map_validation_error()` 与 `ApplicationError(ValidationError)` 处理链路调用 `enrich_error_payload()`，保证 `payload["error"]["hints"]` 可用。

### 前端脚本回归
- **全局错误横幅脚本**：`app/presentation/web/templates/base.html` 增加 `api_error_banner.js` script 引用，满足 Phase-47/48 UI 合约测试。

### 测试隔离（数据库路径 + demo 用户确定性）
- **SQLite 路径**：`app/config/database_settings.py` 将 `DatabaseConfig.sqlite_path` 改为 lazy default，读取被 monkeypatch 的 `app.config.settings.INSTANCE_DIR`。
- **SQLite demo 用户校准**：`app/infrastructure/repositories/sqlite/sqlite_repositories.py` 在已有数据库场景下也会校准 demo 用户密码哈希，保证 `admin/admin123` 登录在重复测试中稳定可用。

---

## 2026-06-16 — P0 安全与量化硬伤（R02–R08，跳过 R01）

### R02 Markdown XSS
- `ai_analysis.html` / `ai_investment_committee.html`：`marked.parse` → `renderMarkdownSafe()`（DOMPurify + `static/js/qa_markdown_safe.js`）。

### R03 选股脚本
- `scripts/stochastic_selector.py`：`non_stocks` → `non_st_stocks`（ST 过滤生效）。

### R04 回测成本
- `backtest_engine.py`：买卖应用 `slippage_bps`、佣金/印花税/过户费（`transfer_fee`）。

### R05 密码哈希
- `password_hash.py`：拒绝裸 SHA-256 hex 登录；须管理员重置或 PBKDF2 重灌。

### R06 SocketIO CORS
- `realtime.py`：`SOCKETIO_ALLOWED_ORIGINS` 含 `*` 时拒绝启动 SocketIO。

### R07 Legacy 鉴权
- `legacy_routes.py`：`/api/market/sentiment`、`/market/movements`、`/market-rankings` 加 `@login_required`。

### R08 SQL 表名校验
- 新增 `app/core/sql_safety.py`（`safe_sql_identifier` / `safe_table_name`）；`history_repository`、`timeseries_sync_status`、`ohlcv_*_reader` 统一引用。

### 测试
- `tests/core/test_sql_safety.py`；`test_password_hash` / `test_auth_service` 更新 legacy 行为断言。

---

## 2026-06-16 — P1 性能与安全加固（R09–R12、R15、R16）

### R09 ORM N+1
- `market` / `collaboration` / `auth` / `trading` / `moments` 模型：集合 `relationship` 加 `lazy="selectin"`。

### R10 Redis KEYS → SCAN
- `redis_client.py`：`scan_keys()`、`delete_keys_by_pattern()`；`global_cache` / `multi_level_cache` 前缀失效改 SCAN。

### R11 Celery Worker 回收
- `celery_app.py`：`worker_max_tasks_per_child`（默认 500，env `CELERY_WORKER_MAX_TASKS_PER_CHILD`）。

### R12 无界查询上限
- `query_limits.py`：自选股/分组/团队列表上限；`mysql_watchlist` / `async_mysql_watchlist` / `mysql_stockgroup` / `mysql_collaboration` 应用 `.limit()`。

### R15 模板 XSS
- `index.html` Jarvis 结果用 `escHtml`；`backtest.html` 交易/对决表格转义；`register.html` 去掉 `|safe`。

### R16 覆盖率门槛
- `pyproject.toml`：`fail_under` 30 → 50，与 CI 对齐。

### 测试
- `tests/infrastructure/test_redis_scan.py`

---

## 2026-06-16 — P1 第二批（R13/R14 切片 + CSP 收尾）

### R13 缓存统一入口
- 新增 `app/infrastructure/cache/cache_manager.py`（`CacheManager` / `get_cache_manager()`）：L1 `MemoryCache` + L2 `GlobalCache`。
- 新增 `app/infrastructure/cache/__init__.py` 作为对外统一 import 路径。
- `application/performance.py`：移除重复 `MemoryCache` 实现，委托 `infrastructure.memory_cache.get_cache()`。

### R14 API 响应信封（数据湖模块）
- `routes_v1_data_lake.py`：成功路径 `success_response`；错误路径 `error_payload(ErrorCode.INTERNAL_ERROR, ...)`，去除裸 `{"status":"error"}`。

### CSP 收尾
- `run_history.html`：MLflow 链接 `onclick` → `data-rh-action="mlflow-link"` + `stopPropagation` 委托。

### 测试
- `tests/infrastructure/test_cache_manager.py`

---

## 2026-06-16 — P1 第三批（R13/R14 续 + R17 切片）

### R14 API 响应信封（实验 / 历史共振 / 生命周期监控）
- `routes_v1_experiments.py`：列表/详情 `success_response`；列表异常 `error_payload(INTERNAL_ERROR)`；`NotFoundError` 交全局 handler。
- `routes_v1_historical_resonance.py`：加 `@register_routes` 注册；校验错误 `error_payload`；成功 `success_response`；修正子蓝图前缀为 `/historical-resonance`。
- `v1/lifecycle/monitoring_routes.py`：6 条监控路由改 `success_response`（去除裸 `jsonify({"ok": True})`）。

### R13 QuoteCache L1
- `quote_cache.py`：读路径 L1 `MemoryCache` → Redis 回填；写路径双写 L1 + Redis；Redis 不可用时仍可用进程内缓存。

### R17 OrderPersistence 切片
- 新增 `domain/trading/global_persistence.py`：`GlobalPersistence` 单例 + `get_persistence()`。
- `order_persistence.py`：移除尾部 ~300 行空行类定义，re-export `GlobalPersistence` / `get_persistence`。

### 测试
- `tests/infrastructure/test_quote_cache.py`

---

## 2026-06-16 — P1 第四批（R13/R14 续：cognitive_mesh + 缓存 L1 统一）

### R14 cognitive_mesh
- `routes_v1_cognitive_mesh.py`：加 `@register_routes` 自动挂载（此前仅有未注册的 `bp`）；子蓝图前缀 `/cognitive-mesh`；14 条路由改 `success_response` / `error_payload`。

### R13 缓存 L1 统一
- `multi_level_cache.py`：L1 内嵌 dict 改为 `get_cache()`（`MemoryCache`）；Redis 命中回填 L1。
- `request_middleware.py`：`RequestCache` 委托 `get_cache()`，键前缀 `reqcache:`。

### 测试
- `tests/infrastructure/test_multi_level_cache.py`
- `tests/application/test_request_cache.py`

---

## 2026-06-16 — P1 第五批（R14 zen/jarvis/tokenized + R13 QuoteCache）

### R14 API 响应信封
- `routes_v1_zen_mode.py`：13 条路由 `success_response` / `error_payload`；子蓝图前缀 `/zen-mode`（修复 `/api/v1` 双前缀）。
- `routes_v1_jarvis_feed.py`：加 `@register_routes`；前缀 `/jarvis`；`feed` / `feed/clear` 改标准信封。
- `routes_v1_tokenized_alpha.py`：`mint` / `get` / `hero-board` / `reputation` 改标准信封；404 用 `ErrorCode.NOT_FOUND`。

### R13 QuoteCache → CacheManager
- `quote_cache.py`：移除直连 Redis，统一 `get_cache_manager()`（L1+L2）。

### 测试
- `tests/infrastructure/test_quote_cache.py`（适配 CacheManager mock）
- `routes_v1_provenance.py`：补 `blueprint` 别名（修复既有 smoke 测试导入）

---

## 2026-06-16 — P1 第六批（R14 收尾 + R17 文件后端）

### R14 API 响应信封
- `routes_v1_self_healing_execution.py`：6 条路由标准信封 + `ErrorCode`。
- `routes_v1_strategy_wizard.py`：子蓝图 `/strategy/wizard`（修复路径与前端契约）；标准信封。
- `routes_v1_truth_badge.py` / `routes_v1_data_verify.py`：`success_response`。
- `strategy_wizard.html`：`wizardFetch` 解包 `success_response.data`。

### R17 OrderPersistence 文件后端
- 新增 `order_persistence_file.py`（`FileOrderPersistenceBackend`）。
- `order_persistence.py`：3810 行 → ~160 行；文件 I/O 委托 backend；保留 SQLite/Redis 路径。

### 测试
- `tests/domain/trading/test_order_persistence_file.py`

---

## 2026-06-16 — P1 第七批（R17 完成：SQLite/Redis 后端外提）

### R17 OrderPersistence 三分 backend
- 新增 `order_persistence_sqlite.py`（`SqliteOrderPersistenceBackend`）。
- 新增 `order_persistence_redis.py`（`RedisOrderPersistenceBackend`，可注入 client 便于测试）。
- `order_persistence.py`：仅保留门面 + 路由；无内联 SQL/Redis 实现（~90 行）。

### P2 状态备注（Alembic）
- 仓库已有 `alembic.ini` + `alembic/versions/`（含 `p0_infrastructure.py` 等）；`env.py` 绑定 `Base.metadata` + MySQL URI。本批未改迁移链。

### 测试
- `tests/domain/trading/test_order_persistence_file.py`：补充 SQLite/Redis 单测与集成测---

---

## 2026-06-21 - P1 Fix: ORM Migration Demo + API Response Unification

### P06 - 5 High-Frequency Repository ORM Migration Demo
- Created pp/infrastructure/repositories/mysql/orm_facade.py with 5 Facade classes demonstrating SQLAlchemy ORM replacing raw SQL:
  - ORMUserFacade: list_users(), get_by_username(), create_user() - ORM eager load + joinedload
  - ORMWatchlistFacade: list_symbols(), add_symbol(), remove_symbol() - ORM select/delete
  - ORMStockGroupFacade: list_groups(), add_symbol_to_group() - ORM order_by/merge
  - ORMMarketDataFacade: get_historical_bars() - StockHistory ORM filter/limit
  - ORMSignalObservationFacade: create_observation(), list_recent_signals() - text() SQL wrapper (no ORM model for signal_observations table yet)
- Compile verified, all 5 classes import cleanly
- Whitepaper checklist: P06 [x]

### P07 - API Response Format Unification
- app/presentation/api/error_handlers.py: _error_payload() standardized to {success, data, error, meta}, retaining status/request_id for backward compatibility
- app/presentation/api/actionable_error_catalog.py: enrich_error_payload() compatible with new format
- app/application/errors.py: ApplicationError.to_payload() unified to standard format
- Test expectations updated: tests/api/test_api_error_handlers.py + tests/presentation/api/test_domain_error_handlers.py
- Whitepaper checklist: P07 [x]

### Verification
- All modified files pass py_compile
- All tests green (21 error handler tests)
- App boots with 0 new warnings
