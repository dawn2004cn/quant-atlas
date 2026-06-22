#!/usr/bin/env python3
"""Gate: template inline styles must stay within migration allowlist.

- No ``<style>`` blocks outside ``error_*.html``.
- ``style=`` only in allowlisted files, counts must not exceed baseline.
- Run: ``python scripts/check_template_inline_styles.py``
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"

# Baseline after UI/CSS migration batch10 + auth (2026-06-20).
STYLE_ALLOWLIST: dict[str, int] = {
    "components/skeleton.html": 8,
    "global_radar.html": 6,
    "self_stocks.html": 5,
    "ai_investment_committee.html": 3,
    "portfolio_detail.html": 3,
    "nl_strategy.html": 2,
    "components/strategy/evidence_card.html": 2,
    "agent_center.html": 1,
    "ai_hedge_fund.html": 1,
    "factor_detail.html": 1,
    "portfolio.html": 1,
    "selection_result.html": 1,
    "signal_observations.html": 1,
    "stock_selector.html": 1,
    "strategy_compare.html": 1,
    "swarm_dashboard.html": 1,
    "truth_droplet.html": 1,
    "components/stock/resonance_meter.html": 1,
    "components/stock/live_research_lab.html": 1,
}

MAX_TOTAL_STYLE = sum(STYLE_ALLOWLIST.values())


def _rel(path: Path) -> str:
    return path.relative_to(TPL).as_posix()


def scan() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    counts: dict[str, int] = {}

    for path in sorted(TPL.rglob("*.html")):
        rel = _rel(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        n_style = text.count("style=")
        if n_style:
            counts[rel] = n_style

        if rel.startswith("error_"):
            continue
        if "<style" in text.lower():
            errors.append(f"{rel}: forbidden <style> block (use static/css/pages/)")

    for rel, n in counts.items():
        if rel not in STYLE_ALLOWLIST:
            errors.append(f"{rel}: unexpected style= ({n}); migrate to CSS or update allowlist")
        elif n > STYLE_ALLOWLIST[rel]:
            errors.append(
                f"{rel}: style= count {n} exceeds allowlist {STYLE_ALLOWLIST[rel]}"
            )

    for rel, limit in STYLE_ALLOWLIST.items():
        if rel not in counts:
            errors.append(f"{rel}: missing from templates (allowlist stale?)")
        elif counts[rel] < limit:
            errors.append(
                f"{rel}: style= count {counts[rel]} below allowlist {limit} "
                "(good cleanup — lower allowlist in check script)"
            )

    total = sum(counts.values())
    if total > MAX_TOTAL_STYLE:
        errors.append(f"total style= {total} exceeds cap {MAX_TOTAL_STYLE}")

    return errors, counts


def main() -> int:
    errors, counts = scan()
    total = sum(counts.values())
    print(f"template style= total: {total} (cap {MAX_TOTAL_STYLE})")
    print(f"allowlisted files: {len(STYLE_ALLOWLIST)}")
    if errors:
        print("\nFAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK: inline style gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
