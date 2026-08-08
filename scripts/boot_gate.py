#!/usr/bin/env python3
"""CI boot gate — app must start and satisfy API v1 route contracts."""

from __future__ import annotations

import sys


def main() -> int:
    from app.bootstrap import create_app
    from app.presentation.api.route_contract import (
        LEGACY_PATH_ALIASES,
        assert_v1_route_contract,
        missing_canonical_paths,
        missing_template_fetch_paths,
    )

    app = create_app()
    rules_count = len(app.url_map._rules)
    print(f"Boot OK: {rules_count} routes")

    missing = missing_canonical_paths(app.url_map)
    if missing:
        print("MISSING canonical:", ", ".join(missing))
        return 1

    tpl_missing = missing_template_fetch_paths(app.url_map)
    if tpl_missing:
        print("MISSING template fetch:", ", ".join(tpl_missing[:30]))
        if len(tpl_missing) > 30:
            print(f"... and {len(tpl_missing) - 30} more")
        return 1

    # Strict assert (no-op unless STRICT_BOOTSTRAP / production env).
    assert_v1_route_contract(app, strict=True, check_templates=True)

    alias_count = len(LEGACY_PATH_ALIASES)
    print(f"API v1 contract OK (canonical + {alias_count} legacy aliases, templates clean)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
