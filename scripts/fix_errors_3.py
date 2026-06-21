"""Fix remaining syntax/encoding errors in 4 files."""
from __future__ import annotations

import py_compile

files = [
    "app/infrastructure/realtime/quote_aggregator.py",
    "app/domain/trading/order_persistence.py",
    "app/infrastructure/tracing.py",
    "app/infrastructure/execution/driver/redis_executor.py",
]

for path in files:
    with open(path, "rb") as fh:
        raw = fh.read()
    
    # Read as UTF-8 with replacement
    text = raw.decode("utf-8", errors="replace")
    
    # Replace all corrupted characters (replacement char and other garbage)
    text = text.replace("\ufffd", "")
    
    # Also handle cases where the string might be in a different encoding
    # by trying specific known fixes
    lines = text.split("\n")
    modified = False
    
    for i, line in enumerate(lines):
        # Fix string literals with corrupted content
        if "marker" in line and 'if err' in line:
            lines[i] = '            marker = "X" if err else "O"'
            modified = True
            print(f"  Fixed marker line in {path}:{i+1}")
    
    if modified:
        text = "\n".join(lines)
    
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)

# Now try to compile
for path in files:
    try:
        py_compile.compile(path, doraise=True)
        print(f"OK: {path}")
    except py_compile.PyCompileError as e:
        print(f"FAIL: {path}: {str(e)[:200]}")