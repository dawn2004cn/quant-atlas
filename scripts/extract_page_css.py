"""Extract inline <style> blocks into pages/*.css (one-off migration helper)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS_DIR = ROOT / "static/css/pages"


def extract_style(text: str) -> str:
    match = re.search(r"<style>(.*?)</style>", text, re.S)
    return match.group(1).strip() if match else ""


def build_system_css() -> None:
    arch = (TPL / "architecture_roadmap.html").read_text(encoding="utf-8")
    css = """/**
 * pages/system.css — 系统/架构/集成类页面
 * Depends on: design-tokens.css, common.css
 */

/* ─── Architecture roadmap ─────────────────────────────────────────── */
"""
    css += extract_style(arch)
    css = css.replace(
        "radial-gradient(circle at top right, rgba(16,63,145,0.12), transparent 35%),\n            #fff;",
        "radial-gradient(circle at top right, color-mix(in srgb, var(--brand) 12%, transparent), transparent 35%),\n            var(--surface-strong);",
    )
    css += """

/* ─── Shared system utilities ────────────────────────────────────────── */
.roadmap-hero-head {
    display: flex;
    justify-content: space-between;
    gap: 18px;
    flex-wrap: wrap;
    align-items: flex-end;
}

.roadmap-panel-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
}

.roadmap-symbol-input {
    max-width: 140px;
    border-radius: 12px;
    padding: 8px 12px;
}

.roadmap-self-check {
    font-size: 0.88rem;
    margin-bottom: 14px;
}

.roadmap-beat-sync {
    font-size: 0.85rem;
}

.roadmap-active-jobs {
    font-size: 0.85rem;
    margin-top: 8px;
}

.rp-hero-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 16px;
}

.rp-hero-actions {
    display: flex;
    gap: 10px;
    margin-bottom: 12px;
}
"""
    (ROOT / "static/css/pages/system.css").write_text(css, encoding="utf-8")


def build_research_css() -> None:
    """Rebuild research.css from templates that still contain <style>, plus preserved sections."""
    path = CSS_DIR / "research.css"
    marker = "/* ─── Shared research utilities"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    idx = existing.find(marker)
    if idx == -1:
        raise SystemExit("research.css missing shared utilities marker; run migrate_phase3_batch2 first")

    # Sections already extracted (templates no longer have <style>)
    preserved = existing[:idx]

    append_sources = [
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
    tail = existing[idx:]
    extra: list[str] = []
    for fname, title in append_sources:
        text = (TPL / fname).read_text(encoding="utf-8")
        css = extract_style(text)
        if css:
            extra.append(f"/* ─── {title} ({fname}) ──────────────────────────────────────────── */\n{css}\n\n")
    if extra:
        path.write_text(preserved + "".join(extra) + tail, encoding="utf-8")
    print(f"research.css preserved {len(preserved)} chars, tail ok")


if __name__ == "__main__":
    build_system_css()
    build_research_css()
    print("done")
