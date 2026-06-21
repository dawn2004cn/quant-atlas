# ADR-0005: 已迁 11 个 SPA 页面补冒烟 E2E 覆盖

- **状态**：Accepted
- **日期**：2026-06-21
- **决策者**：项目负责人
- **关联里程碑**：M0（地基）
- **关联文档**：`docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md` §3（已迁页面清单）
- **依赖 ADR**：[0004](0004-playwright-ci-strategy.md)（Playwright CI 策略）

## 背景

项目当前已有 11 个页面迁到 React SPA：`/app/dashboard`、`/app/portfolio`、`/app/watchlist`、`/app/strategy`、`/app/backtest`、`/app/factor`、`/app/screener`、`/app/agent`、`/app/notes`、`/app/settings`、`/app/profile`。

这些页面在生产已运行一段时间，未出大故障，但**没有任何 E2E 覆盖**——纯靠开发者手动验证。

M1/M2/M3 迁移期会大量改动 shared store、API 客户端、layout 组件——这些改动可能间接破坏已迁页面。问题：M0 任务 7 要不要给这 11 页都补 Playwright case？

| 选项 | 工作量 | 风险 |
|---|---|---|
| A. 补（11 条冒烟 case） | M0 任务 7 工期 +5.5h（每页 30min） | M1+ 可放心改 shared 资源 |
| B. 不补（仅 5–10 条核心流） | 节省 5.5h | M1+ 改 shared 资源时无回归网，靠运气 |

## 决策

**采用 A：补 11 条冒烟 case**。

每条 case 范围最小化（"页面能加载 + 关键元素可见"），不测业务逻辑：

```
test('/app/dashboard loads', async ({ page }) => {
  await loginAs('test_user');
  await page.goto('/app/dashboard');
  await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
});
```

## 理由

1. **shared 资源风险高**：M1/M2 会大改 `frontend/src/api/`、`frontend/src/components/layout/`、shared store。这 11 页全都依赖这些 shared 模块——一次 shared 改动可能同时破坏多个页面。没有 E2E 守门会出现"我合并的 PR 把另外 3 个页面跑挂了我都不知道"。
2. **冒烟 case 成本低**：单页 30min 已包含写 case + 加 `data-testid` 到对应 React 组件。11 页 5.5h 一次性投入，后续维护成本接近零（不改业务测试，只测"能加载"）。
3. **CI 时间影响小**：11 条冒烟 + 5–10 条核心流 = 16–21 条总 case，并行 worker 跑约 5min，可接受。
4. **心理价值**：开发者迁移新页面时，看到 CI 全绿（包括已迁页面冒烟），心理负担明显降低，加速迁移节奏。

## 后果

### 正面
- M1+ 改 shared 模块时，11 页冒烟立即报警，回归即时可见。
- 11 页都被强制加 `data-testid`，提高了组件可测性（M1+ 新迁页面也会沿用这个习惯）。
- Playwright 套件覆盖率从"5–10 条核心流"扩展到"16–21 条 case"，反映项目真实形态。

### 负面
- M0 任务 7 工期从 1 天扩到 1.5 天（+5.5h）。
- 给 11 个 React 组件加 `data-testid` 是侵入式改动（虽然只是加属性，不改逻辑），合并时仍是修改这 11 个文件——会污染 commit history。
- 若 11 页中有任何一页本就有 bug 无法加载，会在 M0 暴露，M0 工期可能继续延长（属于"额外发现的债务"）。

### 中性
- "页面能加载"级别的 case 不能测业务正确性——这部分仍要靠开发者手动 / 5–10 条核心流 case 覆盖。

## 实施清单

- [ ] M0 任务 7：给 11 个 React 页面根组件加 `data-testid="<page-name>-root"`
- [ ] M0 任务 7：写 11 条冒烟 case，统一模板，共享 `loginAs()` helper
- [ ] M0 任务 7：跑通后纳入 `tests/e2e/playwright.config.ts` 默认 suite
- [ ] M0 任务 8：CI `e2e` job 包含全部 16–21 条 case

## 替代方案为何被否

- **B. 不补**：M1+ 改 shared 模块时无回归网。"省 5.5h 但承担接下来 2 个里程碑的回归恐惧"显然不划算。
