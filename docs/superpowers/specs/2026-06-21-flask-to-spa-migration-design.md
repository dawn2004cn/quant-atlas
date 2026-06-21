# Flask -> SPA 迁移设计文档

- **日期**：2026-06-21
- **状态**：Draft，待用户审查
- **作者**：Brainstorming session（OpenCode + 用户）
- **关联**：`frontend/`（已存在的 React 19 SPA 工程）、`mobile/`（Flutter 工程，未来消费同一组 API）

---

## 0. 背景与现状

QuantAtlas 后端是 Flask 单进程，同时承担两类职责：

- **JSON API**：`app/presentation/api/routes_v1_*.py`，共 110 个路由文件，整体约 575 路由
- **服务端渲染（SSR）页面**：`app/presentation/web/pages_*.py`，共 88 个 Jinja 页面路由，对应 `app/presentation/web/templates/` 下 114 个 `.html` 模板（含 components / layouts / partials）

SPA 已经迈出第一步：

- `frontend/` 目录已存在 React 19 + Vite + TypeScript + Tailwind + DaisyUI + react-router v7 + SWR + socket.io-client + i18next 的完整工程
- 已实现 11 个页面：Dashboard / Login / Backtest / MarketPanorama / RunHistory / ExperimentReport / Marketplace / StockDetail / AlphaFactory / SignalFlag / NotFound
- Flask 通过 `app/presentation/web/pages_spa.py` 在 `/app/*` 挂载 React 构建产物（`frontend/dist/`）
- Vite dev server 通过 `/api`、`/login`、`/socket.io` 反向代理到 `127.0.0.1:5000`

`mobile/` 目录还存在一个 Flutter 工程（`pubspec.yaml` + `lib/`），未来要消费同一组 API。

剩余 **75 个 Jinja 业务页面** 需要迁到 SPA（详细分批见第 3 节）。本文档定义这次迁移的目标、形态、节奏、保障与里程碑。

---

## 1. 目标与终态愿景

迁移完成后：

- Flask **收敛为纯 API 服务器**：REST + SSE + Socket.IO
- React SPA 在 `/app/*` 接管所有用户界面
- Flutter 作为同一组 API 的第二消费方，从 day 1 拥有强类型 SDK
- `Flask-Login` cookie 认证路径在 M3 末下线
- `templates/` 目录**全部保留**作为历史归档与回滚备份；迁完的页面对应模板冻结（不再演进），新功能一律走 SPA

**非目标**：

- 不重写后端业务逻辑
- 不引入 SSR / Next.js 等服务端 React 框架
- 不引入 GraphQL
- 不删除 `templates/` 目录（保留作归档）
- 不在本次迁移内改造 Flutter 工程本身（仅在 M4 试产 SDK）

---

## 2. 路由形态

### 2.1 SPA 位置

- SPA 始终位于 `/app/*`，**保持现状**
- 选择 `/app/*` 而非根路径的理由：未来若需要把 SPA 拆出 Flask（例如 CDN 托管 + 独立 API 服务器），迁移成本接近零

### 2.2 老 Jinja URL 处置（302 灰度 -> 301 永久）

每个 Jinja 页面迁完后，对应的 Flask 路由实现替换为重定向到 `/app/<对应路径>`，分两阶段：

- **第一阶段（灰度一周）**：返回 `302 Found`。浏览器不缓存，每次仍命中服务器，便于观察跳转目标是否正确、访问量是否符合预期、是否有外部系统依赖被打断
- **第二阶段（永久）**：切换为 `301 Moved Permanently`。浏览器永久缓存，外链/书签/搜索引擎索引随之迁移

**为什么不直接 301**：301 会被浏览器强缓存，一旦 `Location` 写错，老用户的浏览器即使在服务器修复后仍会跳到错误地址，必须清浏览器缓存才能恢复。302 灰度是廉价的工程保险。

**Flask 实现示例**：

```python
# 灰度阶段（302）
from flask import redirect

@blueprint.route("/dashboard")
def dashboard():
    return redirect("/app/dashboard", code=302)

# 灰度通过后切换为永久（301）
@blueprint.route("/dashboard")
def dashboard():
    return redirect("/app/dashboard", code=301)
```

### 2.3 特殊路径

