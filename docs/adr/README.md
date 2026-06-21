# Architecture Decision Records (ADR)

本目录存放 quant-atlas 项目的架构决策记录，遵循 [ADR](https://adr.github.io/) 标准格式。

## 为什么写 ADR

每一个对系统结构、依赖、技术栈、跨模块约定的改动，都应有一份 ADR：
- 把决策的**上下文**写下来，不只是"我们用什么"，更是"为什么是这个而不是那个"。
- 让 6 个月后的自己 / 新人 / AI 助手能理解决策背景。
- 替代方案显式记录，避免"我们当时怎么没想到"这种事后诸葛亮。

## 状态

- **Proposed**：草案，待评审
- **Accepted**：已决议，正在执行
- **Superseded**：被后续 ADR 取代（同时在标题标注被哪个 ADR 取代）
- **Deprecated**：决策不再有效但保留历史

## 索引

### M0（Flask → SPA 迁移地基期，2026-06-21）

| 编号 | 标题 | 状态 | 摘要 |
|---|---|---|---|
| [0001](0001-jwt-algorithm.md) | JWT 签名算法选用 RS256 | Accepted | 公私钥分离，便于 Flutter / 网关独立验签 |
| [0002](0002-openapi-tooling.md) | OpenAPI 工具选用 apispec | Accepted | docstring YAML 渐进式接入，零侵入 |
| [0003](0003-jwt-refresh-strategy.md) | JWT 滑动续期 + Refresh Token Rotation | Accepted | 活跃用户永不掉线 + 重放检测 + 90d 绝对上限 |
| [0004](0004-playwright-ci-strategy.md) | Playwright 同时跑在 CI 与本地 | Accepted | PR 必过 E2E，迁移期回归防线 |
| [0005](0005-existing-spa-pages-coverage.md) | 已迁 11 个 SPA 页面补冒烟 E2E | Accepted | 16–21 条 case，迁移期保护 shared 资源 |
| [0006](0006-public-share-ssr-exception.md) | `/share/*` 永久保留 Jinja SSR | Accepted | 唯一刻意保留的 SSR 出口，SEO + 首屏优先 |

## 写作规范

每份 ADR 包含以下章节：

1. **元数据**：状态、日期、决策者、关联里程碑、关联文档、依赖 ADR
2. **背景**：问题是什么、候选方案对比表
3. **决策**：用一句话说清最终选择
4. **理由**：1–4 条核心理由，每条 1–3 句
5. **后果**：正面、负面、中性影响
6. **实施清单**：可勾选的 todo，对应到具体任务
7. **替代方案为何被否**：把候选方案逐个解释为何不选

## 写新 ADR 的流程

1. 复制最相近的现有 ADR 作为模板
2. 编号递增（4 位数字，零填充）
3. 状态先设 `Proposed`，评审通过后改 `Accepted`
4. 提交时 commit message 用 `docs(adr): NNNN <title>`
5. 在本 README 索引里加一行

## 何时改 ADR

ADR **不可改写历史决策**。如果决策变更：
1. 写一份新 ADR 描述新决策
2. 在新 ADR 元数据中标注 `Supersedes: ADR-NNNN`
3. 把原 ADR 状态改为 `Superseded by ADR-MMMM`
4. 原 ADR 内容保持不变（保留历史）
