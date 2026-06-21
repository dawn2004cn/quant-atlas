# 双主题 UI 验收清单

> 对应 `docs/UI_CSS_MIGRATION_PLAN.md` DoD 最后一项。  
> 在 **日间（light）** 与 **夜间（dark）** 各走查一次，勾选通过项。

## 准备

- [ ] 本地启动：`FLASK_APP=app bootstrap` 或项目既有 dev 命令，访问 `http://127.0.0.1:5000`
- [ ] 主题切换：顶栏 / 用户设置 / `localStorage` 键（与 `design-tokens.css` `[data-theme="dark"]` 一致）
- [ ] 浏览器：Chrome 或 Edge，宽度 1440px + 375px 各测一次

## 路径 1 — 导航壳（base.html）

| 检查项 | Light | Dark |
|--------|-------|------|
| 顶栏 `app-shell` 背景/边框无错位 | ☐ | ☐ |
| 下拉菜单可读（对比度、hover） | ☐ | ☐ |
| 移动端汉堡/折叠无横向滚动条 | ☐ | ☐ |

## 路径 2 — 操盘台（`/`，daily_workbench）

| 检查项 | Light | Dark |
|--------|-------|------|
| Hero / stat-grid 间距与 `workbench.css` 一致 | ☐ | ☐ |
| 卡片 `section-shell` 背景非纯白刺眼（dark） | ☐ | ☐ |
| 按钮 `btn-brand` / `btn-soft` 可辨、可点 | ☐ | ☐ |

## 路径 3 — 个股（`/stock/<symbol>`，如 600519）

| 检查项 | Light | Dark |
|--------|-------|------|
| 工作台分区（Copilot / 共振 / 证据）无重叠 | ☐ | ☐ |
| 图表区高度正常（`stock-detail.css`） | ☐ | ☐ |
| 动态组件（`:style` 共振条）在双主题下仍可读 | ☐ | ☐ |

## 路径 4 — 回测（`/backtest`）

| 检查项 | Light | Dark |
|--------|-------|------|
| 表单 `bt-form-panel` 对齐 | ☐ | ☐ |
| 成绩卡 `score-card` 正负色（pos/neg）正确 | ☐ | ☐ |
| 交易表滚动时表头不「透底」错乱 | ☐ | ☐ |

## 认证页（独立壳）

| 页面 | Light | Dark |
|------|-------|------|
| `/login`（`pages/auth.css`） | ☐ | N/A（auth 页固定浅色） |
| `/register` | ☐ | N/A |

## 回归命令（提交前）

```bash
python scripts/check_template_inline_styles.py
python -m pytest tests/smoke/test_template_inline_styles.py tests/smoke/test_dual_theme_pages.py -v
ruff check scripts/check_template_inline_styles.py
```

## 自动化结构验收（2026-06-20）

以下项由 `tests/smoke/test_dual_theme_pages.py` 覆盖，**不等同于**视觉走查：

| 检查项 | 自动化 |
|--------|--------|
| 四路径 HTTP 200 + 页级 CSS 链接 | ✅ |
| 壳层 `app-shell` / `themeToggle` / `toggleTheme` | ✅ |
| 模板响应无 `<style>` 块 | ✅ |
| `design-tokens` / `common.css` 双主题规则存在 | ✅ |
| 对比度、hover、移动端 375px、图表重叠 | ☐ 人工 |

---

| 角色 | 日期 | 结果 |
|------|------|------|
| 验收人 | | ☐ 通过 / ☐ 有问题（见 issue） |
