"""Fix all 28 compilation errors from Phase 1 changes.

Categories of errors:
1. Quotes around os.getenv(...) - Subagent put quotes around os.getenv() calls
2. Misplaced import logging in try/except blocks
3. Indentation errors
4. Remaining GBK corruption in order_persistence.py
"""
from __future__ import annotations

import os
import re

BASE = "app"

# Category 1: Fix quotes around os.getenv() in default params
# Pattern: "os.getenv("REDIS_URL", ...)" -> os.getenv("REDIS_URL", ...)
def fix_osgetenv_quoting(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    
    # Fix: "os.getenv("X", "y")" -> os.getenv("X", "y")
    content = re.sub(r'"os\.getenv\(([^)]+)\)"', 
                     r'os.getenv(\1)',
                     content)
    
    # Fix: get_runtime("X", "os.getenv(Y)") -> get_runtime("X", os.getenv(Y))
    content = re.sub(r'get_runtime\(([^,]+),\s*"os\.getenv\(([^)]+)\)"\)',
                     r'get_runtime(\1, os.getenv(\2))',
                     content)
    
    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


# Category 2 & 3: Fix misplaced imports and indent
def fix_misplaced_imports(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    original = lines.copy()
    new_lines = []
    skip_until = -1
    
    for i, line in enumerate(lines):
        if i < skip_until:
            continue
        
        # Skip misplaced import logging that appears in try/except blocks
        if i > 10 and 'import logging' in line and i + 2 < len(lines):
            if 'logger = logging' in lines[i+1]:
                # Check if this is inside a try/except block
                before = ''.join(lines[max(0,i-5):i])
                if 'except' in before or i > 50:
                    skip_until = i + 3
                    continue
        
        new_lines.append(line)
    
    content = ''.join(new_lines)
    if content != ''.join(original):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


# Fix specifically the files
files = [
    "app/agents/redis_evidence_blackboard.py",
    "app/config/infra_settings.py",
    "app/core/llm_config.py",
    "app/core/tracing/__init__.py",
    "app/domain/trading/order_persistence.py",
    "app/infrastructure/redis_client.py",
    "app/infrastructure/tracing.py",
    "app/infrastructure/adapters/ccxt_adapter.py",
    "app/infrastructure/adapters/tencent_quote_gateway.py",
    "app/infrastructure/cache/multi_level_cache.py",
    "app/infrastructure/cache/quote_cache.py",
    "app/infrastructure/execution/driver/redis_executor.py",
    "app/infrastructure/messaging/task_message_store.py",
    "app/infrastructure/persistence/distributed_state.py",
    "app/infrastructure/persistence/knowledge_store.py",
    "app/infrastructure/realtime/market_stream.py",
    "app/modules/health.py",
    "app/modules/ai_agent/services/command_plan_service.py",
    "app/modules/ai_agent/services/prompt_trace.py",
    "app/modules/execution/services/pre_trade_preflight_service.py",
    "app/modules/system/services/config/hot_config.py",
    "app/modules/system/services/system/data_truth_guardian_service.py",
    "app/modules/system/services/ui/decision_snapshot_service.py",
    "app/presentation/api/routes_v1_evolution_arbiter.py",
    "app/presentation/api/routes_v1_llm_config.py",
    "app/presentation/api/routes_v1_workflows.py",
    "app/presentation/api/v1/retail_assistant/shadow_routes.py",
    "app/tasks/task_wiring.py",
]

fixed = 0
for f in files:
    path = os.path.join(BASE, f) if not f.startswith("app/") else f
    exists = os.path.exists(path)
    if not exists:
        continue
    
    # Fix os.getenv quoting
    if fix_osgetenv_quoting(path):
        fixed += 1
        print(f"  FIX_QUOTING: {f}")
    
    # Fix misplaced imports
    if fix_misplaced_imports(path):
        fixed += 1
        print(f"  FIX_IMPORTS: {f}")

# Special fix for order_persistence.py - corrupted docstring
f = "app/domain/trading/order_persistence.py"
with open(f, "r", encoding="utf-8", errors="replace") as fh:
    content = fh.read()

# Find and fix unterminated docstring with \u7ab9 or other corrupted chars
lines = content.split("\n")
for i, line in enumerate(lines):
    if '"""\u7ab9' in line or '\u7ab9\u5cf0' in line:
        lines[i] = '"""Get global portfolio snapshot"""'
        print(f"  FIX_DOCSTRING: {f}:{i+1}")
    if '\ufffd' in line:
        lines[i] = line.replace('\ufffd', '')
        print(f"  FIX_FFFD: {f}:{i+1}")

content = "\n".join(lines)
with open(f, "w", encoding="utf-8") as fh:
    fh.write(content)

if fixed:
    print(f"\nFixed {fixed} files")

# Verify
import py_compile
ok = 0
fail = 0
for f in files:
    path = os.path.join(BASE, f) if not f.startswith("app/") else f
    if not os.path.exists(path):
        continue
    try:
        py_compile.compile(path, doraise=True)
        ok += 1
    except py_compile.PyCompileError as e:
        fail += 1
        print(f"  STILL FAILS: {f}: {str(e)[:100]}")

print(f"\nCompilation: {ok} OK, {fail} FAILED")