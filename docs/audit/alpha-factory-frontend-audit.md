# Alpha Factory Frontend Audit Report
**File**: `app/presentation/web/templates/alpha_factory.html`  
**Size**: 830 lines (verified by read, not 1256 as earlier estimate)  
**Date**: 2026-06-21

## Executive Summary

`alpha_factory.html` is a monolithic server-side-rendered Jinja template containing 830 lines of HTML + inline JavaScript. It implements a 10-tab SPA (Single Page Application) for quantitative factor research, but uses no modern frontend framework, build tooling, or state management.

**Verdict**: P1 — Functional but unsustainable. Works today, will break at scale.

---

## 1. Architecture Analysis

### Current Stack
- **Template**: Jinja2 (server-side rendering)
- **JS**: Vanilla ES6, inline `<script>` block (lines 341-829)
- **CSS**: External `alpha-factory.css`
- **State**: Implicit DOM state + global functions
- **Routing**: Tab switching via `data-af-action` attribute delegation

### File Structure
```
alpha_factory.html (830 LOC)
├── Lines 1-338: HTML structure (10 tab panels)
│   ├── Hero section (lines 17-84)
│   ├── Stats row (line 44)
│   ├── Tab navigation (lines 99-110)
│   └── 10 tab panels (lines 112-337)
└── Lines 340-829: Inline JavaScript (489 LOC)
    ├── Global state: goalDescriptions, unwrap()
    ├── Tab management: switchTab()
    ├── API functions: loadDashboard, loadFactors, validateFormula, etc.
    ├── Form handlers: submitExperiment, submitPaperTrading
    └── Event delegation: handleAfAction()
```

---

## 2. Critical Issues

### 2.1 No Component Architecture (P1)
**Issue**: 830-line monolithic file with no component boundaries.  
**Impact**: Cannot maintain, test, or reuse individual features.  
**Evidence**: `submitExperiment()` (lines 695-765) mixes form validation, API calls, DOM updates, and error handling in one function.

### 2.2 No State Management (P1)
**Issue**: State scattered across DOM elements + global variables.  
**Impact**: Race conditions when multiple API calls return out of order.  
**Evidence**:
```javascript
// Lines 578-598: loadDashboard reads DOM, writes DOM
// No caching, no loading state, no cancellation
async function loadDashboard() {
    const resp = await fetch('/api/v1/alpha-factory/status');
    // If user switches tabs mid-request, result still renders
}
```

### 2.3 No Error Boundaries (P2)
**Issue**: Each function has its own try/catch, but failures are silent.  
**Impact**: User sees blank panel with no feedback.  
**Evidence**: Lines 405-407, 434-435, 460-461 — all log to `window.qcLogError` but never show user-visible error.

### 2.4 No Request Cancellation (P2)
**Issue**: No AbortController for in-flight requests.  
**Impact**: Tab switch doesn't cancel previous fetch; results overwrite current view.

### 2.5 Mojibake / Encoding Issues (P2)
**Issue**: Chinese characters garbled in multiple places.  
**Evidence**:
- Line 24: `自动鍖?Alpha Factory` (should be 自动化)
- Line 27: `因子搴?` (should be 因子库)
- Line 31: `数据来源说明锛?` (should be 数据来源说明：)
- Line 343: `鉁?` (should be ✓ or 良好)

**Root cause**: Mixed encoding between template rendering and JS string literals.

### 2.6 Duplicate Attributes (P3)
**Issue**: Multiple elements have duplicate `type="button"` attributes.  
**Evidence**: Lines 134, 135, 136, 137, 138, 139, 140, 141, 166, 220, 233, 246, 259, 273, 303, 331 — all have `type="button"` twice.

### 2.7 No Loading States (P3)
**Issue**: Buttons disabled but no spinner or progress indicator.  
**Evidence**: Line 704: `btn.disabled = true; btn.textContent = '提交中...';` — text changes but no visual loading state.

### 2.8 Global Function Pollution (P3)
**Issue**: All functions (`loadDashboard`, `switchTab`, etc.) are global.  
**Impact**: Risk of name collisions with other scripts.

---

## 3. Performance Issues

### 3.1 No Code Splitting (P2)
**Issue**: All JS loaded on page load, even if user never visits certain tabs.  
**Impact**: ~50KB JS payload blocking initial render.

### 3.2 No Virtual Scrolling (P3)
**Issue**: `loadFactors()` (lines 600-630) renders all factors into DOM.  
**Impact**: 1000+ factors = DOM bloat, scroll jank.

### 3.3 No Memoization (P3)
**Issue**: `loadFactors()` called on every `change` event (line 827).  
**Impact**: Duplicate API calls when user changes filter rapidly.

---

## 4. Security Issues

### 4.1 XSS Risk (P2)
**Issue**: Template literals inject raw API responses into `innerHTML`.  
**Evidence**: Lines 616-626, 639-648 — no escaping of `f.formula`, `a.description`.  
**Risk**: If API returns malicious HTML, it executes in user's browser.

### 4.2 No CSRF Protection (P2)
**Issue**: POST endpoints (`/api/v1/rd-agent/runs`, `/api/v1/alpha-factory/paper-trading`) have no CSRF token.  
**Risk**: Cross-site request forgery on state-changing operations.

---

## 5. Accessibility Issues

### 5.1 No ARIA Labels (P3)
**Issue**: Tab buttons lack `role="tab"`, `aria-selected`, `aria-controls`.  
**Impact**: Screen readers cannot navigate tabs.

### 5.2 No Keyboard Navigation (P3)
**Issue**: No arrow key navigation between tabs.

---

## 6. Recommendations

### Immediate (P1 — This Sprint)
1. **Extract JS to external file**: Move lines 341-829 to `static/js/alpha-factory.js`
2. **Add loading states**: Show spinners during API calls
3. **Fix mojibake**: Ensure UTF-8 encoding throughout template

### Short-term (P2 — Next Sprint)
1. **Add AbortController**: Cancel in-flight requests on tab switch
2. **Add error UI**: Show toast/alert on API failures, not just log
3. **Escape HTML**: Use `textContent` instead of `innerHTML` for user content

### Medium-term (P3 — Phase 2)
1. **Migrate to React/Vue**: Componentize each tab
2. **Add state management**: Zustand/Redux for shared state
3. **Add virtual scrolling**: For factor list > 100 items

---

## 7. Metrics

| Metric | Current | Target |
|--------|---------|--------|
| File size | 830 LOC | < 200 LOC per component |
| JS loading | Inline (blocking) | Deferred/external |
| Time to interactive | ~3s (estimated) | < 1.5s |
| Tab switch latency | ~0ms (no loading) | < 100ms with skeleton |
| Error visibility | 0% (silent) | 100% (user-visible) |

---

## 8. Comparison with Best Practice

| Practice | Status | Gap |
|----------|--------|-----|
| Component architecture | ❌ Monolithic | Needs React/Vue migration |
| State management | ❌ DOM-scattered | Needs Zustand/Redux |
| Error handling | ⚠️ Partial | Needs error boundaries |
| Loading states | ❌ None | Needs skeletons/spinners |
| Accessibility | ❌ Minimal | Needs ARIA + keyboard nav |
| Security (XSS) | ⚠️ Risky | Needs escaping |
| Build tooling | ❌ None | Needs Vite/Webpack |
