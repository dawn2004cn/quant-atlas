"""Phase 1: Fix try/except pass patterns across app/ directory.

Replaces bare ``except ...: pass`` with ``except ...: logger.warning(...)``.
"""
from __future__ import annotations

import ast
import logging
import os
import re

FIX_COUNT = 0
FILE_COUNT = 0

for dirpath, dirnames, filenames in os.walk("app"):
    if "__pycache__" in dirpath:
        continue
    for filename in filenames:
        if not filename.endswith(".py"):
            continue
        path = os.path.join(dirpath, filename)

        # Read file, handle encoding
        try:
            with open(path, encoding="utf-8") as f:
                raw = f.read()
        except UnicodeDecodeError:
            try:
                with open(path, encoding="gbk") as f:
                    raw = f.read()
            except Exception:
                continue

        original = raw
        lines = raw.split("\n")
        changed = False

        # Check if logger exists
        has_logger = any(
            "logger = logging.getLogger" in l or "logger = get_logger" in l
            for l in lines
        )
        has_logging_import = any(
            "import logging" in l or "from logging import" in l
            for l in lines
        )

        # Find the right place to add logger import
        # (after docstring, after __future__, after imports)
        insert_pos = 0
        for i, l in enumerate(lines):
            if l.startswith("import ") or l.startswith("from "):
                insert_pos = i + 1
            elif l.startswith('"""') or l.startswith("#"):
                pass  # keep looking past docstring

        # Fix each except: pass pattern
        i = 0
        while i < len(lines):
            line = lines[i]
            # Pattern: except X: pass  (same line)
            m = re.match(r"(\s*)(except [^:]+:)\s*pass\s*(#.*)?$", line)
            if m:
                indent = m.group(1)
                exc_clause = m.group(2)
                comment = m.group(3) or ""
                spacer = " " if comment else ""
                lines[i] = (
                    f"{indent}{exc_clause}\n"
                    f'{indent}    logger.warning("Suppressed exception", exc_info=True)\n'
                    f"{indent}    pass{spacer}{comment}"
                )
                changed = True
                FIX_COUNT += 1
                i += 1
                continue

            # Pattern: except X:\n    pass  (next line)
            if re.match(r"\s*except [^:]+:$", line):
                # Check next lines for pass
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and re.match(r"\s*pass\s*(#.*)?$", lines[j]):
                    indent = re.match(r"\s*", line).group(0)
                    lines[i] = line.rstrip()
                    lines.insert(j, f"{indent}    logger.warning(\"Suppressed exception\", exc_info=True)")
                    changed = True
                    FIX_COUNT += 1
                    i = j + 1
                    continue
            i += 1

        if not changed:
            continue

        # Now we need to ensure logger is available
        # Find or add logger after imports
        raw = "\n".join(lines)

        if not has_logger:
            if not has_logging_import:
                # Find spot after __future__ and docstrings
                insert_at = 0
                mod_lines = raw.split("\n")
                for k, l in enumerate(mod_lines):
                    if l.startswith("from __future__"):
                        insert_at = k + 1
                    elif l.startswith('"""') and insert_at <= k < insert_at + 5:
                        insert_at = k + 1
                    elif l.strip().startswith("import ") or l.strip().startswith("from "):
                        insert_at = k + 1
                mod_lines.insert(
                    insert_at,
                    "import logging\nlogger = logging.getLogger(__name__)\n",
                )
                raw = "\n".join(mod_lines)
            else:
                # Has logging import but no logger var
                mod_lines = raw.split("\n")
                for k, l in enumerate(mod_lines):
                    if l.strip().startswith("import logging"):
                        mod_lines.insert(k + 1, "logger = logging.getLogger(__name__)")
                        break
                raw = "\n".join(mod_lines)

        with open(path, "w", encoding="utf-8") as f:
            f.write(raw)
        FILE_COUNT += 1
        print(f"  Fixed: {os.path.relpath(path)} ({FIX_COUNT} patterns)")

print(f"\nSummary: {FILE_COUNT} files modified, {FIX_COUNT} except:pass patterns fixed")
