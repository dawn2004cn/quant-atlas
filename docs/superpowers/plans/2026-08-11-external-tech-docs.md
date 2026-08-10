# 对外技术文档门户 Implementation Plan

> **For agentic workers:** Implement task-by-task; checkboxes track progress.

**Goal:** 产出 `docs/public/` 对外门户，并更新根 README / `docs/README.md`。

**Architecture:** 精简可承诺文档集；内部 plan/审计不进导航。

**Tech Stack:** Markdown only

## Global Constraints

- 中文为主，术语保留英文
- 无密钥明文；不删历史文件；不上 MkDocs
- 技术栈写 Flask + React SPA（`/app`）

---

### Task 1: 写出 `docs/public/` 八篇 + 双 README

**Files:**
- Create: `docs/public/README.md`, `01-overview.md` … `07-contributing.md`
- Modify: `README.md`, `docs/README.md`
- Update: design spec 验收勾选；`REFACTORING_LOG.md` 短条目

- [x] Write all public docs from codebase facts
- [x] Update READMEs
- [x] Commit + push + update PR

**验证：** 人工检查链接；`ls docs/public | wc -l` ≥ 8
