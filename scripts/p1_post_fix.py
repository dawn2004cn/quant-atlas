"""Fix remaining compilation errors after Phase 1 subagent fixes.

Three categories of errors:
A. os.getenv injected inside existing string literals (15 files)  
B. import logging placed inside try/except blocks (6 files)
C. Indentation errors (5 files)
D. Remaining GBK corruption (2 files)
"""
from __future__ import annotations

import py_compile
import re
import os


def fix_file(path: str) -> bool:
    with open(path, "rb") as fh:
        raw = fh.read()
    
    try:
        text = raw.decode("utf-8", errors="replace")
    except:
        text = raw.decode("gbk", errors="replace")
    
    original = text
    
    # A. Fix os.getenv injected inside string literals
    # Pattern: "os.getenv("REDIS_URL", "redis://...")" -> "" (empty default)
    text = re.sub(r'"os\.getenv\("REDIS_URL",\s*"redis://[^"]+"\)"', '""', text)
    text = re.sub(r'"os\.getenv\("REDIS_URL",\s*"redis://[^"]+",\s*\d+\)"', '""', text)
    
    # More permissive pattern for any os.getenv nested in string
    text = re.sub(r'"[^"]*os\.getenv[^"]*"', '""', text)
    
    # B. Fix import logging inside except blocks
    # Remove import logging / logger = logging that was injected inside try/except
    lines = text.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # If we see "import logging" or "logger = logging" inside an except block context
        if (stripped == "import logging" and 
            i > 0 and "except" in lines[i-1]):
            # Skip this line, the import should be at the top
            i += 1
            continue
            
        if (stripped.startswith("logger = logging.getLogger") and
            i > 0 and "except" in lines[i-1]):
            i += 1
            continue
            
        new_lines.append(line)
        i += 1
    
    text = "\n".join(new_lines)
    
    if text != original:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return True
    return False


def main():
    # Find all failing files
    failed = []
    for r, _, files in os.walk("app"):
        if "__pycache__" in r:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(r, f)
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError:
                failed.append(path)
    
    print(f"Files failing: {len(failed)}")
    
    fixed = 0
    for path in failed:
        if fix_file(path):
            fixed += 1
            print(f"  Fixed: {os.path.relpath(path)}")
    
    # Verify
    still_failing = []
    for path in failed:
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            still_failing.append((path, str(e)[:120]))
    
    print(f"\nFixed: {fixed}")
    print(f"Still failing: {len(still_failing)}")
    for path, err in still_failing:
        print(f"  {os.path.relpath(path)}: {err}")


if __name__ == "__main__":
    main()