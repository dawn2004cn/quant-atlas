# Flask → SPA 页面全景清单

> **日期**: 2026-06-21
> **上下文**: B 方案（回滚 M1+M2 已迁页面到 switcher 灰度形态）的前置盘点
> **数据来源**: `app/presentation/web/*.py` 全量扫描 + `frontend/src/pages/*.tsx` 全量扫描

---

## 总览

| 分类 | 数量 | 描述 | B 方案动作 |
|---|---|---|---|
| **A. 302 redirect → SPA** | 38 route (36 unique page) | Flask 路由已改为 `redirect("/app/...", code=302)` | **回滚到 render_template + spa_switcher 块** |
| **B. 双轨并存** | ~15 | Flask 仍 render_template + 对应 SPA 页面也存在 | **加 spa_switcher 链接（不回滚，因为没 302 过）** |
| **C. SPA-only** | ~5 | SPA 页面无 Flask 对应路由 | **不加回跳口（无 Jinja 可回）** |
| **D. Jinja-only（M3 候选）** | ~25 | Flask 仍 render_template，无对应 SPA | **M3 迁移时走完整 switcher 三阶段** |
| **E. 特殊路由** | 6 | 登录/注册/OAuth/logout/头像等 | **不动（认证路由不属于迁移范围）** |
| **F. 死代码** | 1 file | `spa_redirects.py` 从未被调用 | **删除或标记为死代码** |

---

## Group A: 302 redirect → SPA（B 方案核心回滚目标）

### 来源 1: pages_*.py 静态字符串 redirect（38 处）

| # | Flask 路由 | → SPA URL | 来源文件 | Jinja 模板是否仍存在 |
|---|---|---|---|---|
| 1 | /collaboration | /app/collaboration-workspace | pages_admin.py | 待验证 |
| 2 | /task-center | /app/task-center | pages_admin.py | 待验证 |
| 3 | /alert-center | /app/alert-center | pages_admin.py | 待验证 |
| 4 | /expert-teams | /app/expert-teams | pages_admin.py | 待验证 |
| 5 | /run-history | /app/run-history | pages_admin.py | 待验证 |
| 6 | /agent-center | /app/agent-center | pages_admin.py | 待验证 |
| 7 | /swarm-dashboard | /app/swarm-dashboard | pages_admin.py | 待验证 |
| 8 | /swarm-designer | /app/swarm-designer | pages_admin.py | 待验证 |
| 9 | /swarm-designer/flow | /app/swarm-designer | pages_admin.py | 待验证 |
| 10 | /research-canvas | /app/research-canvas | pages_admin.py | 待验证 |
| 11 | /war-room | /app/war-room | pages_admin.py | 待验证 |
| 12 | /voice-briefing | /app/voice-briefing | pages_admin.py | 待验证 |
| 13 | /decision-replay | /app/decision-replay | pages_admin.py | 待验证 |
| 14 | /moments | /app/moments | pages_admin.py | 待验证 |
| 15 | /yanbao-hub | /app/yanbao-hub | pages_admin.py | 待验证 |
| 16 | /message-center | /app/message-center | pages_admin.py | 待验证 |
| 17 | /ai-hedge-fund | /app/ai-hedge-fund | pages_ai.py | 待验证 |
| 18 | /ai-investment-committee | /app/ai-investment-committee | pages_ai.py | 待验证 |
| 19 | /ai-committee-dashboard | /app/ai-committee-dashboard | pages_ai.py | 待验证 |
| 20 | /ai-committee-selection | /app/ai-committee-selection | pages_ai.py | 待验证 |
| 21 | /nl-strategy | /app/nl-strategy | pages_ai.py | 待验证 |
| 22 | /ai-analysis | /app/ai-analysis | pages_ai.py | 待验证 |
| 23 | /ai-research-report | /app/ai-research-report | pages_ai.py | 待验证 |
| 24 | /ai-chat | /app/ai-chat | pages_ai.py | 待验证 |
| 25 | /research-pipeline | /app/research-pipeline | pages_ai.py | 待验证 |
| 26 | /strategy-wizard | /app/strategy-wizard | pages_ai.py | 待验证 |
| 27 | /global-radar | /app/global-radar | pages_market.py | 待验证 |
| 28 | /tdx-blocks | /app/tdx-blocks | pages_market.py | 待验证 |
| 29 | /hot-sectors | /app/hot-sectors | pages_market.py | 待验证 |
| 30 | /strategy-compare | /app/strategy-compare | pages_stock.py | 待验证 |
| 31 | /strategy-snapshots | /app/strategy-snapshots | pages_stock.py | 待验证 |
| 32 | /self-stocks | /app/self-stocks | pages_stock.py | 待验证 |
| 33 | /long-term-select | /app/long-term-select | pages_stock.py | 待验证 |
| 34 | /stock-selector | /app/stock-selector | pages_stock.py | 待验证 |
| 35 | /signal-observations | /app/signal-observations | pages_stock.py | 待验证 |
| 36 | /investment-managers | /app/investment-managers | pages_stock.py | 待验证 |
| 37 | /portfolio | /app/portfolio | pages_stock.py | 待验证 |

