# ADR-0007: Switcher 灰度机制 — Flask 与 SPA 渐进双轨切换

- **状态**：Accepted
- **日期**：2026-06-21
- **决策者**：项目负责人
- **关联里程碑**：M0（地基），M1/M2/M3（每个迁移页面）
- **关联文档**：`docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md` §9.2（灰度策略）
- **依赖 ADR**：[0006](0006-public-share-ssr-exception.md)（`/share/*` SSR 例外）

## 背景

原迁移计划"每页先 302 灰度一周再切 301"对用户来说是被动切换：用户访问 Flask 旧版页面，被悄悄重定向到 SPA 新版，没有选择权。

实际推进中发现需要更柔性的灰度机制：

1. **用户感知问题**：用户突然被切到陌生 UI（即使更好），可能引发投诉。
2. **数据反馈不足**：直接强切只能拿到"切完之后的稳定数据"，无法获得"切前用户的主动选择信号"——这个信号是决定要不要强切的关键依据。
3. **回退路径缺失**：用户被切后发现新版有不满（即使是主观偏好），没有显式退回口，容易直接弃用。

候选灰度机制：

| 选项 | 节奏 | 用户感知 |
|---|---|---|
| 直接 302（原方案） | 每页 302 一周 → 301 | 被动切换 |
| Switcher 灰度（本 ADR） | 加 switcher 入口 1–2 周 → 302 一周 → 301 | 主动尝鲜 → 渐进强切 |

## 决策

**采用三阶段 Switcher 灰度机制**。每个迁移页面经历：

### 阶段 1：Switcher 入口（1–2 周）
- Flask 旧版页面 `<nav class="app-nav">` 内加一个"试试新版 →"链接，指向对应 SPA URL（`/app/<page>`）。
- SPA 对应页面右下角加一个"回到经典版 ←"小链接（不抢主视觉），点击跳回 Flask。
- 用户可双向自由切换，**默认仍在 Flask**。
- 埋点：switcher 点击数、回跳点击数、SPA 该页停留时长。

### 阶段 2：302 渐进强切（1 周）
- 满足以下任一条件可进入阶段 2：
  - **主动切换率 ≥ 30%**：30% 用户在阶段 1 主动从 Flask 切到了 SPA。
  - **转化稳定率 ≥ 60%**：切到 SPA 的用户中，60% 没有点"回到经典版"回跳。
  - **SPA 错误率 < 0.5%**：该 SPA 页面的 JS 错误率 / API 失败率低于阈值。
- Flask 该页 302 跳转到 SPA URL。
- SPA "回到经典版"链接保留（兜底，遇问题可回退）。

### 阶段 3：301 永久切换
- 阶段 2 一周内无重大回滚 → Flask 该页 301 永久重定向。
- SPA "回到经典版"链接**移除**（不再保留兜底）。
- Flask 对应 Jinja 模板**保留在 `templates/` 归档目录**（不删，按设计文档第 11 节决定）。

### M0 预埋（任务 0.5 新加）
- Jinja base 模板加 switcher 注入点（Jinja 块语法），M1+ 每页只需填一行 URL 即可启用。
- SPA Layout 组件加回跳口注入点（React Context + 配置），M1+ 每页只需 wrap 一个 prop。
- 埋点工具就位：`/api/v1/telemetry/switcher` POST 端点 + 前端 SDK helper。

## 理由

1. **用户主动权**：阶段 1 让用户自己决定是否尝鲜，避免被动切换引发的投诉。
2. **数据驱动决策**：阶段 1 的主动切换率、转化稳定率、错误率是切阶段 2 / 阶段 3 的硬指标，避免拍脑袋。
3. **回退路径显式**：用户在阶段 1 / 阶段 2 都有"回到经典版"出口，降低尝鲜心理成本。
4. **机制可复用**：每个迁移页面都走相同的三阶段，M1/M2/M3 不必为不同页面发明不同灰度策略。
5. **M0 预埋避免重复工作**：基础设施一次性做好（base 模板注入点 + SPA 注入点 + 埋点端点），M1+ 每页只需 0.5h 即可启用 switcher。

## 后果

