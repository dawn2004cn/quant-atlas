"""Fix remaining 3 GBK-corrupted files by reading as GBK, writing as UTF-8."""
from __future__ import annotations

import py_compile

# These 3 files were originally stored as GBK; read as GBK, write as UTF-8
# then fix any remaining compilation issues

files = [
    "app/domain/trading/order_persistence.py",
    "app/infrastructure/tracing.py",
    "app/infrastructure/execution/driver/redis_executor.py",
]

for path in files:
    with open(path, "rb") as fh:
        raw = fh.read()
    
    # Step 1: decode the original bytes as GBK to get correct Chinese text
    try:
        text = raw.decode("gbk")
        was_gbk = True
        print(f"{path}: was GBK, decoded successfully")
    except (UnicodeDecodeError, LookupError):
        text = raw.decode("utf-8", errors="replace")
        was_gbk = False
        print(f"{path}: read as UTF-8 with replacement")
    
    # Step 2: remove any remaining U+FFFD
    text = text.replace("\ufffd", "")
    
    # Step 3: write back as UTF-8
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"  Written as UTF-8 ({len(text)} chars)")

# Verify compilation
for path in files:
    try:
        py_compile.compile(path, doraise=True)
        print(f"  OK: {path}")
    except py_compile.PyCompileError as e:
        msg = str(e)
        print(f"  FAIL: {path}: {msg[:120]}")
        # Find the line number
        import re
        m = re.search(r"line (\d+)", msg)
        if m:
            lineno = int(m.group(1))
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            for l in range(max(0, lineno-2), min(len(lines), lineno+2)):
                print(f"    L{l+1}: {lines[l].rstrip()[:100]}")