### 来源 2: pages_*.py f-string redirect（6 处，含路径参数）

| # | Flask 路由 | → SPA URL | 来源文件 | 备注 |
|---|---|---|---|---|
| 38 | /decision-snapshot/\<id\> | /app/decision-snapshot/\<id\> | pages_stock.py | 动态路径 |
| 39 | /share/decision/\<token\> | /app/share/decision/\<token\> | pages_stock.py | 公共分享页（ADR-0006 保留 SSR 例外）⚠️ |
| 40 | /investment-managers/\<id\> | /app/investment-manager-detail | pages_stock.py | 动态路径 |
| 41 | /selection-result/\<id\> | /app/selection-result | pages_stock.py | 动态路径 |
| 42 | /portfolio/\<id\> | /app/portfolio-detail | pages_stock.py | 动态路径 |
| 43 | /task/\<id\> | /app/task-detail | pages_admin.py | 动态路径 |

> ⚠️ **#39 `/share/decision/<token>` 是 ADR-0006 保留的 SSR 例外**——此路由不应该重定向到 SPA，应保留 Jinja SSR。这是一个 **bug**：M1+M2 迁移时错误地对公共分享路径做了 302 redirect。B 方案回滚此路由时不能加 spa_switcher，应直接恢复 `render_template("decision_snapshot_public.html")`。

### 来源 3: spa_redirects.py（死代码，11 处）

`app/presentation/web/spa_redirects.py` 定义了 11 个 M1 redirect + 3 个参数化 redirect，但 `register_spa_redirects()` 从未被任何模块调用。这些路由 **没有生效**，与 source 1 中部分路由重复。

**状态**: 死代码。B 方案无需处理（但建议清理）。

---

## Group B: 双轨并存（Flask render_template + 对应 SPA 页面）

这些路由当前仍用 `render_template` 渲染 Jinja，但对应的 SPA 页面也存在于 `/app/` 下。**用户可以直接通过 URL 访问两个版本**。

| # | Flask 路由 | Jinja 模板 | SPA 页面 | SPA URL | 来源文件 |
|---|---|---|---|---|---|
| 1 | / | daily_workbench.html | Dashboard.tsx | /app/dashboard | pages_market.py |
| 2 | /dashboard | index.html | Dashboard.tsx | /app/dashboard | pages_market.py |
| 3 | /backtest | (待验证) | Backtest.tsx | /app/backtest | pages_market.py |
| 4 | /login | (_render_login helper) | Login.tsx | /app/login | auth.py |
| 5 | /alpha-factory | (待验证) | AlphaFactory.tsx | /app/alpha-factory | pages_ai.py |
| 6 | /market-panorama | market_panorama.html | MarketPanorama.tsx | /app/market-panorama | pages_market.py |
| 7 | /signal-flag | (待验证) | SignalFlag.tsx | /app/signal-flag | pages_stock.py |
| 8 | /experiment-report | experiment_reporter.html | ExperimentReport.tsx | /app/experiment-report | pages_admin.py |
| 9 | /longhu-bang | longhu_bang.html | LonghuBang.tsx | /app/longhu-bang | pages_market.py/stock.py |
| 10 | /selection-result/\<id\> | (待验证) | SelectionResult.tsx | /app/selection-result | pages_stock.py |
| 11 | /profile | (待验证) | — | — | pages_admin.py |
| 12 | /retail-assistant | (待验证) | — | — | pages_admin.py |

