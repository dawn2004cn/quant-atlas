"""Fix the three remaining GBK-corrupted files by making them syntactically valid."""
from __future__ import annotations

import os

# File 1: order_persistence.py
f = "app/domain/trading/order_persistence.py"
with open(f, "r", encoding="utf-8", errors="replace") as fh:
    lines = fh.readlines()
# Find and fix docstrings with corruption
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if '"""' in line and ('鑾' in line or '濡' in line or '�' in line):
        # Skip until closing triple quote
        new_lines.append('        """Order persistence service"""\n')
        i += 1
        while i < len(lines) and '"""' not in lines[i]:
            i += 1
        if i < len(lines):
            i += 1  # skip the closing line
        continue
    new_lines.append(line)
    i += 1
with open(f, "w", encoding="utf-8") as fh:
    fh.writelines(new_lines)
print(f"Fixed: {f}")

# File 2: tracing.py
f = "app/infrastructure/tracing.py"
with open(f, "r", encoding="utf-8", errors="replace") as fh:
    lines = fh.readlines()
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if 'marker = "' in line and 'if err' in line:
        new_lines.append('            marker = "X" if err else "O"\n')
        i += 1
    elif 'lines.append(' in line and '{i+1}' in line and '{span.get' in line:
        # Fix the f-string
        new_lines.append('            lines.append(f"{i+1}. [{span.get(\'span_type\', \'\')}] {op}: {start} - {end} {marker}")\n')
        i += 1
    else:
        new_lines.append(line)
        i += 1
with open(f, "w", encoding="utf-8") as fh:
    fh.writelines(new_lines)
print(f"Fixed: {f}")

# File 3: redis_executor.py
f = "app/infrastructure/execution/driver/redis_executor.py"
with open(f, "r", encoding="utf-8", errors="replace") as fh:
    lines = fh.readlines()
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if '"""' in line and ('濡' in line or '�' in line):
        # Skip until closing triple quote
        new_lines.append('        """Process execution result"""\n')
        i += 1
        while i < len(lines) and '"""' not in lines[i]:
            i += 1
        if i < len(lines):
            i += 1
        continue
    new_lines.append(line)
    i += 1
with open(f, "w", encoding="utf-8") as fh:
    fh.writelines(new_lines)
print(f"Fixed: {f}")

print("All three files fixed for syntax.")