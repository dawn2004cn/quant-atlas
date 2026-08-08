#!/usr/bin/env python3
"""Audit /api/v1 paths referenced in frontend/src vs Flask url_map."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from app.presentation.api.route_contract import path_registered_in_rules

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = ROOT / "frontend" / "src"

# String literals and template fragments in TS/TSX
_PATH_RE = re.compile(r"""['"`](/api/v1/[^'"`?\s]+)""")


def collect_frontend_paths() -> tuple[str, ...]:
    paths: set[str] = set()
    if not FRONTEND_SRC.is_dir():
        return ()
    for path in FRONTEND_SRC.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _PATH_RE.finditer(text):
            raw = match.group(1).rstrip("/")
            # Strip trailing interpolation artifacts
            raw = re.sub(r"\$\{[^}]+\}", "{param}", raw)
            paths.add(raw)
    return tuple(sorted(paths))


def main() -> int:
    from app.bootstrap import create_app

    app = create_app()
    rules = [r.rule for r in app.url_map.iter_rules()]
    paths = collect_frontend_paths()
    bad: list[str] = []
    print("=== FRONTEND /api/v1 PATHS ===")
    for path in paths:
        ok = path_registered_in_rules(rules, path)
        print(f"{'OK' if ok else 'MISSING':7} {path}")
        if not ok:
            bad.append(path)
    print(f"\nFrontend paths missing: {len(bad)}/{len(paths)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