> **注**: #11 `/profile` 和 #12 `/retail-assistant` 可能没有对应 SPA 页面——需进一步验证。

**B 方案对 Group B 的动作**：加 `spa_switcher` 块指向 SPA 版本。不需要回滚（因本身无 302 redirect）。

---

## Group C: SPA-only（无 Flask 对应路由）

这些 SPA 页面没有对应的 Flask 路由（既无 redirect 也无 render_template）。它们只能通过 `/app/` 前缀直接访问。

| # | SPA 页面 | SPA URL | 说明 |
|---|---|---|---|
| 1 | NotFound.tsx | /app/not-found | 404 页面 |
| 2 | TaskDetail.tsx | /app/task/\<id\> | 任务详情（与 Group A #43 对应） |
| 3 | PortfolioDetail.tsx | /app/portfolio/\<id\> | 组合详情（与 Group A #42 对应） |
| 4 | InvestmentManagerDetail.tsx | /app/investment-manager-detail | 基金经理详情 |
| 5 | DecisionReplaySpace.tsx | /app/decision-replay-space | — |

> **注**: 此清单可能不完整——需要逐个验证 SPA 路由注册 (`App.tsx`) 与 Flask 路由的对应关系。

**B 方案对 Group C 的动作**：无。不需要加回跳口（没地方回退）。

---

## Group D: Jinja-only（M3 候选，仍 render_template）

| # | Flask 路由 | Jinja 模板 | 来源文件 |
|---|---|---|---|
| 1 | /alpha-marketplace | marketplace.html | pages_ai.py |
| 2 | /architecture-roadmap | architecture_roadmap.html | pages_market.py |
| 3 | /attribution-dashboard | attribution_dashboard.html | pages_stock.py |
| 4 | /data-lake-health | data_lake_health.html | pages_market.py(?) |
| 5 | /factor/\<id\> | factor_detail.html | pages_ai.py |
| 6 | /factor-evolution | factor_evolution.html | pages_ai.py |
| 7 | /factor-repository | factor_repository.html | pages_ai.py |
| 8 | /optimize | optimize.html | pages_admin.py |
| 9 | /portfolio-resonance | portfolio_resonance.html | pages_ai.py |
| 10 | /professional-workbench | professional_workbench.html | pages_ai.py |
| 11 | /quant-lab | quant_lab.html | pages_admin.py |
| 12 | /register | register.html | auth.py |
| 13 | /shadow-account | shadow_account.html | pages_admin.py |
| 14 | /stocks-manage | stocks_manage.html | pages_admin.py |
| 15 | /truth-droplet | truth_droplet.html | truth_droplet_routes.py |
| 16 | /users-manage | users_manage.html | pages_admin.py |
| 17 | /user-spectrum-hub | user_spectrum_hub.html | pages_ai.py |
| 18 | /user-tiers/boutique | user_tiers_boutique.html | pages_ai.py |
| 19 | /user-tiers/fund | user_tiers_fund.html | pages_ai.py |
| 20 | /user-tiers/institution | user_tiers_institution.html | pages_ai.py |
| 21 | /user-tiers/investment | user_tiers_investment.html | pages_ai.py |
| 22 | /zen-dashboard | zen_dashboard.html | pages_ai.py |
| 23 | /zen-terminal | zen_terminal.html | pages_ai.py |
| 24 | /capabilities | (待验证) | pages_market.py |
| 25 | /integration-hub | (待验证) | pages_market.py |
| 26 | /observability | (待验证) | pages_market.py |
| 27 | /ui-showcase | (待验证) | pages_market.py |
| 28 | /ui-showcase/dark | (待验证) | pages_market.py |
| 29 | /ui-showcase/light | (待验证) | pages_market.py |

