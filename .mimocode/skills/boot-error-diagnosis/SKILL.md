---
name: boot-error-diagnosis
description: "Systematic diagnosis and fixing of quant-atlas Flask app boot errors. Use when the app fails to start, throws ImportError/TypeError/NameError during create_app(), or shows 'REQUIRED services missing' / 'Failed to register route' warnings. Covers the full cycle: run → parse → categorize → fix → re-verify."
---

# Boot Error Diagnosis

Systematically diagnose and fix quant-atlas Flask app startup errors. This skill encodes the repeated workflow observed across 8+ sessions where boot errors were the primary blocking issue.

## When to use

- `python run.py` fails or shows errors
- `create_app()` raises exceptions
- Boot warnings appear: "REQUIRED services missing", "Failed to register route", "wiring failed"
- After adding new factory functions, routes, or service wiring
- After refactoring imports or module structure

## Prerequisites

- Python `(base)` conda environment
- Working directory: `E:\project\workspace\myrepo\quant-atlas`
- `FLASK_SECRET_KEY` must be set (use `test` for dev)

## Procedure

### Step 1 — Run the app and capture errors

```powershell
cd E:\project\workspace\myrepo\quant-atlas
$env:FLASK_SECRET_KEY='test'; python run.py 2>&1 | Out-File -FilePath boot-errors.txt
```

If `run.py` doesn't exist or has its own errors, use the direct import:

```powershell
python -c "
import sys, os
sys.path.insert(0, '.')
os.environ['FLASK_SECRET_KEY'] = 'test'
from app.bootstrap import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules()]
print('Routes:', len(rules))
print('OK')
" 2>&1
```

### Step 2 — Categorize each error

Parse the error output and classify into these known categories:

| Category | Symptom | Likely root cause |
|----------|---------|-------------------|
| **A — Missing import** | `ImportError: cannot import name 'X' from 'Y'` | Re-export missing in `__init__.py` or `registry.py`; wrong import path |
| **B — Factory kwargs** | `got an unexpected keyword argument '_registry'` | Factory function lacks `**kwargs`. `TypedServiceRegistry.resolve()` always passes `_registry=self` |
| **C — Missing factory** | `REQUIRED services missing: X, Y` | Factory not registered, or factory errors silently during resolution |
| **D — Route registration** | `Failed to register route X: Y_unavailable` | Service dependency not resolved; factory returns None |
| **E — Blueprint import** | `No module named 'X'` during blueprint registration | Transitive import chain broken; try/except wrapper needed |
| **F — Missing variable** | `NameError: name 'X' is not defined` | Import missing in route file (common: `login_required`, DTO names) |
| **G — Optional component** | `OPTIONAL component 'X' skipped` | Non-critical; skip unless user explicitly requests fix |

### Step 3 — Fix each error by category

**Category A — Missing import:**
1. Check if the name exists in the target module
2. If yes: add re-export to `__init__.py` or `app/core/registry.py` (which re-exports from `typed_registry`, `route_registry`, `module_registry`)
3. If no: the name was removed/renamed; update the import site

**Category B — Factory kwargs (CRITICAL — most common):**
1. Find the factory function in `app/bootstrap_components/wiring_*.py`
2. Add `**kwargs` to the signature: `_make_xxx(reg)` → `_make_xxx(reg, **kwargs)`
3. ALL factory functions registered via `register_factory()` MUST accept `**kwargs`

**Category C — Missing factory:**
1. Check `app/bootstrap_components/wiring_*.py` for factory registration
2. Verify factory function doesn't error during execution (add try/except for debugging)
3. Check `app/bootstrap_components/service_readiness.py` for REQUIRED vs OPTIONAL classification

**Category D — Route registration:**
1. Trace the service dependency chain back to the factory
2. Fix the factory or mark the route as optional
3. Check `v1_context.py` defaults — route_deps builder picks up services from context

**Category E — Blueprint import:**
1. Wrap blueprint registration in try/except if the module is non-critical
2. For v2 blueprint: the error is typically in transitive imports, not the direct import

**Category F — Missing variable:**
1. Add the missing import to the route file
2. Common patterns: `login_required` from `flask_login`, DTO names from `app.domain.dto.*`
3. Stock sub-modules (`v1/stock/stock_basic.py` etc.) need their own imports — parent dispatcher doesn't inject them

### Step 4 — Verify after each fix

```powershell
python -m py_compile <fixed_file> && echo "COMPILE OK"
```

### Step 5 — Full boot verification

```powershell
python -c "
import sys, os
sys.path.insert(0, '.')
os.environ['FLASK_SECRET_KEY'] = 'test'
from app.bootstrap import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules()]
print(f'Routes: {len(rules)}')
# Check specific endpoints
for r in ['/system/health', '/api/v1/stock/search']:
    try:
        app.url_map.build(r.strip('/').replace('/', '.'))
    except Exception:
        print(f'WARNING: {r} not routable')
print('Boot OK')
" 2>&1
```

Verify:
- Zero `ImportError` / `TypeError` / `NameError`
- Route count matches expected (check REFACTORING_LOG.md for baseline)
- No new "REQUIRED services missing" warnings
- No new "Failed to register route" warnings

### Step 6 — Handle remaining warnings

For pre-existing warnings that are NOT new:
- `Auth blueprint not available` — known, auth_service needs JsonUserRepository
- `warm_runtime_extensions skipped` — optional component
- Document in REFACTORING_LOG.md if the user wants them tracked

## Known gotchas (from MEMORY.md)

- **Factory `**kwargs`**: `TypedServiceRegistry.resolve()` passes `_registry=self` as keyword arg. Without `**kwargs`, factory calls fail silently.
- **Stock sub-module imports**: `v1/stock/` files need their own Flask/DTO imports.
- **`user_tiers` path**: Lives at `app.presentation.api.v1.user_tiers`, not `app.presentation.api.user_tiers`.
- **`start_truth_sentry`**: Defined in `app/bootstrap_components/bootstrap_helpers.py`.
- **`get_registry`**: Must be re-exported from `app/core/registry.py` (which re-exports from `typed_registry`).
- **`auth_service` wiring**: Requires `JsonUserRepository` — constructor has mandatory args.
- **Error cascade**: Broken import in wiring module → factory registration skipped → "REQUIRED services missing" for downstream services.

## Stopping condition

All of these must be true:
- `create_app()` completes without exceptions
- Zero new error categories A-F
- Route count is stable (no unexpected drops)
- User confirms the app is usable
