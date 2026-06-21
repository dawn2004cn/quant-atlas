import json
import re

path = "E:\\project\\workspace\\myrepo\\quant-atlas\\app\\modules\\system\\services\\institution_tier_service.py.bak"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Fix the split newline in audit_change
for i in range(940, 960):
    line = lines[i]
    if line is None:
        continue
    if "fh.write(json.dumps(record" in str(line) and i+1 < len(lines):
        next_line = lines[i+1]
        if next_line is not None and next_line.strip() == '")':
            print(f"Found split line at L{i+1}-{i+2}")
            lines[i] = '            fh.write(json.dumps(record, ensure_ascii=False) + "\\n")\n'
            lines[i+1] = None

# Remove orphaned import lines
for i in range(len(lines)):
    if lines[i] is None:
        continue
    if "from app.infrastructure.database.models import" in str(lines[i]):
        # Check if this import is orphaned (inside a method, not at top)
        prev_has_def = False
        for j in range(max(0, i-30), i):
            if lines[j] is not None and re.match(r"    def (\w+)", str(lines[j])):
                prev_has_def = True
        if prev_has_def:
            # Only remove if not inside audit_change
            in_audit = False
            for j in range(max(0, i-20), i):
                if lines[j] is not None and "def audit_change" in str(lines[j]):
                    in_audit = True
                    break
            if not in_audit:
                print(f"Removing orphaned import at L{i+1}")
                lines[i] = None

# Remove None entries
lines = [l for l in lines if l is not None]

# Also remove consecutive blank lines (more than 2)
cleaned = []
blank_count = 0
for l in lines:
    if l.strip() == "":
        blank_count += 1
        if blank_count <= 2:
            cleaned.append(l)
    else:
        blank_count = 0
        cleaned.append(l)
lines = cleaned

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"Written: {len(lines)} lines")

import py_compile
py_compile.compile(path, doraise=True)
print("Compiles OK!")
