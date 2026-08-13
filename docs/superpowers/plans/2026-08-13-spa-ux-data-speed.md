# SPA UX data / speed / partial refresh

> Implement task-by-task. Checkboxes track progress.

**Goal:** 操盘台有数据、切换局部刷新、沿用性能快赢。

**Architecture:** Layout 常驻 + KeepAlive 内容区；后端空面板演示填充。

**Tech Stack:** React Router 7, SWR, Flask workbench snapshot

## Global Constraints

- 演示数据必须标明，不得写成实盘
- 导航只用 SPA Link/NavLink
- 不引入新的 keep-alive 库

---

### Task 1: display fallback + SPA shell

- [x] Tests
- [x] Implementation
