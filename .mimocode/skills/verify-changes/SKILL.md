---
name: verify-changes
description: "Post-change verification pipeline for quant-atlas. Use after any code edit to verify compilation, boot integrity, route count, and test suite. Encodes the verification steps observed in 20+ sessions."
---

# Verify Changes

Standard verification pipeline to run after any code modification in quant-atlas. Ensures no regressions in compilation, boot, routing, or tests.

## When to use

- After editing any `.py` file in `app/`
- After adding/removing/modifying routes
- After changing factory wiring or service registration
- Before ending a session or marking a task complete
- After merging or relocating files

## Procedure

### Step 1 — Compile check (all modified files)

```powershell
python -m py_compile <file1> && python -m py_compile <file2> && echo "ALL COMPILE OK"
```

For bulk check of recently modified files:

```powershell
python -c "
import py_compile, sys, os
from pathlib import Path

app_root = Path('app')
errors = []
count = 0
for f in app_root.rglob('*.py'):
    if '__pycache__' in str(f) or 'graphify-out' in str(f):
        continue
    try:
        py_compile.compile(str(f), doraise=True)
        count += 1
    except py_compile.PyCompileError as e:
        errors.append(str(e))

print(f'{count} files compiled OK')
if errors:
    print(f'{len(errors)} ERRORS:')
    for e in errors:
        print(f'  {e}')
    sys.exit(1)
print('All files compile cleanly')
"
```

### Step 2 — Boot test (create_app)

```powershell
$env:FLASK_SECRET_KEY='test'; python -c "
import sys, os
sys.path.insert(0, '.')
from app.bootstrap import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules()]
print(f'Routes: {len(rules)}')
print('Boot OK')
" 2>&1
```

Record the route count. If it dropped from the previous baseline, investigate which routes are missing.

**Expected baseline**: 595+ routes (as of 2026-06-15; check REFACTORING_LOG.md for latest).

### Step 3 — Route sanity check

Verify key endpoints exist:

```powershell
python -c "
import sys, os
sys.path.insert(0, '.')
os.environ['FLASK_SECRET_KEY'] = 'test'
from app.bootstrap import create_app
app = create_app()

required = [
    '/system/health',
    '/api/v1/stock/search',
    '/api/v1/market/quote',
]
missing = []
for ep in required:
    # Try to resolve the endpoint
    try:
        # Build from dot notation
        parts = ep.strip('/').split('/')
        endpoint = '.'.join(parts)
        app.url_map.build(endpoint)
    except Exception:
        # Try direct rule match
        rules = [r.rule for r in app.url_map.iter_rules()]
        if ep not in rules:
            missing.append(ep)

if missing:
    print(f'MISSING endpoints: {missing}')
else:
    print('All key endpoints present')
"
```

### Step 4 — Lint check (optional, for new/modified files)

```powershell
python -m ruff check app/ --select F,E,W --statistics 2>&1 | Select-Object -Last 10
```

Focus on:
- **F811** — redefinition of unused name (most common in this codebase)
- **E402** — module-level import not at top of file
- **F401** — unused import

### Step 5 — Smoke tests (if test suite exists)

```powershell
python -m pytest tests/smoke/ -v --tb=short 2>&1 | Select-Object -Last 20
```

If smoke tests don't exist or have pre-existing failures, skip and note in output.

### Step 6 — Summary report

Output a compact verification report:

```
=== Verification Report ===
Compile:     X files OK / Y errors
Boot:        N routes (baseline: M)
Endpoints:   all present / missing: [...]
Lint:        W warnings
Smoke tests: P passed / Q failed / skipped
Status:      PASS / FAIL
```

## Stopping condition

- Status: PASS (all checks green) → safe to commit or continue
- Status: FAIL → fix the specific failures before proceeding

## Notes

- The `FLASK_SECRET_KEY=test` env var is required for dev boot — without it, settings validation may fail
- Route count can legitimately change when adding new routes; compare against expected delta, not absolute baseline
- Pre-existing lint warnings (F811 in wiring files, E402 in route files) are tracked in REFACTORING_LOG.md — don't re-fix them unless actively working on those files
