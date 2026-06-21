"""Fix remaining GBK->UTF-8 corrupted docstrings."""
from __future__ import annotations

import os
import re

corrupted = {
    "app/infrastructure/realtime/quote_aggregator.py": [
        (185, 'self._adaptesource] = adapter', 'self._adapters[source] = adapter'),
        (36, None, None),  # Already fixed above
    ],
    "app/infrastructure/execution/driver/redis_executor.py": [
        (353, None, None),  # docstring with U+FFFD
    ],
    "app/infrastructure/tracing.py": [
        (None, None, None),
    ],
}

# Fix quote_aggregator.py
f = "app/infrastructure/realtime/quote_aggregator.py"
with open(f, "r", encoding="utf-8") as fh:
    content = fh.read()

# Fix line 185 corruption
content = content.replace("self._adaptesource] = adapter", "self._adapters[source] = adapter")

# Fix the DataSource enum (line 36) if still broken
if "EALTIME" in content:
    content = content.replace("  EALTIME", "    REALTIME")
    content = content.replace('    PUS "push"', '    PUSH = "push"')
    content = content.replace('    POLL poll"', '    POLL = "poll"')

with open(f, "w", encoding="utf-8") as fh:
    fh.write(content)
print(f"Fixed: {f}")

# Fix redis_executor.py and tracing.py (GBK docstrings)
for f in ["app/infrastructure/execution/driver/redis_executor.py",
          "app/infrastructure/tracing.py",
          "app/domain/trading/order_persistence.py"]:
    with open(f, "rb") as fh:
        raw = fh.read()
    try:
        raw.decode("utf-8")
        # Already UTF-8, just need to replace U+FFFD
        text = raw.decode("utf-8", errors="replace")
    except:
        text = raw.decode("gbk", errors="replace")
    
    # Replace U+FFFD and other non-printable chars in docstrings
    text = text.replace("\ufffd", "")
    text = re.sub(r'"""\s*"""', '""" """', text)  # empty docstring
    
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Fixed: {f}")

# Verify compilation
import py_compile
for f in ["app/infrastructure/realtime/quote_aggregator.py",
          "app/infrastructure/realtime/market_stream.py",
          "app/infrastructure/execution/driver/redis_executor.py",
          "app/infrastructure/tracing.py",
          "app/domain/trading/order_persistence.py"]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {f}: {e}")
