# 性能快赢设计：SPA 首屏 + 热路径 API

> 日期：2026-08-11  
> 状态：待用户审阅 spec  
> 范围：双轨快赢（前端加载 + API 响应），不做大重构

## 1. 背景与目标

Quant Atlas 已具备路由级 `lazy()`、Vite 分包、Gzip 与静态 `max-age`，但仍存在：

- 图表三库打入同一 `charts` chunk，任一图表页拖全量
- Dashboard 默认真时连接 + workbench 轮询，抢占首屏
- `StockDetail` 同步进主包；壳层 `AiAssistantDrawer` 常驻
- 全局 JSON `Cache-Control: max-age=300` 过粗，动态接口易误伤、可缓存接口又不够精准

**目标（可验收）**

| 维度 | 指标 |
|------|------|
| 前端 | `echarts` / `recharts` / `lightweight-charts` 分独立 chunk；StockDetail 懒加载 |
| 首屏 | Dashboard 默认不连 WS；助手抽屉点击再挂载 |
| API | `daily_workbench` 同参短 TTL 缓存可证；`strategic-features` 私有短/中缓存 |
| 安全 | 行情类动态 GET 不为 `public, max-age=300` |

**明确不做**

- 不删除 90+ Jinja、不做全站 SSR、不换框架
- 不重写 CompositeEngine / 分钟引擎
- 不引入新的大型依赖（除非测试所需）

## 2. 方案选择

采用 brainstorming 确认的 **方案 C：双轨快赢**（前端瘦身 + API 缓存细化），拒绝「只做前端」或「只做 API」。

## 3. 前端设计

### 3.1 Vite 分包

文件：`frontend/vite.config.ts`

将现有：

```ts
charts: ["lightweight-charts", "echarts", "recharts"]
```

改为按库拆分，例如：

```ts
"chart-lw": ["lightweight-charts"],
"chart-echarts": ["echarts"],
"chart-recharts": ["recharts"],
```

保持 `vendor` / `i18n` / `swr` / `socketio` 不变。

### 3.2 路由懒加载

文件：`frontend/src/App.tsx`

- `StockDetailPage`：改为 `lazy(() => import(...))`，与其他业务页一致
- `LoginPage` / `DashboardPage`：保持同步（登录与默认落地页），避免首跳多一次瀑布

### 3.3 Dashboard 实时与 SWR

文件：`frontend/src/pages/Dashboard.tsx`

- `useRealtime(false)` 默认；提供显式开关或「连接实时」按钮后再 `true`
- `useSWR`：`revalidateOnFocus: false`，`dedupingInterval: 10_000`（或与 refreshInterval 协调）

### 3.4 壳层懒挂载

文件：`frontend/src/components/Layout.tsx`

- `AiAssistantDrawer`：仅在用户打开助手时再 `lazy` + `Suspense` 挂载（或条件渲染）

### 3.5 可选（同一迭代若有余力）

- 主路径导航 `onMouseEnter` / `onFocus` 预取对应 lazy chunk（不阻塞首屏）

## 4. 后端设计

### 4.1 修正全局 API 缓存策略

文件：`app/infrastructure/response_optimizer.py`

- **默认**：对 `/api/` JSON 响应不自动加 `public, max-age=300`
- **白名单**（示例）：
  - `GET /api/v1/platform/strategic-features` → `private, max-age=600`
  - 其他可缓存只读资源显式在路由或服务层设置
- 静态资源路径保持现有 `static_files.py` 逻辑；若托管 `frontend/dist` hashed 资产，使用 `public, max-age=31536000, immutable`

### 4.2 daily_workbench 短 TTL 缓存

文件建议：

- `app/modules/strategy/services/analytics/daily_workbench_service.py`（或现有等价路径）
- 使用已有 `MemoryCache` / `app.infrastructure.memory_cache`，键：`workbench:{market}:{user_id或anon}:{limit}`
- TTL：30–60 秒
- 缓存命中写 debug 日志或 `meta.cache = "hit"|"miss"`（便于测试与观测，不破坏既有字段）

### 4.3 strategic-features 缓存

- 路由或服务层对结果做 5–15 分钟进程内缓存
- 响应头：`Cache-Control: private, max-age=600`

## 5. 测试与验证

| 项 | 方式 |
|----|------|
| Vite chunks | `npm run build` 后 `dist/assets` 出现分离的 chart-* 文件；无合并三库大 chunk |
| StockDetail lazy | 构建产物中 StockDetail 独立 chunk；App 主入口不再静态 import 该页 |
| workbench 缓存 | 单测：同参连续两次调用，第二次命中（mock 时钟或 spy 底层） |
| Cache-Control | 单测：普通 API JSON 无错误 `public, max-age=300`；白名单路径符合预期 |
| 回归 | 既有 presentation / smoke 相关子集不红 |

## 6. 文档与日志

- 实现完成后在 `REFACTORING_LOG.md` 追加「2026-08-11 性能快赢」条目
- 本文件为权威设计；实现计划见后续 `docs/superpowers/plans/2026-08-11-perf-fast-win.md`

## 7. 风险与回滚

| 风险 | 缓解 |
|------|------|
| workbench 缓存导致数据略旧 | TTL ≤ 60s；与前端 refreshInterval 对齐 |
| 拆 chunk 后首访图表页多一次请求 | 可接受；总下载量下降 |
| Dashboard 默认无 WS | UI 提供一键开启，避免功能回退误解 |

回滚：按文件还原 Vite/Dashboard/response_optimizer/workbench 缓存即可。

## 8. 验收清单

- [ ] 设计已获用户确认（本文件）
- [ ] 实现计划已写并按 TDD 执行
- [ ] 前端构建证明 charts 分家 + StockDetail lazy
- [ ] workbench / cache-control 单测通过
- [ ] `REFACTORING_LOG.md` 已更新
