"""Manual smoke helper — prefer ``pytest tests/smoke/test_critical_api_endpoints.py``."""

from __future__ import annotations

import sys

from app.presentation.api.route_contract import path_registered_in_rules

KEY_API_PATHS = (
    "/api/v1/global/quote",
    "/api/v1/global/history",
    "/api/v1/markets/CN/quotes",
    "/api/v1/system/task-messages",
    "/api/v1/quotes",
    "/api/v1/compliance/manifest",
    "/api/v1/jarvis/proactive",
)


def main() -> int:
    from app.bootstrap import create_app

    app = create_app()
    rules = [r.rule for r in app.url_map.iter_rules()]
    missing = [p for p in KEY_API_PATHS if not path_registered_in_rules(rules, p)]
    for path in KEY_API_PATHS:
        ok = path not in missing
        print(f"{'OK' if ok else 'MISSING':7} {path}")
    print(f"\nTotal: {len(KEY_API_PATHS) - len(missing)}/{len(KEY_API_PATHS)}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
