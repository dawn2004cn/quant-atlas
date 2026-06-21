"""Phase 3 batch 2: extract page CSS + wire templates to external stylesheets."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS_DIR = ROOT / "static/css/pages"

RESEARCH_MARKER = "/* ─── Shared research utilities"

RESEARCH_APPEND: list[tuple[str, str]] = [
    ("ai_investment_committee.html", "AI investment committee"),
    ("ai_committee_dashboard.html", "AI committee dashboard"),
    ("ai_committee_selection.html", "AI committee selection"),
    ("ai_hedge_fund.html", "AI hedge fund"),
    ("quant_lab.html", "Quant lab"),
    ("ai_research_report.html", "AI research report"),
    ("voice_briefing.html", "Voice briefing"),
    ("decision_replay_space.html", "Decision replay space"),
    ("experiment_reporter.html", "Experiment reporter"),
    ("nl_strategy.html", "NL strategy"),
    ("nl_strategy_v2.html", "NL strategy v2"),
]

SWARM_TEMPLATES: list[tuple[str, str]] = [
    ("swarm_dashboard.html", "Swarm dashboard"),
    ("swarm_designer.html", "Swarm designer"),
    ("swarm_designer_flow.html", "Swarm designer flow"),
]

RESEARCH_LINK = (
    '<link rel="stylesheet" '
    'href="{{ url_for(\'static\', filename=\'css/pages/research.css\') }}">'
)
SWARM_LINK = (
    '<link rel="stylesheet" '
    'href="{{ url_for(\'static\', filename=\'css/pages/swarm.css\') }}">'
)
CANVAS_LINK = (
    '<link rel="stylesheet" '
    'href="{{ url_for(\'static\', filename=\'css/pages/research-canvas.css\') }}">'
)
TRUTH_LINK = (
    '<link rel="stylesheet" '
    'href="{{ url_for(\'static\', filename=\'css/pages/truth.css\') }}">'
)


def extract_style(text: str) -> str:
    match = re.search(r"<style>\s*(.*?)\s*</style>", text, re.S)
    return match.group(1).strip() if match else ""


def tokenize_hero_gradients(css: str) -> str:
    return css.replace(
        "radial-gradient(circle at top right, rgba(16,63,145,0.12), transparent 35%), #fff;",
        "radial-gradient(circle at top right, color-mix(in srgb, var(--brand) 12%, transparent), transparent 35%), var(--surface-strong);",
    ).replace(
        "radial-gradient(circle at top right, rgba(16,63,145,0.12), transparent 35%),\n            #fff;",
        "radial-gradient(circle at top right, color-mix(in srgb, var(--brand) 12%, transparent), transparent 35%),\n            var(--surface-strong);",
    )


def append_research_css() -> None:
    path = CSS_DIR / "research.css"
    content = path.read_text(encoding="utf-8")
    idx = content.find(RESEARCH_MARKER)
    if idx == -1:
        raise SystemExit("research.css: shared utilities marker not found")
    head = content[:idx]
    tail = content[idx:]
    blocks: list[str] = []
    for fname, title in RESEARCH_APPEND:
        text = (TPL / fname).read_text(encoding="utf-8")
        css = tokenize_hero_gradients(extract_style(text))
        if not css:
            raise SystemExit(f"{fname}: no <style> block to extract")
        blocks.append(f"/* ─── {title} ({fname}) ──────────────────────────────────────────── */\n{css}\n\n")
    path.write_text(head + "".join(blocks) + tail, encoding="utf-8")
    print(f"research.css +{len(RESEARCH_APPEND)} sections")


def build_swarm_css() -> None:
    parts = [
        "/**\n * pages/swarm.css — Swarm 设计器 / 看板\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n"
    ]
    for fname, title in SWARM_TEMPLATES:
        css = tokenize_hero_gradients(extract_style((TPL / fname).read_text(encoding="utf-8")))
        if not css:
            raise SystemExit(f"{fname}: no <style> block")
        parts.append(f"/* ─── {title} ({fname}) ──────────────────────────────────────────── */\n{css}\n\n")
    (CSS_DIR / "swarm.css").write_text("".join(parts), encoding="utf-8")
    print("swarm.css written")


def build_research_canvas_css() -> None:
    text = (TPL / "research_canvas.html").read_text(encoding="utf-8")
    css = extract_style(text)
    if not css:
        raise SystemExit("research_canvas.html: no <style>")
    header = (
        "/**\n * pages/research-canvas.css — Research Canvas (xyflow)\n"
        " * Depends on: design-tokens.css, common.css, vendor/xyflow.css\n */\n\n"
    )
    (CSS_DIR / "research-canvas.css").write_text(header + css + "\n", encoding="utf-8")
    print("research-canvas.css written")


def build_truth_css() -> None:
    text = (TPL / "truth_droplet.html").read_text(encoding="utf-8")
    css = extract_style(text)
    if not css:
        raise SystemExit("truth_droplet.html: no <style>")
    header = (
        "/**\n * pages/truth.css — 数据真相水滴（独立页）\n"
        " * Depends on: zen-finance.css\n */\n\n"
    )
    (CSS_DIR / "truth.css").write_text(header + css + "\n", encoding="utf-8")
    print("truth.css written")


def replace_style_block(text: str, link: str) -> str:
    new_text, count = re.subn(r"<style>\s*.*?\s*</style>", link, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"expected 1 style block, replaced {count}")
    return new_text


def migrate_templates() -> None:
    for fname, _ in RESEARCH_APPEND:
        path = TPL / fname
        path.write_text(replace_style_block(path.read_text(encoding="utf-8"), RESEARCH_LINK), encoding="utf-8")
        print(f"OK research {fname}")

    for fname, _ in SWARM_TEMPLATES:
        path = TPL / fname
        path.write_text(replace_style_block(path.read_text(encoding="utf-8"), SWARM_LINK), encoding="utf-8")
        print(f"OK swarm {fname}")

    rc = TPL / "research_canvas.html"
    rc_text = rc.read_text(encoding="utf-8")
    rc.write_text(replace_style_block(rc_text, CANVAS_LINK), encoding="utf-8")
    print("OK research_canvas.html")

    td = TPL / "truth_droplet.html"
    td.write_text(replace_style_block(td.read_text(encoding="utf-8"), TRUTH_LINK), encoding="utf-8")
    print("OK truth_droplet.html")


def main() -> None:
    append_research_css()
    build_swarm_css()
    build_research_canvas_css()
    build_truth_css()
    migrate_templates()
    print("Phase 3 batch 2 complete")


if __name__ == "__main__":
    main()
