# 前端架构重构方案（v3）

> 目标：把 Dependency Injector 和状态管理完全隐藏在 UI 背后，让普通交易员/策略研究员也能流畅使用。

---

## 1. 现状诊断

| 维度 | 当前状态 | 问题 |
|------|----------|------|
| **框架** | 纯 Jinja2 + jQuery | 无组件化，inline script 散落各处 |
| **路由** | 服务端 MPA（全页刷新） | 无 SPA，跳转即白屏 |
| **API 调用** |  scattered `$.getJSON` / `fetch` | 无统一错误处理，无认证头管理 |
| **状态管理** | localStorage + CustomEvent | 无集中 store，跨页面状态丢失 |
| **图表** | 4 种库（ECharts/Lightweight/Three/React Flow） | 无统一抽象，每页重复初始化 |
| **移动端** | 基础响应式 CSS | `user-scalable=no` 阻断无障碍 |
| **i18n** | 部分支持 zh/en | inline JS 大量硬编码中文 |

---

## 2. 重构目标

```
Before:  页面 → 散落 JS → 直接 fetch → 解析 JSON → 更新 DOM
After:   页面 → QCApi → 统一错误 → State Bus → 组件渲染
```

---

## 3. 技术选型

| 方案 | 优势 | 风险 | 推荐 |
|------|------|------|------|
| **A. 渐进增强（推荐）** | 零破坏，逐步替换 | 周期长 | ✅ |
| **B. 全量 SPA 迁移** | 现代化体验 | 高风险，影响所有页面 | ❌ |
| **C. Alpine.js 轻量组件化** | 低学习成本，渐进式 | 生态小 | 备选 |

**决策：方案 A** — 在现有 MPA 架构上叠加统一层。

---

## 4. 分层设计

```
┌─────────────────────────────────────────┐
│  Presentation Layer (Jinja2 + 新 JS)     │
│  ├── pages/ (Flask routes)              │
│  ├── components/ (Web Components)       │
│  └── layouts/ (base.html 扩展)          │
├─────────────────────────────────────────┤
│  Client Infrastructure Layer (NEW)      │
│  ├── api_client.js      → 统一 API      │
│  ├── state_bus.js        → 事件状态      │
│  ├── chart_service.js    → 图表抽象      │
│  └── error_banner.js     → 错误标准化    │
├─────────────────────────────────────────┤
│  Existing jQuery / vanilla JS           │
│  (逐步迁移，不强制一次性重写)             │
└─────────────────────────────────────────┘
```

---

## 5. 实施路线图

### Phase 1：基础设施层（2 周）— 已完成

- [x] `static/js/api_client.js` — 统一 fetch 封装
- [x] `static/js/focus_context_enhancer.js` — Focus 联动增强
- [ ] `static/js/state_bus.js` — 全局事件总线
- [ ] `static/js/chart_service.js` — 图表统一接口

### Phase 2：组件化起步（2 周）

**目标**：将高频 partials 转为 Web Component。

| 现有 Partial | 组件化方案 | 优先级 |
|--------------|-----------|--------|
| `global_focus_bar.html` | `<qa-focus-bar>` | 高 |
| `health_banner.html` | `<qa-health-banner>` | 高 |
| `decision_brief_strip.html` | `<qa-decision-brief>` | 中 |
| `team_context_bar.html` | `<qa-team-bar>` | 中 |

```javascript
// 示例：Web Component 封装
class QAFocusBar extends HTMLElement { ... }
customElements.define('qa-focus-bar', QAFocusBar);
```

**优势**：不破坏现有 Jinja2 模板，渐进替换。

### Phase 3：状态管理统一（1 周）

```javascript
// state_bus.js 设计
QCStateBus = {
  subscribe(key, callback),
  publish(key, value),
  getState(key),
  hydrate(pageContext),  // 服务端注入初始状态
}
```

**应用场景**：
- user_preferences → localStorage + server sync
- focus_context → 已有 QAFocusContext，纳入 bus
- task_progress → 实时更新
- team_context → 跨标签同步

### Phase 4：图表服务抽象（1 周）

```javascript
// chart_service.js 设计
QCChartService = {
  createKline(container, data),      // Lightweight Charts
  createEquity(container, data),     // ECharts
  create3D(container, data),         // Three.js
  createFlow(container, nodes),      // React Flow
  destroyAll(),                       // 页面卸载清理
}
```

**解决痛点**：当前每页独立初始化图表，切换页面时内存泄漏 + 重复加载库文件。

### Phase 5：移动端体验（1 周）

- [ ] `base.html` 移除 `user-scalable=no`
- [ ] `.qc-mobile-lane` 升级为底部 Tab Bar
- [ ] 所有 `:hover` 补 `:active`
- [ ] 按钮最小 44×44px

### Phase 6：i18n 补全（1 周）

- [ ] 扫描 inline JS 硬编码中文 → 提取到 `locales/`
- [ ] 提供 `t_js(key)` 函数供 `<script>` 调用

---

## 6. 迁移策略：Strangler Fig 模式

```
         ┌──────────────┐
 请求 ──► │  Flask MPA   │
         └──────┬───────┘
                │
         ┌──────▼───────┐
         │  New JS Layer │ ← 逐步接管
         │  (api_client) │
         └──────┬───────┘
                │
         ┌──────▼───────┐
         │  Components   │ ← 长期目标
         └──────────────┘
```

**规则**：
1. 新页面默认用 `QCApi` + 组件化
2. 旧页面不动，除非需要修改
3. 每季度迁移 3-5 个高频页面

---

## 7. 验证标准

| 指标 | 当前 | 目标 |
|------|------|------|
| API 调用方式 | 15+ 种散落模式 | 1 种（QCApi） |
| 页面首屏 JS 加载 | ~200KB (jQuery + 各页面独立) | <150KB (tree-shaking) |
| 图表内存泄漏 | 切换即泄漏 | 页面卸载自动 destroy |
| 移动端可用性 | 基础响应式 | 44px 触控目标 + 可缩放 |
| 错误处理 | Generic 500 | Actionable hint + retry |

---

## 8. 推荐下一步

| 选项 | 优先级 | 说明 |
|------|--------|------|
| **1. state_bus.js** | 🔴 高 | 为后续所有组件提供状态基础 |
| **2. chart_service.js** | 🟡 中 | 消除内存泄漏，统一图表 API |
| **3. 选 1 个页面做组件化试点** | 🟡 中 | 如 `global_focus_bar` → `<qa-focus-bar>` |
| **4. 迁移 Sprint（全量）** | ⚪ 低 | 需 CI 全绿后启动 |

---

**结论**：前端架构不需要推倒重来。在现有 MPA 上叠加 `api_client` + `state_bus` + `chart_service` 三层基础设施，即可在不破坏业务的前提下，为未来 SPA 迁移铺平道路。
