#!/usr/bin/env python3
"""Audit canonical /api/v1 paths expected by templates vs Flask url_map."""

from __future__ import annotations

import sys

from app.presentation.api.route_contract import (
    CRITICAL_ROUTE_MODULES,
    LEGACY_PATH_ALIASES,
    collect_template_fetch_paths,
    missing_canonical_paths,
    missing_template_fetch_paths,
    path_registered_in_rules,
)


def _canonical_paths() -> tuple[str, ...]:
    paths: list[str] = []
    for spec in CRITICAL_ROUTE_MODULES:
        paths.extend(spec.paths)
    for alias, _target in LEGACY_PATH_ALIASES:
        if alias not in paths:
            paths.append(alias)
    return tuple(paths)


def main() -> int:
    from app.bootstrap import create_app

    app = create_app()
    rules = [r.rule for r in app.url_map.iter_rules()]

    print("=== CANONICAL PATHS ===")
    missing = missing_canonical_paths(app.url_map)
    for path in _canonical_paths():
        ok = path_registered_in_rules(rules, path)
        print(f"{'OK' if ok else 'MISSING':7} {path}")

    print(f"\nMissing canonical: {len(missing)}/{len(_canonical_paths())}")

    print("\n=== TEMPLATE FETCH PATHS (missing) ===")
    tmpl_paths = collect_template_fetch_paths()
    bad = missing_template_fetch_paths(app.url_map)
    for path in bad[:60]:
        print("MISSING", path)
    if len(bad) > 60:
        print(f"... and {len(bad) - 60} more")
    print(f"\nTemplate fetch paths missing: {len(bad)}/{len(tmpl_paths)}")

    if missing or bad:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