以下路径在迁移前需要单独评审是否保留 SSR 入口（在 M3 决定）：

- `/share/decision/<share_token>`（公共分享，可能被搜索引擎或社交平台抓取）
- `/decision-snapshot/<snapshot_id>`（嵌入分享场景）

---

## 3. 迁移顺序（按价值密度）

### 3.1 已完成（11 页）

Dashboard / Login / Backtest / MarketPanorama / RunHistory / ExperimentReport / Marketplace / StockDetail / AlphaFactory / SignalFlag / NotFound

### 3.2 M1 核心流（约 15 页）

高频、高交互、核心用户工作流：

- `daily_workbench`、`portfolio`、`portfolio_detail`、`self_stocks`
- `hot_sectors`、`global_radar`、`stock_selector`、`long_term_select`
- `strategy_compare`、`strategy_snapshots`、`decision_snapshot`
- `nl_strategy`、`nl_strategy_v2`、`strategy_wizard`、`tdx_blocks`

### 3.3 M2 次核心 + 流式（约 30 页）

AI / 流式重度 / 协作类页面：

- `ai_chat`、`ai_analysis`、`ai_research_report`、`ai_hedge_fund`
- `ai_committee_dashboard`、`ai_committee_selection`、`ai_investment_committee`
- `war_room`、`agent_center`、`agent_lab`、`research_canvas`、`research_pipeline`
- `signal_observations`、`decision_replay_space`、`voice_briefing`
- `swarm_dashboard`、`swarm_designer`、`swarm_designer_flow`
- `collaboration_workspace`、`message_center`、`task_center`、`task_detail`
- `yanbao_hub`、`longhu_bang`、`moments`、`alert_center`
- `selection_result`、`investment_managers`、`investment_manager_detail`、`expert_teams`

### 3.4 M3 长尾（约 30 页）

低频、一次性、不一定值得迁的页面：

- `user_tiers_retail` / `user_tiers_boutique` / `user_tiers_fund` / `user_tiers_institution` / `user_tiers_investment`
- `ui_showcase`、`shadow_account`、`feature_retired`、`architecture_roadmap`
- `capabilities`、`observability`、`integration_hub`
- `register`、`profile`、`users_manage`、`stocks_manage`
- `factor_repository`、`factor_detail`、`factor_evolution`
- `truth_droplet`、`zen_dashboard`、`zen_terminal`、`portfolio_resonance`
- `optimize`、`retail_assistant`、`professional_workbench`、`user_spectrum_hub`
- `attribution_dashboard`、`data_lake_health`、`quant_lab`

**计数对账**：已迁 11 + M1 15 + M2 30 + M3 30 = 86 个业务页面。templates/ 下另有 3 个非业务模板（`base.html` 基础布局；`error_500.html` 错误页；`decision_snapshot_public.html` 公共分享页，去留在第 2.3 节单独评审），合计 88 个 Jinja 路由对应 89 个 .html 模板（含 base.html）。

> 上述清单基于 `app/presentation/web/templates/*.html` 现状盘点。M3 启动前需要做一次最终核对（可能有新增/删除）。

---

## 4. 认证策略（双轨 -> 单轨）

### 4.1 双轨期（M0 启用，M1/M2 期间持续）

登录端点同时设置 cookie session **和**返回 JWT（HS256，过期时间对齐当前 cookie session 过期时间）。

`before_request` 钩子按以下优先级填充 `current_user`：

1. `Authorization: Bearer <token>` -> JWT 解码 -> 加载用户
2. cookie session（Flask-Login 现有路径） -> 加载用户
3. 都没有 -> 匿名

业务代码继续用 `current_user`，对认证形态无感知。

### 4.2 客户端使用方式

- **SPA**：JWT 存储在 `httpOnly` + `Secure` + `SameSite=Strict` 的 cookie 中（不放 `localStorage`，避免 XSS 直接窃取）。所有 API 请求自动带这个 cookie，前端代码不需要手动操作
- **Jinja 残留页**：继续使用现有 Flask-Login session cookie
- **Flutter（M4）**：JWT 存储在平台 secure storage，请求带 `Authorization: Bearer` header

### 4.3 单轨化（M3 末）

由于 `templates/` 全部保留，cookie session 只继续服务于"评审为永久保留 Jinja"的页面。M3 末执行：

