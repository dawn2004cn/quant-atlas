#!/usr/bin/env python3
"""Count cross-imports between context modules (architecture gate baseline)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "app" / "modules"

# Pairs that should not grow without explicit review (Phase C gate).
WATCHED_PAIRS: tuple[tuple[str, str], ...] = (
    ("system", "strategy"),
    ("system", "ai_agent"),
    ("system", "user"),
    ("strategy", "ai_agent"),
    ("strategy", "user"),
    ("ai_agent", "user"),
)

IMPORT_RE = re.compile(
    r"^\s*(?:from\s+app\.modules\.(\w+)\.|import\s+app\.modules\.(\w+)\.)",
    re.MULTILINE,
)


def count_cross_imports() -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {pair: 0 for pair in WATCHED_PAIRS}
    for py_file in MODULES.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = py_file.relative_to(MODULES)
        source = rel.parts[0] if rel.parts else ""
        for match in IMPORT_RE.finditer(text):
            target = match.group(1) or match.group(2) or ""
            if not target or target == source:
                continue
            pair = (source, target)
            if pair in counts:
                counts[pair] += 1
    return counts


# Baseline captured 2026-06-16 — gate fails only when counts increase.
BASELINE: dict[tuple[str, str], int] = {
    ("system", "strategy"): 9,
    ("system", "ai_agent"): 4,
    ("system", "user"): 4,
    ("strategy", "ai_agent"): 1,
    ("strategy", "user"): 1,
    ("ai_agent", "user"): 0,
}


def main() -> int:
    current = count_cross_imports()
    failures: list[str] = []
    for pair, baseline in BASELINE.items():
        value = current.get(pair, 0)
        if value > baseline:
            failures.append(f"{pair[0]} -> {pair[1]}: {value} > baseline {baseline}")
    if failures:
        print("Cross-module import gate FAILED (new edges detected):", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        print("\nCurrent counts:", current, file=sys.stderr)
        return 1
    print("Cross-module import gate OK:", current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
