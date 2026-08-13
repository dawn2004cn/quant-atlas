# 性能快赢 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or implement task-by-task with TDD. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 双轨快赢——SPA 首屏更轻、热路径 API 更快（Cache-Control 白名单 + workbench 短 TTL）。

**Architecture:** 后端修正 `response_optimizer` 默认不缓存 `/api/` JSON，白名单 `strategic-features`；`DailyWorkbenchService.build_snapshot` 用 `MemoryCache` 30–60s。前端拆 Vite 图表 chunk、`StockDetail` lazy、Dashboard 默认关 WS、助手抽屉懒挂载。

**Tech Stack:** Flask, MemoryCache, Vite, React lazy/Suspense, SWR, pytest

## Global Constraints

- 不删 Jinja、不做 SSR、不换框架、不重写 CompositeEngine
- 不引入大型新依赖
- 行情类动态 GET 不得 `public, max-age=300`
- workbench TTL ≤ 60s

---

### Task 1: API Cache-Control 白名单

**Files:**
- Modify: `app/infrastructure/response_optimizer.py`
- Test: `tests/infrastructure/test_response_optimizer_cache.py`

**Interfaces:**
- Produces: `_is_cacheable(response)` 对 `/api/` 默认 False；路径含 `strategic-features` 时路由可设 header（见 Task 3）或 optimizer 白名单设 `private, max-age=600`

- [ ] **Step 1: Write failing tests** for default API no public max-age=300 and whitelist behavior
- [ ] **Step 2: Implement optimizer changes**
- [ ] **Step 3: Pass tests + commit**

### Task 2: daily_workbench 短 TTL 缓存

**Files:**
- Modify: `app/modules/strategy/services/analytics/daily_workbench_service.py`
- Test: `tests/modules/strategy/test_daily_workbench_cache.py`

**Interfaces:**
- Consumes: `MemoryCache`
- Produces: `build_snapshot(...)` 同参第二次走缓存；可选在返回 DTO/`model_dump` 侧不破坏契约（测试用 spy 计调用次数）

- [ ] **Step 1: Failing test** — mock `_safe_panorama` 只应被调用一次
- [ ] **Step 2: Inject MemoryCache(ttl=45) into service**
- [ ] **Step 3: Pass + commit**

### Task 3: strategic-features 响应头 + 进程缓存

**Files:**
- Modify: `app/presentation/api/routes_v1_platform.py`
- Test: extend `tests/infrastructure/test_response_optimizer_cache.py` or `tests/presentation/test_platform_features_cache.py`

- [ ] **Step 1–3:** private max-age=600 + 进程内 600s 缓存 flags dict

### Task 4: 前端 Vite + App + Dashboard + Layout

**Files:**
- Modify: `frontend/vite.config.ts`, `frontend/src/App.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/Layout.tsx`

- [ ] Split chart chunks
- [ ] Lazy StockDetail
- [ ] Dashboard realtime off by default + toggle
- [ ] Lazy AiAssistantDrawer on open
- [ ] `npm run build` verify chart-* assets if node available

### Task 5: REFACTORING_LOG + 更新 spec 验收勾选 + push

---

**Spec coverage:** 3.1–3.4, 4.1–4.3, 5–6 均有任务；3.5 prefetch 可选跳过（YAGNI）。