### 正面
- 用户主动切换信号清晰，可判断 SPA 新版是否真的更好。
- 阶段 1 暴露出来的 SPA 问题（错误率 / 主观差评）可在强切前修复。
- 三阶段流程标准化，M1/M2/M3 每页执行模式统一。
- 用户对"被切到新版"心理预期建立，301 强切时不会突兀。

### 负面
- M1/M2 每页工期 +0.5h（加 switcher 入口 + 埋点 + 测试）。
- M0 新增任务 0.5（switcher 基础设施预埋），M0 工期 +0.5 天（6 天 → 6.5 天）。
- 阶段 1 期间用户态分裂——一部分在 Flask、一部分在 SPA——两套 UI 都要保持可用，调试 / 客服回应成本略增。
- 埋点数据要有人定期看 + 决策切阶段（建议每页有"灰度负责人"）。

### 注意：适用范围变更

本 ADR 最初设计为"仅适用于 M3+ 新迁移页面"，后经项目决策变更为"**所有迁移页面（含 M1+M2 已迁的 36+ 页）均走 switcher 灰度**"。这意味着：

- M1+M2 已迁的 36+ 页 302 redirect 必须回滚为 render_template + switcher 入口
- Group B（双轨并存页面）需加 switcher 链接（不需回滚，因为本来没 redirect）
- `/share/decision/<token>` 保留 SSR（ADR-0006），**不加 switcher**

详见 [B 方案执行计划](../../superpowers/plans/2026-06-21-rollback-plan-b.md)。

终态（M3 末）仍是"完全替换 Jinja，除 `/share/*` 外"。

## 实施清单

### M0 任务 0.5（新加，本 ADR 触发）
- [ ] Jinja base 模板加 switcher 注入点：`{% block spa_switcher %}{% endblock %}` 在 `<nav class="app-nav">` 内末尾
- [ ] SPA Layout 组件加回跳口注入点：通过 React Context 提供 `useSpaSwitcher()` hook，子页面 wrap 时可启用
- [ ] 埋点端点 `POST /api/v1/telemetry/switcher`：接受 `{event, page, user_id}`，写入 `instance/telemetry.jsonl`（轻量，无需数据库）
- [ ] 前端 SDK helper：`frontend/src/lib/switcher-telemetry.ts` 暴露 `trackSwitcherClick()` / `trackBackToClassic()`
- [ ] 单元测试：注入点存在、端点接受 POST、JSONL 写入正确
- [ ] 文档：`docs/spa-migration-runbook.md` 加"如何为新页面启用 switcher"小节

### M1+ 每页迁移（本 ADR 启用）
- [ ] Flask 旧版页面填写 `{% block spa_switcher %}<a href="/app/<page>">试试新版 →</a>{% endblock %}`
- [ ] SPA 对应页面 `<Layout enableBackToClassic url="/<page>">...</Layout>`
- [ ] 埋点 dashboard 加该页统计（手动定期看 telemetry.jsonl 或导入 Excel）
- [ ] 灰度负责人按阶段 1/2/3 条件切换状态

### M3 末（本 ADR 收尾）
- [ ] 所有迁移完成的页面 switcher 入口清除
- [ ] SPA 所有"回到经典版"链接清除
- [ ] 埋点端点保留但归档（telemetry.jsonl 不再有新写入）
- [ ] Flask 旧版 Jinja 模板移到 `templates/_archive/`（按设计文档第 11 节）

## 替代方案为何被否

- **直接 302（原方案）**：用户被动切换，缺乏主动信号，不利于发现 SPA 体感问题。
- **永久双轨（解读 A）**：长期维护两套 UI 体系，成本翻倍，与"完全替换 Jinja"终态矛盾。
- **同 URL 不同版本（B-同路径不同 cookie）**：实现复杂，开发期调试痛苦，用户感知不清晰。

## 已知未决

- **埋点存储**：当前用 JSONL 文件，简单可靠。若 M2 末数据量超过 100k 条记录，考虑导入 SQLite 或 ClickHouse（写入 `data/`）。
- **灰度负责人角色**：建议在 M1 第一页迁移时明确——可以是产品负责人或开发者本人，需要每周看一次数据。
- **A/B test 严格度**：本 ADR 是"用户自选 + 阈值切换"风格，不是严格 A/B test（无对照组随机分配）。若需要严格 A/B，需要额外的 ADR 描述实验设计。