- 登录端点停止设置 Flask-Login session cookie
- 删除 Flask-Login 相关代码
- **若仍有 Jinja 残留页面在使用**：这些页面的访问入口同步迁到 JWT（在页面 HTML 中通过 `<script>` 注入 JWT cookie 的方式继续支持）；或评估这些页面的 PV，若极低则接受 cookie 下线后该页失效（M3 评审会上明确）

### 4.4 流式通道认证

- **Socket.IO**：连接握手时带 `auth: { token }`，服务端在 `connect` 事件用相同 JWT 解码逻辑校验
- **SSE / EventSource**：因 `EventSource` 浏览器 API 不支持自定义 header，token 通过 URL query string 传递（`?token=...`），后端做相同 JWT 解码。Token 须为短期（5 分钟），SSE 连接前由前端用主 JWT 换取一次性 SSE token，避免主 JWT 被记录在 access log


---

## 5. API 契约（渐进式 OpenAPI）

### 5.1 工具栈

- Schema 定义：pydantic v2（项目已有）
- OpenAPI 生成：apispec + apispec-webframeworks 的 Flask 适配器，或 flask-smorest（含路由装饰器 + 自动 schema 注册）；M0 决定具体选型
- CI 产物：docs/openapi.json（每次 PR 自动生成并校验进仓库）
- 前端类型生成：openapi-typescript，输出到 frontend/src/api/types.ts，CI 校验生成结果与仓库内同步

### 5.2 推进节奏（与页面迁移捆绑）

每迁一个页面，在该 PR 内：

1. 列出该页面消费的所有 API 端点
2. 为每个端点的入参（query / path / body）和出参定义 pydantic model
3. 在 Flask 路由上添加 OpenAPI 注解
4. CI 校验：路由声明的 schema 与实际响应一致；TS 类型已重新生成并提交

**CI 强制规则**：新迁页面 PR 必须包含其依赖 API 的 schema；已纳入契约的端点不可在不更新 schema 的情况下被改签名。

### 5.3 M4 契约固化

所有页面迁完后，做一次统一对齐：

- 命名规范：snake_case（与现有 Python 后端一致），TS 侧由生成工具透传
- 错误形态：统一 { code, message, details } 形态（项目已有 error_codes.py 枚举可直接对齐）
- 分页规范：统一 { items, total, page, page_size } 或 cursor-based，全局二选一
- 时间戳：统一 ISO 8601 UTC 字符串，禁止混用 unix timestamp
- 完成上述对齐后，发首版 Flutter Dart SDK 试产

---

## 6. 流式契约（Socket.IO + SSE）

### 6.1 不引入完整 AsyncAPI

完整 AsyncAPI 工具链投入产出比低。改用「pydantic event model + 单页 events.md」的轻量方案。

### 6.2 事件 model 定义

约定：所有 Socket.IO 事件 / SSE 帧的 payload 必须有对应的 pydantic model，集中放在 app/domain/events/ 下。后端发送前先 model.model_dump()，前端按 events.md 描述消费。

示例（app/domain/events/watchlist.py）：

    from pydantic import BaseModel
    from datetime import datetime

    class WatchlistAnomalyDetectedEvent(BaseModel):
        # 触发：自选股异常检测发现异动
        user_id: str
        symbol: str
        anomaly_type: str  # price_spike | volume_spike | news
        severity: int      # 1-5
        detected_at: datetime

### 6.3 events.md 格式

docs/events.md 列出所有事件，每条一段：

    ## watchlist.anomaly_detected (Socket.IO)
    - payload: WatchlistAnomalyDetectedEvent (app/domain/events/watchlist.py)
    - 触发: 自选股 agent 检测到价格/量能/新闻异常
    - 频率: 突发，单用户单 symbol 5 分钟内最多一次
    - 消费方: 自选股页面、Jarvis 通知面板

### 6.4 推进节奏

与页面迁移捆绑：迁某个流式页面时，把该页面消费的所有事件加 model + events.md 条目。

---

## 7. 测试与回归保障

### 7.1 Playwright 关键路径 E2E

