# Frontend Baseline

## Scope

Static baseline scan over `app/presentation/web/templates/*.html` on 2026-06-15.

Lighthouse was not run because the repository has no frontend test runner or Lighthouse script. The current baseline is a structural scan that identifies repeatable cleanup targets before any design-system rewrite.

## Static scan results

| Metric | Value |
|---|---:|
| Top-level HTML templates | 87 |
| Templates extending `base.html` | 80 |
| Templates with inline `<style>` | 75 |
| Templates with inline `<script>` | 82 |
| Templates with `lang="zh-CN"` | 7 |
| Templates with non-`zh-CN` `lang` | 0 |
| Templates missing `lang` | 80 |

The 80 templates missing `lang` are child templates that extend `base.html`; the effective document language is inherited from `base.html`, which already declares `lang="zh-CN"`.

## Repeated color tokens

Most repeated colors found in top-level templates:

| Color | Occurrences |
|---|---:|
| `#fff` | 136 |
| `#10b981` | 51 |
| `#f59e0b` | 49 |
| `#ef4444` | 44 |
| `#3b82f6` | 32 |
| `#94a3b8` | 28 |
| `#64748b` | 25 |
| `#e2e8f0` | 25 |
| `#6366f1` | 23 |
| `#059669` | 21 |
| `#7c3aed` | 20 |
| `#1e293b` | 19 |

## Baseline design tokens

Proposed initial token set for the next frontend cleanup pass:

```css
:root {
  --color-bg: #ffffff;
  --color-surface: #f8fafc;
  --color-primary: #3b82f6;
  --color-primary-dark: #059669;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-purple: #7c3aed;
  --color-indigo: #6366f1;
  --color-slate-500: #64748b;
  --color-slate-400: #94a3b8;
  --color-slate-200: #e2e8f0;
  --color-slate-800: #1e293b;
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --shadow-card: 0 4px 20px rgba(15, 23, 42, 0.12);
}
```

## Cleanup priorities

1. Child templates that extend `base.html` inherit `lang="zh-CN"` from the layout.
2. Standalone templates must declare `lang="zh-CN"` explicitly.
3. Move repeated inline styles into shared component CSS or reusable partials.
3. Move repeated inline scripts into small shared helpers only when pages have common patterns.
4. Standardize cards, badges, tables, forms, and empty states before touching charts.
5. Add Lighthouse scripts only after the static cleanup targets are stable.

## Immediate follow-up already applied

- `strategy_wizard.html` now uses `lang="zh-CN"`, a small AJAX error wrapper, escaped rendering, and visible toast messages.
- `data_lake_health.html` now inherits `lang="zh-CN"` from `base.html`.
- All top-level standalone templates now have an effective `zh-CN` language either directly or via `base.html`.
