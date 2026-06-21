#!/usr/bin/env python3
"""Audit script: scan the codebase for get_*() imports from _wiring and _access modules.

Identifies consumers still using the legacy bind/get pattern that should be migrated
to direct dependency injection.

Usage:
    python scripts/audit_bind_get_usage.py
"""

import ast
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict


@dataclass
class ImportSite:
    file: str
    line: int
    imported_name: str
    source_module: str
    is_reexport: bool  # True if importing via _wiring which re-exports from _access


def scan_file(filepath: Path) -> list[ImportSite]:
    """Parse a Python file and find imports from *_wiring.py and *_access.py that
    bring in names starting with get_ or _get or _wire_from."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    sites = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if not (module.endswith("_wiring") or module.endswith("_access")):
                continue

            for alias in node.names:
                name = alias.name
                # Flag get_* imports
                if name.startswith("get_") or name == "_get" or name == "_wire_from_registry":
                    sites.append(ImportSite(
                        file=str(filepath),
                        line=node.lineno,
                        imported_name=name,
                        source_module=module,
                        is_reexport=module.endswith("_access"),
                    ))

    return sites


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "app"
    if not root.is_dir():
        root = Path(".").resolve() / "app"

    all_sites: list[ImportSite] = []

    for pyfile in sorted(root.rglob("*.py")):
        sites = scan_file(pyfile)
        if sites:
            all_sites.extend(sites)

    # Categorize
    by_type = defaultdict(list)
    for s in all_sites:
        if s.is_reexport:
            by_type["_access (re-export via _wiring or direct _access import)"].append(s)
        else:
            by_type["_wiring import"].append(s)

    # Group by source module
    by_module = defaultdict(list)
    for s in all_sites:
        by_module[s.source_module].append(s)

    # Group by consumer file
    by_file = defaultdict(list)
    for s in all_sites:
        by_file[s.file].append(s)

    # Output
    print("=" * 72)
    print("BIND/GET USAGE AUDIT")
    print(f"Scanning: {root}")
    print(f"Total import sites found: {len(all_sites)}")
    print(f"Consumer files affected: {len(by_file)}")
    print("=" * 72)

    # Summary by file
    print("\n--- Consumer files (sorted by hit count) ---")
    for filepath, imports in sorted(by_file.items(), key=lambda x: -len(x[1])):
        names = {i.imported_name for i in imports}
        print(f"  {filepath} ({len(imports)} hit(s)): {', '.join(sorted(names))}")

    # Summary by module
    print("\n--- Source modules (sorted by hit count) ---")
    for mod, imports in sorted(by_module.items(), key=lambda x: -len(x[1])):
        names = {i.imported_name for i in imports}
        files = sorted({i.file for i in imports})
        print(f"  {mod} ({len(imports)} hit(s), {len(files)} file(s)): {', '.join(sorted(names))}")

    # JSON output for programmatic use
    print("\n--- JSON summary ---")
    json_summary = {
        "total_sites": len(all_sites),
        "consumer_files": len(by_file),
        "by_file": {
            fp: [{"line": s.line, "name": s.imported_name, "source": s.source_module}
                 for s in sorted(sl, key=lambda x: x.line)]
            for fp, sl in by_file.items()
        },
        "by_module": {
            mod: {"hits": len(imps), "files": sorted({i.file for i in imps})}
            for mod, imps in by_module.items()
        },
    }
    print(json.dumps(json_summary, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
