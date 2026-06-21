"""Phase 1 post-fix: Fix remaining 17 compilation errors."""
from __future__ import annotations

import re

# 1. infra_settings.py: string splice error
f = "app/config/infra_settings.py"
with open(f, "r", encoding="utf-8") as fh:
    content = fh.read()
content = content.replace('_MODEL_REGISTRY_PATH = _CONFIG_DIR / "model_registry.json""DE', '_MODEL_REGISTRY_PATH = _CONFIG_DIR / "model_registry.json"')
content = content.replace('"DEFAULT_NETWORK_MASK", "os.getenv(','os.getenv("DEFAULT_NETWORK_MASK", ')
with open(f, "w", encoding="utf-8") as fh:
    fh.write(content)
print(f"Fixed: {f}")

# 2. llm_config.py: import logging in except block
f = "app/core/llm_config.py"
with open(f, "r", encoding="utf-8") as fh:
    text = fh.read()
# Remove standalone import logging / logger = logging inside blocks
text = re.sub(r'\n\s+import logging\s*\n\s+logger = logging\.getLogger\(__name__\)', '', text)
with open(f, "w", encoding="utf-8") as fh:
    fh.write(text)
print(f"Fixed: {f}")

# 3. tracing/__init__.py: import logging in except block
f = "app/core/tracing/__init__.py"
with open(f, "r", encoding="utf-8") as fh:
    text = fh.read()
text = re.sub(r'\n\s+import logging\s*\n\s+logger = logging\.getLogger\(__name__\)', '', text)
with open(f, "w", encoding="utf-8") as fh:
    fh.write(text)
print(f"Fixed: {f}")

# 4. order_persistence.py: unterminated docstring
f = "app/domain/trading/order_persistence.py"
with open(f, "r", encoding="utf-8") as fh:
    lines = fh.readlines()
for i, line in enumerate(lines):
    if '\u7ab9' in line:
        lines[i] = '"""Get global portfolio snapshot"""\n'
with open(f, "w", encoding="utf-8") as fh:
    fh.writelines(lines)
print(f"Fixed: {f}")

# 5. ccxt_adapter.py: indentation error
f = "app/infrastructure/adapters/ccxt_adapter.py"
with open(f, "r", encoding="utf-8") as fh:
    lines = fh.readlines()
for i, line in enumerate(lines):
    if line.strip() == 'import logging' and i > 5:
        lines[i] = ''  # remove duplicate
    if line.strip().startswith('logger = logging.getLogger') and i > 5:
        lines[i] = ''  # remove duplicate
lines = [l for l in lines if l.strip() or l == '\n']  # remove orphan blank lines
with open(f, "w", encoding="utf-8") as fh:
    fh.writelines(lines)
print(f"Fixed: {f}")

# 6. tencent_quote_gateway.py: import logging in except
f = "app/infrastructure/adapters/tencent_quote_gateway.py"
with open(f, "r", encoding="utf-8") as fh:
    text = fh.read()
text = re.sub(r'\n\s+import logging\s*\n\s+logger = logging\.getLogger\(__name__\)', '', text)
with open(f, "w", encoding="utf-8") as fh:
    fh.write(text)
print(f"Fixed: {f}")

# 7. redis_executor.py: corrupted docstring
f = "app/infrastructure/execution/driver/redis_executor.py"
with open(f, "r", encoding="utf-8") as fh:
    lines = fh.readlines()
for i, line in enumerate(lines):
    if '\u6ce1' in line:
        lines[i] = '        """Submit order for processing"""\n'
with open(f, "w", encoding="utf-8") as fh:
    fh.writelines(lines)
print(f"Fixed: {f}")

# 8-17: Fix misplaced imports in remaining files
fixes = {
    "app/modules/ai_agent/services/prompt_trace.py": None,
    "app/modules/execution/services/pre_trade_preflight_service.py": None,
    "app/modules/system/services/system/data_truth_guardian_service.py": None,
    "app/presentation/api/routes_v1_evolution_arbiter.py": None,
    "app/presentation/api/routes_v1_llm_config.py": None,
    "app/presentation/api/routes_v1_workflows.py": None,
    "app/presentation/api/v1/retail_assistant/shadow_routes.py": None,
    "app/tasks/task_wiring.py": None,
    "app/modules/ai_agent/services/command_plan_service.py": None,
    "app/modules/system/services/ui/decision_snapshot_service.py": None,
}

for f in fixes:
    with open(f, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    # Remove misplaced import logging (inside blocks, not at module top)
    # Strategy: remove ALL 'import logging' and 'logger = logging' that appear after line 20
    new_lines = []
    for i, line in enumerate(lines):
        if i > 20:
            stripped = line.strip()
            if stripped == 'import logging' or stripped.startswith('logger = logging.getLogger'):
                continue
        new_lines.append(line)
    with open(f, "w", encoding="utf-8") as fh:
        fh.writelines(new_lines)
    print(f"Cleaned: {f}")

# Verify
import py_compile
errors = []
for f in list(fixes.keys()) + [
    "app/config/infra_settings.py",
    "app/core/llm_config.py",
    "app/core/tracing/__init__.py",
    "app/domain/trading/order_persistence.py",
    "app/infrastructure/adapters/ccxt_adapter.py",
    "app/infrastructure/adapters/tencent_quote_gateway.py",
    "app/infrastructure/execution/driver/redis_executor.py",
]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {f}")
    except py_compile.PyCompileError as e:
        errors.append((f, str(e)[:120]))

print(f"\nRemaining errors: {len(errors)}")
for f, e in errors:
    print(f"  {f}: {e}")