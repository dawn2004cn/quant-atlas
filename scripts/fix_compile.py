"""Fix remaining syntax errors in 4 files."""
from __future__ import annotations

import py_compile

# 1. quote_aggregator.py - fix indent error at line 195
f = "app/infrastructure/realtime/quote_aggregator.py"
with open(f, "r", encoding="utf-8") as fh:
    lines = fh.readlines()
if "self._running = True" in lines[194]:
    # Check indentation - should be 8 spaces (inside async def)
    lines[194] = "        self._running = True\n"
with open(f, "w", encoding="utf-8") as fh:
    fh.writelines(lines)
print(f"Fixed indent: {f}")

# 2. redis_executor.py - fix corrupted GBK docstring at line 715
f = "app/infrastructure/execution/driver/redis_executor.py"
with open(f, "rb") as fh:
    raw = fh.read()
text = raw.decode("utf-8", errors="replace")
text = text.replace(
    '"""\ufffd\u6a21\u62df\u8ba2\u5355\u6267\u884c\ufffd (\u5b9e\u4e3a\ufffd\u5e94\u6d6e\u66ff\u6362\u4e3a\u771f\u5b9e\u4ea4\u6613\u6d41\ufffd\u7a0b)"""',
    '"""\u6a21\u62df\u8ba2\u5355\u6267\u884c (\u5e94\u66ff\u6362\u4e3a\u771f\u5b9e\u4ea4\u6613\u6d41\u7a0b)"""',
)
# Also fix corrupted marker string
text = text.replace('\u201c\ufffd if err else \u201c\ufffd', '"" if err else "\u2714"')
with open(f, "w", encoding="utf-8") as fh:
    fh.write(text)
print(f"Fixed encoding: {f}")

# 3. tracing.py - fix corrupted marker string at line 601
f = "app/infrastructure/tracing.py"
with open(f, "rb") as fh:
    raw = fh.read()
text = raw.decode("utf-8", errors="replace")
# The line has unicode FFFD in quotes, need to replace the specific corruption
if '\ufffd' in text:
    # Remove all U+FFFD from string literals
    # Specific fix: the marker line
    text = text.replace('\u201c\ufffd if err else \u201c\ufffd', '"" if err else "\u2714"')
    text = text.replace('\ufffd', '')  # Remove remaining
with open(f, "w", encoding="utf-8") as fh:
    fh.write(text)
print(f"Fixed encoding: {f}")

# 4. order_persistence.py - fix unterminated docstring at line 769
f = "app/domain/trading/order_persistence.py"
with open(f, "rb") as fh:
    raw = fh.read()
text = raw.decode("utf-8", errors="replace")
# Fix specific known corruption in the last docstring
if "\u83b7\u53d6\u5168\u5c40\u6301\u4e45\u5316\u5b9e\u4f8b" in text:
    pass  # Already correct
else:
    # Find the last docstring and fix it
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "\u768e" in line and '"""' in line:
            lines[i] = '"""\u83b7\u53d6\u5168\u5c40\u6301\u4e45\u5316\u5b9e\u4f8b"""'
            break
    text = "\n".join(lines)
with open(f, "w", encoding="utf-8") as fh:
    fh.write(text)
print(f"Fixed encoding: {f}")

# Verify all
for f in [
    "app/domain/trading/order_persistence.py",
    "app/infrastructure/tracing.py",
    "app/infrastructure/execution/driver/redis_executor.py",
    "app/infrastructure/realtime/quote_aggregator.py",
]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {f}: {str(e)[:120]}")
