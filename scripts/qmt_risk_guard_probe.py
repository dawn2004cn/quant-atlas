#!/usr/bin/env python
"""CLI: run QMT × Risk Guard integration probe (simulation only).

Usage:
  python scripts/qmt_risk_guard_probe.py
  python scripts/qmt_risk_guard_probe.py --account qmt_demo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="QMT Risk Guard integration probe")
    parser.add_argument("--account", default=None, help="account_id override")
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args()

    from app.modules.execution.services.qmt_integration_probe import run_qmt_integration_probe

    report = run_qmt_integration_probe(account_id=args.account)
    payload = report.as_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"ok={payload['ok']} mode={payload['mode']} passed={payload['passed']} failed={payload['failed']}")
        for c in payload["checks"]:
            mark = "PASS" if c["passed"] else "FAIL"
            req = "REQ" if c["required"] else "OPT"
            print(f"  [{mark}/{req}] {c['id']}: {c['title']} — {c['detail']}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
