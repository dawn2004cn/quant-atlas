# SPA Migration Runbook

## 1. 如何为新页面启用 Switcher

### Step 1: Flask 端（Jinja 模板）

在迁移页面的 Jinja 模板中添加 `{% block spa_switcher %}` 覆写：

```jinja
{% extends "base.html" %}

{% block spa_switcher %}
<a href="/app/dashboard"
   class="nav-pill nav-pill--spa-switcher"
   onclick="window.trackSwitcherClick && window.trackSwitcherClick('dashboard')">
  试试新版 →
</a>
{% endblock %}
```

- `base.html` 已包含空的 `{% block spa_switcher %}{% endblock %}`，未覆写的页面不会显示任何内容。
- `window.trackSwitcherClick()` 由 `frontend/src/lib/switcher-telemetry.ts` 在 SPA 加载时全局注入。Flask 页面需在 base.html 的 `{% block core_scripts %}` 之后引用或内联该 SDK（或在 switcher 链接的 `onclick` 中直接写 `fetch('/api/v1/telemetry/switcher', ...)` 作为降级方案）。

### Step 2: SPA 端（React 组件）

在对应 SPA 页面的 Layout 调用处启用回跳链接：

```tsx
<Layout enableBackToClassic backToClassicUrl="/daily-workbench">
  <DashboardPage />
</Layout>
```

- `enableBackToClassic` 为 `true` 时，Layout 右下角显示 "← 回到经典版" 链接。
- `backToClassicUrl` 指向对应 Flask 页面路径，默认为 `"/"`。

---

## 2. 如何查看埋点数据

埋点数据写入 `instance/telemetry.jsonl`，每行一条 JSON 记录。

### 查看最近 10 条事件

```bash
tail -10 instance/telemetry.jsonl | jq .
```

### 统计各事件类型数量

```bash
cat instance/telemetry.jsonl | jq -s 'group_by(.event) | map({event: .[0].event, count: length})'
```

### 统计某页面的切换率

```bash
cat instance/telemetry.jsonl | jq -s '
  group_by(.page) | map({
    page: .[0].page,
    switch_to_spa: (map(select(.event == "switch_to_spa")) | length),
    back_to_classic: (map(select(.event == "back_to_classic")) | length)
  })'
```

### 按日期统计

```bash
cat instance/telemetry.jsonl | jq -s '
  group_by(.timestamp[:10]) | map({
    date: .[0].timestamp[:10],
    total: length,
    switch_to_spa: (map(select(.event == "switch_to_spa")) | length),
    back_to_classic: (map(select(.event == "back_to_classic")) | length)
  })'
```

---

## 3. 三阶段切换条件

摘自 [ADR-0007](../adr/0007-switcher-grayscale-mechanism.md)。

### 阶段 1：Switcher 入口（1–2 周）

- Flask 旧版页面 `<nav>` 内显示"试试新版 →"链接
- SPA 对应页面右下角显示"回到经典版 ←"
- 默认仍在 Flask，用户可主动切换
- 埋点：switcher 点击数、回跳数、SPA 页面停留时长

### 阶段 2：302 渐进强切（1 周）

满足以下**任一条件**可进入阶段 2：

| 指标 | 阈值 |
|------|------|
| 主动切换率 | ≥ 30% |
| 转化稳定率 | ≥ 60%（切到 SPA 的用户没回跳） |
| SPA 错误率 | < 0.5% |

- Flask 该页 302 跳转到 SPA URL
- "回到经典版"链接保留（兜底回退）

### 阶段 3：301 永久切换

- 阶段 2 一周内无重大回滚 → Flask 该页 301 永久重定向
- "回到经典版"链接移除
- Flask 对应 Jinja 模板保留在 `templates/_archive/`