- M0 在 tests/e2e/ 下搭起 Playwright 工程（独立于 tests/ 下现有 pytest）
- 写 5-10 条核心流脚本：
  1. 登录 -> daily_workbench 首屏关键卡片可见
  2. 选股流：market_panorama -> 点击某 symbol -> stock_detail 加载
  3. 回测流：backtest 页面提交一次任务 -> RunHistory 看到结果
  4. 决策快照流：portfolio -> 创建快照 -> decision_snapshot 打开
  5. 流式流：ai_chat 发送一条消息 -> 收到首个 SSE 帧
- CI 必须跑通 E2E 才能合并 PR

### 7.2 长尾页面验收

- M3 长尾页面采用人肉验收（PV 极低，自动化投入产出比不划算）
- 每个长尾页面在迁完 PR 中附带 5 张以上截图（关键交互前后对比）

### 7.3 redirect 验证

- 每个 302/301 上线前必须用 curl -I 在 staging 验证 Location 正确
- 灰度期间监控 access log 中该路径的 status code 分布

---

## 8. 五里程碑

| 里程碑 | 目标 | 主要交付物 | 退出条件 |
|---|---|---|---|
| **M0 地基** | 把迁移所需的基础设施先建好 | JWT 双轨认证生效；apispec/openapi 流水线跑通；Playwright 框架 + 5 条核心 E2E；frontend api/ 目录骨架；事件 pydantic model 范式；CI 校验规则上线 | 所有 11 个已迁页面回归通过；新页面迁移 PR 模板可用 |
| **M1 核心流** | 15 个核心页面迁完 | 15 页 SPA 实装；老 URL 走 302 灰度 1 周再切 301；OpenAPI 覆盖核心域 API；Playwright 全绿 | 15 页全部 301 上线 >= 1 周无回归 |
| **M2 次核心 + 流式** | 30 个 AI/协作/流式页面迁完 | Socket.IO / SSE 双轨认证稳定；events.md 覆盖所有迁过的流式事件；30 页 SPA 实装并 301 | 30 页全部 301 上线 >= 1 周无回归 |
| **M3 长尾收尾（硬截止 2 天）** | 30 个长尾页面逐项处置 | Day 1：拉 90 天 PV 日志按访问量分档；Day 2 上午：评审会做迁/保留 Jinja 二选一；Day 2 下午：高 PV 快速迁移，低 PV 标注 frozen 注释；Flask-Login cookie 路径在所有 Jinja 页面也走 JWT 后下线 | 30 页全部有处置决定并执行 |
| **M4 契约固化 + Flutter 试产** | OpenAPI 字段/错误/分页统一 + Flutter SDK 首版 | 命名/错误/分页/时间戳规范 PR；Dart SDK 自动生成流水线；mobile/ 工程接入并跑通登录 + 一条核心 API | Flutter 屏幕可成功登录并展示一条核心 API 数据 |

> M3 的 2 天硬截止是工程姿态选择：长尾页面通常 80% 访问量集中在 20% 页面上，逼团队直面这页面还有人用吗。M3 的执行模式不是逐页迁移而是一次性评审 + 批量处置。

---

## 9. 风险与退路

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| **R1: 双轨认证逻辑漂移** | API 在某条路径上 cookie 通过但 JWT 失败（或反之），导致迁移到一半某些功能突然 401 | M0 末写一份认证集成测试作为基线，覆盖 cookie-only / JWT-only / 同时存在 三种场景；每次改动 before_request 钩子都要跑这套测试 |
| **R2: Jinja 与 SPA 风格不一致引发用户困惑** | 用户在不同页面间跳转时认为产品出 bug | 在 base.html 加一条横幅提示该页面正在升级；在 SPA 对应页面加反馈不一致按钮 |
| **R3: 301 缓存写错** | 老用户浏览器永久跳到错误地址，必须清缓存 | 每页 302 灰度 1 周 -> 监控日志确认 -> 才切 301；上线前 curl -I 在 staging 验证 Location；准备一个 302 强制覆盖 301 的应急 PR 模板（虽然不能完全治愈已缓存浏览器，但能阻断新缓存形成） |
| **R4: OpenAPI schema 跟不上迁移速度** | 渐进契约目标在压力下被跳过 | CI 强制规则：新迁页面 PR 必须包含其依赖 API 的 schema；CI 提取已注解端点列表与路由表 diff，未注解端点新增即拒绝合并 |
| **R5: M3 长尾 2 天截止被迫违反** | 评审会发现某页面虽然 PV 极低但是被关键合规流程依赖，必须迁但 2 天做不完 | M3 评审会议程明确包含识别意外依赖环节；若发现，立即升级为 M3 之后单独立项，不要把它塞回 M3 拖期 |
| **R6: 流式 token 通过 URL 暴露** | SSE token 在 access log / referer 中泄露 | SSE 用一次性短期 token（5 分钟、单连接绑定），由 /api/v1/sse/token 用主 JWT 换取，不复用主 JWT |
| **R7: Flutter 在 M4 才接入，发现 API 契约对移动端不友好** | M4 试产时大量返工 | M0 末写一份移动端契约约束清单（例如：避免长轮询、SSE 改 WebSocket、避免大对象、强制版本化），M1/M2 渐进 schema 时遵守这些约束 |

