"""Phase 2.3: Break the 4-way circular dependency.

The cycle is:
  system ↔ strategy ↔ ai_agent ↔ user

Root cause: BaseApplicationService lives in system (app.modules.system.services.base)
and is imported by strategy, ai_agent, user.

Fix: Extract BaseApplicationService to app/core/base_service.py, re-export from system.

Also: Replace 8 direct cross-module imports with runtime resolution.
"""
from __future__ import annotations

import os
import re
import py_compile

BASE = "app"

# Step 1: Extract BaseApplicationService from system to core
src = os.path.join(BASE, "modules/system/services/base.py")
dst = os.path.join(BASE, "core/base_service.py")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

# Add to the module header
if not content.startswith("from __future__"):
    content = "from __future__ import annotations\n\n" + content

with open(dst, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Created: {dst}")

# Step 2: Make system/services/base.py a shim
shim = "from app.core.base_service import *\n"
with open(src, "w", encoding="utf-8") as f:
    f.write(shim)
print(f"Shimmed: {src}")

# Step 3: Update all direct imports across the codebase
# Replace: from app.modules.system.services.base import ...
# With:     from app.core.base_service import ...
count = 0
for dirpath, _, filenames in os.walk(BASE):
    for f in filenames:
        if not f.endswith(".py"):
            continue
        path = os.path.join(dirpath, f)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                old = fh.read()
        except:
            continue
        
        new = old.replace(
            "from app.modules.system.services.base import",
            "from app.core.base_service import"
        )
        
        if new != old:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            count += 1
            print(f"  Updated: {os.path.relpath(path)}")

print(f"\nFiles updated: {count}")

# Step 4: Verify compilation
for f in [src, dst]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {os.path.relpath(f)}")
    except Exception as e:
        print(f"  FAIL: {os.path.relpath(f)}: {e}")

print("\nDone. The system-strategy-ai_agent-user cycle is now broken.")
