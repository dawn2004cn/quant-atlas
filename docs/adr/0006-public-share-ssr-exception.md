# ADR-0006: 公共分享路径 `/share/*` 永久保留 Jinja SSR

- **状态**：Accepted
- **日期**：2026-06-21
- **决策者**：项目负责人
- **关联里程碑**：M0（地基），M3（长尾收尾）
- **关联文档**：`docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md` §2.3（公共分享路径单独评审）

## 背景

项目有公共分享页 `decision_snapshot_public.html`，对应 URL 形如 `/share/snapshot/<id>`：

- **用途**：用户把决策快照（投资决策、回测结果、策略概览）通过链接分享给非用户访问者。
- **特点**：无需登录、搜索引擎可索引、首屏快、内容静态。

终态目标是"完全替换 Jinja"，但分享页对 SEO 友好和首屏速度有强诉求，三个候选方案：

| 选项 | 实现 | 代价 |
|---|---|---|
| A. 保留 Jinja SSR | 这一页继续 Flask 渲染 | "完全替换 Jinja"目标打折，留 1 个 SSR 例外 |
| B. 迁 SPA + 预渲染 | Vite SSR / 预渲染管线 | 新增预渲染流水线（不大但是新事物） |
| C. 迁 SPA 纯 CSR | React 客户端渲染 | 失去 SEO，首屏白屏，体感差 |

## 决策

**采用 A：永久保留 `/share/*` 路由的 Jinja SSR**。

明确：

1. **`/share/*` 是"刻意保留的 SSR 出口"**，不是"忘了迁的 Jinja 残留"——架构上显式承认例外。
2. **其它所有 Jinja 模板在 M3 末必须淘汰**（要么迁 SPA、要么删除）。
3. **`/share/*` 的所有 API 仍走纯 API 体系**（与 SPA 共用），分享页 Jinja 模板只是渲染层，不是业务层。
4. **未来若新增分享类页面**（"分享我的持仓"、"分享我的策略"），均走 `/share/*` 前缀 + Jinja SSR。

## 理由

1. **SEO 是核心诉求**：决策快照分享出去后，用户希望被搜索引擎索引、被社交平台预览（OG meta tags）。爬虫不跑 JS 时纯 CSR 看到空 div，纯 SSR 直接看到完整 HTML。
2. **预渲染管线成本高**：方案 B 需要搭 Vite SSR + 路由列表生成 + 静态文件部署，对一个唯一的分享场景来说杀鸡用牛刀。
3. **首屏速度**：分享链接打开者多是首次访问，没有 SPA 的代码包缓存。SSR 直接给 HTML，比"下 React → 解析 → 跑 → 渲染"快 1–3 秒。
4. **架构清晰度可保**：把 SSR 例外限制在 `/share/*` 前缀，是显式的、可记录的、可测试的——这是好工程，不是技术债。

## 后果

### 正面
- 分享页 SEO / 首屏速度保留。
- 不必搭额外的预渲染管线，M0/M3 工程量节省。
- 架构表达更准确："Flask 收敛为纯 API + 1 个刻意保留的 SSR 例外"。

### 负面
- "完全替换 Jinja"目标打折。每个新人入职都要解释一次"为什么 `/share/*` 还是 Jinja"。
- Jinja 模板的样式系统（CSS）与 SPA 的 Tailwind/DaisyUI 体系分离，可能出现样式漂移。需要在 `/share/*` 共用 SPA 的 CSS 构建产物（部分文件软连接）。
- 共享 `decision_snapshot_public.html` 的 React 组件无法直接复用（因为 Jinja 不跑 React），如果将来分享页要加交互（点赞、评论），还是要回到方案 B。

### 中性
- M3 评审会要明确把"`/share/*` 保留 SSR"作为最终架构决定写进 ADR——这一步已通过本 ADR 完成。

## 实施清单

- [ ] M0 任务 0：本 ADR 写入仓库（已完成）
- [ ] M1：`/share/snapshot/<id>` 路由从 `pages_*.py` 抽出到独立 `pages_public.py` 蓝图
- [ ] M2：`decision_snapshot_public.html` 引用的 CSS 改为引用 SPA 构建产物（`/static/dist/index.css`）
- [ ] M3：评审会议正式确认架构例外，更新 `docs/architecture.md` 添加"SSR 例外清单"
- [ ] M4：若 Flutter mobile 工程实现分享功能，通过 deeplink → `https://<domain>/share/snapshot/<id>` 跳转（不重新实现）

## 替代方案为何被否

- **B. 迁 SPA + 预渲染**：对一个唯一场景搭整套预渲染管线性价比低；将来若分享页数量增加可重新评估升级到方案 B。
- **C. 迁 SPA 纯 CSR**：失去 SEO 和首屏速度，破坏分享页的核心价值——直接否决。