> **注**: 24-29 需要验证 Jinja 模板名称。

**B 方案对 Group D 的动作**：无（不在本次回滚范围内）。这些是 M3 迁移时走完整 switcher 三阶段的页面。

---

## Group E: 特殊路由（不动）

| Flask 路由 | 类型 | 处理方式 | 说明 |
|---|---|---|---|
| /login (GET+POST) | 认证 | `_render_login()` | 登录表单，不在迁移范围 |
| /register (GET+POST) | 认证 | render_template(register.html) | 注册表单，不在迁移范围 |
| /logout | 认证 | redirect(url_for(...)) | 注销，不在迁移范围 |
| /auth/wechat/start | OAuth | url_for / abort | 微信 OAuth 回调 |
| /auth/wechat/callback | OAuth | url_for / abort | 微信 OAuth 回调 |
| /auth/oauth/start | OAuth | url_for / abort | 通用 OAuth |
| /auth/oauth/callback | OAuth | url_for / abort | 通用 OAuth |
| /admin-only | 装饰器 | (permission check) | 管理员权限检查 |
| /avatars/user | API | (头像服务) | 静态头像 |
| /avatars/pm/\<id\> | API | (头像服务) | 静态头像 |

---

## Group F: 死代码

| 文件 | 说明 | 动作建议 |
|---|---|---|
| app/presentation/web/spa_redirects.py | 定义了 11 + 3 个 redirect，但 `register_spa_redirects()` 从未被调用 | M0 清理时删除或标记 `# DEPRECATED: never registered` |

---

## 关键发现

### 发现 1: `/share/decision/<token>` 被 302 了

根据 ADR-0006，公共分享路径应保留 Jinja SSR。但 M1+M2 迁移时错误地把它也改成了 302 redirect 到 SPA。**B 方案必须恢复此路由为 `render_template("decision_snapshot_public.html")`，不加 spa_switcher。**

### 发现 2: 双轨并存是无意为之

Group B 的 12 个页面（`/dashboard`, `/login`, `/backtest` 等）是"老 11 页预迁 SPA"阶段留下的——Flask `/dashboard` 仍在渲染 Jinja，同时 `/app/dashboard` 渲染 React。这不是刻意设计，而是 M1+M2 没有处理根路径的残留。

### 发现 3: `spa_redirects.py` 是死代码

另一个 agent 创建了 `spa_redirects.py` 来集中管理 redirect，但忘记在 bootstrap 里调用 `register_spa_redirects()`。实际生效的 redirect 仍在 `pages_*.py` 里。建议在 B 方案执行时一并清理。

### 发现 4: Group B 和 Group A 有部分重叠

注意 `decision_snapshot` 在 Group A 有 `redirect` 版本，在 `spa_redirects.py` 有参数化版本，但 `/decision-snapshot/<id>` 指向 `/app/decision-snapshot/<id>` — 这与 `DecisionSnapshot.tsx` 对应的是 `/app/decision-snapshot`（列表页），而 `decision_snapshot_public.html` 是公共分享页（ADR-0006 保留 SSR）。

---

## B 方案执行前置条件

1. **验证 Group A 所有 Jinja 模板仍存在且可渲染**（`templates/` 下有 `.html` 文件不代表模板 context 完整）。
2. **验证 Group B 12 个双轨页面**——确认哪些有 SPA 对应页面、哪些没有。
3. **修复 `/share/decision/<token>` bug**——恢复 SSR，不加 switcher。
4. **清理 `spa_redirects.py` 死代码**。
5. **完成 M0 任务 0.5（switcher 基础设施）后**才能开始执行回滚。

---

## 附: 数据文件

- `tmp_rollback_map.csv`: Group A 38 条 302 redirect 精确映射 (CSV)
- `tmp_all_routes.csv`: 所有 101 条 Flask 路由全量扫描 (CSV)