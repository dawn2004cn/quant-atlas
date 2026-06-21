# B 方案执行计划：回滚 36+ 页 302 redirect 到 switcher 灰度

> **前置文档**: [页面全景清单](2026-06-21-flask-spa-page-inventory.md)
> **设计依据**: [ADR-0007](../../adr/0007-switcher-grayscale-mechanism.md)
> **状态**: 已确认

---

## 执行顺序

### 前置：M0 任务 0.5（switcher 基础设施）

在 M0 计划中已定义。必须先完成才能开始回滚。

- `base.html` 加 `{% block spa_switcher %}{% endblock %}` 注入点
- `Layout.tsx` 加 `enableBackToClassic` / `backToClassicUrl` prop
- `POST /api/v1/telemetry/switcher` 埋点端点
- `frontend/src/lib/switcher-telemetry.ts` 前端 SDK
- `tests/unit/test_switcher_telemetry.py` 单元测试

### B-1：预验证 Jinja 模板可渲染性（0.5 天）

逐个检查 Group A 38+6 页对应的 Jinja 模板：
1. 确认模板文件存在于 `templates/` 目录
2. 快速烟测：`curl localhost:5000/<route>` 是否返回 200（或至少 302/redirect 被改回后能渲染）
3. 标记"stale"模板（context 变量缺失、import 失效等）
4. 修复 stale 模板

### B-2：回滚 Group A 路由（2 天）

每页操作：
1. `pages_*.py` 中把 `return redirect("/app/...", code=302)` 改回 `return render_template("X.html", ...)`
2. 对应 Jinja 模板加 `{% block spa_switcher %}<a href="/app/X">试试新版 →</a>{% endblock %}`
3. 对应 SPA 页面 `<Layout enableBackToClassic backToClassicUrl="/X">...</Layout>`

**特殊处理**：
- `/share/decision/<token>`：恢复 `render_template("decision_snapshot_public.html")`，**不加** switcher（ADR-0006）
- `/swarm-designer/flow`：与 `/swarm-designer` 指向同一 SPA，两个路由都改回 render_template，只加一个 switcher 块
- f-string 动态路由（5 个含 `<id>` 参数的）：改回 render_template 时保留路径参数

### B-3：Group B 加 switcher 链接（0.5 天）

对约 12 个双轨并存页面（Flask 仍 render_template + SPA 同时存在）：
1. 在 Jinja 模板加 `{% block spa_switcher %}` 块指向 SPA 版本
2. 在 SPA 页面加 `enableBackToClassic` prop
3. **不改路由**（因本来就没 redirect）

### B-4：清理死代码（0.1 天）

1. `spa_redirects.py`：删除或标记 `# DEPRECATED: never registered, redirects are in pages_*.py`
2. 检查 bootstrap / `__init__.py` 是否有对 `register_spa_redirects` 的引用（预期无）

### B-5：更新文档（0.2 天）

1. `REFACTORING_LOG.md` 加条目
2. 本计划文件标记为完成
3. ADR-0007 适用范围更新

---

## 验证清单

- [ ] `python -c "import app"` 不报错（所有路由注册正常）
- [ ] 38+6 个 Group A 路由不再返回 302，而是返回 200 + Jinja HTML
- [ ] 每个 Jinja 页面右上角有"试试新版 →"链接，点击跳到对应 `/app/` 页面
- [ ] 每个 SPA 页面右下角有"回到经典版 ←"链接，点击跳回 Flask
- [ ] `/share/decision/<valid_token>` 返回 Jinja HTML（不是 redirect）
- [ ] `POST /api/v1/telemetry/switcher` 接受埋点并写入 JSONL
- [ ] `spa_redirects.py` 已删除或标记 DEPRECATED