"""Fix remaining syntax errors in two files: trading/order_persistence.py, tracing.py, redis_executor.py"""
from __future__ import annotations

import py_compile

files = [
    "app/domain/trading/order_persistence.py",
    "app/infrastructure/tracing.py",
    "app/infrastructure/execution/driver/redis_executor.py",
]

for path in files:
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        
        # Fix unterminated docstring with corrupted Chinese characters
        if '"""\u7ab9' in line or '"""\u83b7' in line or '\u7ab9\u5cf0' in line:
            lines[i] = '        """\u83b7\u53d6\u5168\u5c40\u6301\u4e45\u5316\u5b9e\u4f8b"""\n'
            print(f"Fixed docstring in {path}:{i+1}")
        
        # Fix corrupted docstring with '濡鈩'
        if '"""\u6e' in line or '\u6e\u6ce1' in line:
            lines[i] = '        """Simulated order execution"""\n'
            print(f"Fixed docstring in {path}:{i+1}")
        
        # Fix corrupted marker line
        if 'marker = "' in line and 'if err' in line:
            lines[i] = '            marker = "X" if err else "O"\n'
            print(f"Fixed marker in {path}:{i+1}")
        
        # Fix corrupted f-string with Chinese characters
        if '\ufffd' in line or '\u2022' in line:
            # Replace the entire line with safe version
            lines[i] = f'            lines.append(f"{{i+1}}. [{{\'span_type\'}}] {{op}}: {{start}} - {{end}} {{marker}}")\n'
            print(f"Fixed f-string in {path}:{i+1}")
    
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)

# Verify
for path in files:
    try:
        py_compile.compile(path, doraise=True)
        print(f"OK: {path}")
    except py_compile.PyCompileError as e:
        print(f"FAIL: {path}: {str(e)[:200]}")