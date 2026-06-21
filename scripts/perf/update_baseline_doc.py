#!/usr/bin/env python3
"""Merge smoke_benchmark.json rows into docs/perf_baseline.md table.

Usage:
  python scripts/perf/smoke_benchmark.py
  python scripts/perf/update_baseline_doc.py
  python scripts/perf/update_baseline_doc.py --json instance/perf/smoke_benchmark.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = ROOT / "instance" / "perf" / "smoke_benchmark.json"
DEFAULT_DOC = ROOT / "docs" / "perf_baseline.md"

PATH_ALIASES = {
    "system_health": "/system/health",
    "market_quotes": "/api/v1/markets/CN/quotes",
    "qlib_health": "/api/v1/qlib/health",
    "data_lake_health": "/api/v1/data-lake/health",
}


def _format_row(path: str, endpoint: dict, run_date: str) -> str:
    err = endpoint.get("error_rate", 0)
    err_pct = f"{err * 100:.2f}%" if isinstance(err, (int, float)) else str(err)
    return (
        f"| `{path}` | {endpoint.get('p50_ms', '')} | {endpoint.get('p95_ms', '')} "
        f"| {endpoint.get('p99_ms', '')} | {err_pct} | {run_date} |"
    )


def build_table_rows(report: dict, run_date: str) -> list[str]:
    rows: list[str] = []
    for item in report.get("endpoints", []):
        name = str(item.get("name", ""))
        path = str(item.get("path") or PATH_ALIASES.get(name, name))
        rows.append(_format_row(path, item, run_date))
    return rows


def patch_markdown(doc_text: str, rows: list[str]) -> str:
    header = "| 端点 | P50 (ms) | P95 (ms) | P99 (ms) | 错误率 | 日期 |"
    separator = "|------|----------|----------|----------|--------|------|"
    block = "\n".join([header, separator, *rows])

    pattern = re.compile(
        r"\| 端点 \| P50 \(ms\) \| P95 \(ms\) \| P99 \(ms\) \| 错误率 \| 日期 \|\n"
        r"\|[-| ]+\|\n"
        r"(?:\|[^\n]*\n)*",
    )
    if not pattern.search(doc_text):
        raise RuntimeError("perf_baseline.md table header not found")

    updated = pattern.sub(block + "\n", doc_text, count=1)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Update perf_baseline.md from smoke JSON")
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    json_path = Path(args.json)
    doc_path = Path(args.doc)
    report = json.loads(json_path.read_text(encoding="utf-8"))
    rows = build_table_rows(report, args.date)

    print("Rows to apply:")
    for row in rows:
        print(row)

    decision = report.get("decision", {})
    print(
        f"\nDecision: async_optimization_recommended={decision.get('async_optimization_recommended')} "
        f"({decision.get('reason', '')})"
    )

    if args.dry_run:
        return 0

    doc_text = doc_path.read_text(encoding="utf-8")
    doc_path.write_text(patch_markdown(doc_text, rows), encoding="utf-8")
    print(f"\nUpdated {doc_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
