# P5 Strategy Wizard Frontend Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Strategy Wizard page resilient to API failures and align its basic language/UX with the Chinese platform without a full UI rewrite.

**Architecture:** Keep the page as a simple inline SPA. Add a small fetch wrapper, toast error display, non-HTML error rendering, and Chinese labels. Do not introduce a frontend framework or rebuild the page.

**Tech Stack:** HTML, CSS, vanilla JavaScript, Flask Jinja.

---

### Task 1: Harden Strategy Wizard AJAX flows

**Files:**
- Modify: `app/presentation/web/templates/strategy_wizard.html`

- [ ] **Step 1: Add global helpers**

```html
<div id="wizard-toast" class="wizard-toast" role="alert"></div>
<script>
  function showWizardMessage(message, isError = false) { ... }
  async function wizardFetch(url, options = {}) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error?.message || data.message || `HTTP ${res.status}`);
    return data;
  }
</script>
```

- [ ] **Step 2: Replace fetch calls**

```js
const data = await wizardFetch('/api/v1/strategy/wizard/templates');
```

- [ ] **Step 3: Add catch blocks**

```js
} catch (err) {
  showWizardMessage(err.message || '加载失败', true);
}
```

- [ ] **Step 4: Escape rendered strings**

```js
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({...}[ch]));
}
```

Use it for template names, descriptions, param keys, and preview text.

- [ ] **Step 5: Run syntax check**

```bash
python -m compileall -q app/presentation/web/templates/strategy_wizard.html
```

Expected: PASS.

---

## Self-review checklist

- [ ] All wizard fetch calls use `wizardFetch`.
- [ ] Network/API failures show a visible error instead of hanging.
- [ ] Template names/descriptions are escaped before `innerHTML`.
- [ ] Page language changed from `en` to `zh-CN`.
- [ ] No new frontend framework or build dependency introduced.