---

## 10. 待 M0 决策的开放问题

以下问题不阻碍本设计文档定稿，但需要在 M0 实施前明确：

1. **OpenAPI 工具选型**：apispec vs flask-smorest。flask-smorest 集成度更高但需要重构现有 blueprint；apispec 更轻量但需要手写更多注解
2. **JWT 算法**：HS256（共享密钥，简单）vs RS256（公私钥，便于多服务校验）。当前单进程下 HS256 足够，但若 M4 后 API 拆出独立服务，RS256 更易扩展
3. **JWT 过期 + refresh 策略**：无 refresh（短期 token，过期重新登录）vs sliding refresh（活跃用户自动续期）vs refresh token（双 token 体系）
4. **Playwright 跑在 CI 还是仅本地**：CI 跑慢但稳定；仅本地跑快但执行率低
5. **既有 11 个 SPA 页面的补强**：当前页面是否需要追加 Playwright 覆盖？预期 M0 内补完
6. **公共分享路径**（/share/decision/<token>）：保留 SSR 还是迁到 SPA？保留 SSR 利于搜索引擎抓取，迁 SPA 一致性更好

---

## 11. 不在本设计范围内

- 本次迁移**不**重构现有 Flask 业务逻辑、领域模型、bootstrap 流程
- **不**触碰 Celery 任务、数据库 schema、领域事件总线
- **不**调整 app/modules/ 下的服务边界
- **不**评估或重写 mobile/ Flutter 工程本身（仅在 M4 试产 SDK + 验证一条核心 API）
- **不**优化 SPA 自身的性能、可访问性、国际化（这些是 SPA 工程的常规迭代，不属于迁移范围）
- **不**触动既有 11 个已迁 SPA 页面的实现（除非 M0 评审决定补强 Playwright 覆盖）

---

## 12. 决策摘要（来自 brainstorming session）

| # | 决定项 | 选择 |
|---|---|---|
| 1 | 终态 | A 完全替换 Jinja，Flask 收敛为纯 API + 为 Flutter 共享预留 |
| 2 | URL 形态 | B 保持 /app/* 前缀，老 URL 全部跳到 /app/* |
| 3 | 迁移节奏 | C 按价值密度排序 |
| 4 | API 契约 | C 渐进式 OpenAPI（pydantic + apispec/flask-smorest） |
| 5 | 认证策略 | C 双轨（cookie + JWT），M3 末下线 cookie |
| 6 | 流式契约 | A+C 双轨认证 + 渐进事件契约（pydantic event model + events.md） |
| 7 | 测试策略 | B Playwright 关键路径 E2E |
| 8 | 里程碑 | C 五里程碑（M0 地基 -> M1 核心流 -> M2 次核心+流式 -> M3 长尾收尾 -> M4 契约固化+Flutter SDK 试产） |
| 9 | 重定向 | A 每页先 302 灰度一周，再切 301 |
| 10 | M3 截止 | 2 天硬截止 |
| 11 | templates/ 处置 | 全部保留，迁完页面冻结模板（不再演进） |

---

## 13. 下一步

本设计文档定稿后：

1. 用户审查并批准本设计
2. 调用 writing-plans 技能，将本设计拆解为可执行的实现计划（按里程碑产出 plan 文件，逐个落到 docs/superpowers/plans/）
3. M0 立即启动：地基先行，避免边迁页面边补地基的反复

