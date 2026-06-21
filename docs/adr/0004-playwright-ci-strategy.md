# ADR-0004: Playwright 同时跑在 CI 与本地

- **状态**：Accepted
- **日期**：2026-06-21
- **决策者**：项目负责人
- **关联里程碑**：M0（地基）
- **关联文档**：`docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md` §10（测试策略）

## 背景

Flask → SPA 迁移过程中，每迁一页都可能影响其它已迁或未迁的页面（共享 layout、shared store、API 客户端）。需要一个稳定的 E2E 防线来减少"改 A 页面把 B 页面跑挂"的恐惧。

候选方案：

| 选项 | CI 上行为 | 本地行为 |
|---|---|---|
| A. CI + 本地都跑 | PR 必过 E2E job | 开发者可手动 `npx playwright test` |
| B. 仅本地跑 | CI 不跑 E2E（只跑 pytest + lint） | 开发者完全负责手动跑 |

## 决策

**采用 A：CI 与本地都跑**。

具体配置：

1. **CI**：`.github/workflows/ci.yml` 新增 `e2e` job，headless Chromium 跑全套 Playwright case，PR 必过。
2. **本地**：开发者用 `cd tests/e2e && npx playwright test` 跑，或 `npx playwright test --ui` 调试。
3. **Artifact**：CI 失败时上传 trace.zip 与截图到 GitHub Actions Artifacts（保留 30d）便于调试。

## 理由

1. **SPA 迁移核心保险**：M1/M2/M3 每迁一页都有"我这次改动会不会把另一个未迁页面跑挂"的恐惧。没有 CI 守门会越迁越虚，最终积累大量"我不确定它还能不能用"的回归隐患。
2. **本地跑必须保留**：CI 跑 5–10min 才反馈，开发期需要本地秒级反馈调试。
3. **GitHub Actions 免费额度足够**：项目当前 CI 总耗时未超过免费额度，加 5min E2E 不会触顶。
4. **强制约束开发纪律**：CI 必过 = PR 不能合并 = 开发者必须先在本地把 E2E 跑通 = E2E 测试始终保持可运行状态。

## 后果

### 正面
- 每个 PR 都有 E2E 兜底，迁移期心理负担显著降低。
- E2E case 不会"写完就坏"——CI 强制持续可运行。
- CI 失败 artifacts 自动保存 trace + 截图，远程调试方便。

### 负面
- CI 总耗时 +5min（headless Chromium 跑 16–21 条 case）。
- Playwright 浏览器二进制需要 CI 缓存（首次拉取 ~150MB），需要在 ci.yml 配 cache step。
- 测试 flaky 会成为 PR merge 阻碍，必须保证 E2E case 是 deterministic 的（条件等待、不用 `sleep`、用 `data-testid` 选择器）。

### 中性
- 本地跑 headed mode 调试比 CI 失败后下载 trace 体验更好，开发者主要会用本地跑。

## 实施清单

- [ ] M0 任务 7：建 `tests/e2e/` 目录，含独立 `package.json`、`playwright.config.ts`、`.gitignore`
- [ ] M0 任务 7：写 5–10 条核心流 case：登录、刷新 token、看盘、下单、回测、AI 推理、SSE 流式
- [ ] M0 任务 7：写 11 条已迁 SPA 页面冒烟 case（ADR-0005 要求）
- [ ] M0 任务 7：所有 case 使用 `data-testid` 选择器，禁止用 css class / text content（脆弱）
- [ ] M0 任务 7：所有等待用 `expect(locator).toBeVisible()` 而非 `page.waitForTimeout()`（避免 flaky）
- [ ] M0 任务 8：`.github/workflows/ci.yml` 新增 `e2e` job：checkout → cache playwright → install → run → upload artifacts on failure
- [ ] M0 任务 8：E2E job 与 lint / test job 并行，不串行（缩短总反馈时间）

## 替代方案为何被否

- **B. 仅本地跑**：开发者会逐渐忘记跑 E2E，case 慢慢就过时不可用了。SPA 迁移期心理预期是"CI 全绿 = 可合并"，少了这道防线会让迁移恐惧加重。
