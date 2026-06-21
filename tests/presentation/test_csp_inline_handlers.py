"""CSP regression: inline HTML event handlers are blocked when script-src uses nonce only."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "app" / "presentation" / "web" / "templates"
STATIC_JS = ROOT / "static" / "js"

INLINE_HANDLER = re.compile(
    r"(?<![\w.])\bon(click|change|keydown|keyup|submit|input|load)\s*=",
    re.IGNORECASE,
)

# Baseline after Batch-4 (2026-06-16): all templates migrated to data-*-action delegation.
TEMPLATE_HANDLER_BASELINE = 0
STATIC_JS_HANDLER_BASELINE = 0


def _count_handlers(paths: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        n = len(INLINE_HANDLER.findall(text))
        if n:
            counts[str(path.relative_to(ROOT)).replace("\\", "/")] = n
    return counts


def _template_paths() -> list[Path]:
    return sorted(TEMPLATES.rglob("*.html"))


def _static_js_paths() -> list[Path]:
    paths: list[Path] = []
    for path in sorted(STATIC_JS.rglob("*.js")):
        rel = path.relative_to(STATIC_JS).as_posix()
        if rel.startswith("vendor/"):
            continue
        paths.append(path)
    return paths


def test_template_inline_handlers_do_not_exceed_baseline() -> None:
    counts = _count_handlers(_template_paths())
    total = sum(counts.values())
    assert total <= TEMPLATE_HANDLER_BASELINE, (
        f"template inline handlers {total} > baseline {TEMPLATE_HANDLER_BASELINE}; "
        f"top offenders: {sorted(counts.items(), key=lambda x: -x[1])[:10]}"
    )


def test_static_js_inline_handlers_do_not_exceed_baseline() -> None:
    counts = _count_handlers(_static_js_paths())
    total = sum(counts.values())
    assert total <= STATIC_JS_HANDLER_BASELINE, (
        f"static/js inline handlers {total} > baseline {STATIC_JS_HANDLER_BASELINE}; offenders={counts}"
    )


def test_all_templates_have_no_inline_handlers() -> None:
    offenders: list[str] = []
    for path in _template_paths():
        text = path.read_text(encoding="utf-8", errors="replace")
        if INLINE_HANDLER.search(text):
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            offenders.append(rel)
    assert not offenders, f"templates with inline handlers: {offenders[:20]}"


def test_representative_pages_have_no_inline_handlers() -> None:
    """Spot-check high-traffic pages (regression guard if baseline is raised)."""
    fixed = [
        TEMPLATES / "base.html",
        TEMPLATES / "stock_detail.html",
        TEMPLATES / "daily_workbench.html",
        TEMPLATES / "ai_analysis.html",
        TEMPLATES / "observability.html",
        TEMPLATES / "message_center.html",
        TEMPLATES / "professional_workbench.html",
        TEMPLATES / "run_history.html",
    ]
    for path in fixed:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert not INLINE_HANDLER.search(text), f"{path.name} still has inline handlers"
