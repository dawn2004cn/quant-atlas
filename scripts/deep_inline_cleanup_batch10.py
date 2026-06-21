"""Batch 10: remaining static inline styles + demo width classes."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS = ROOT / "static/css/pages"
CSS_ZEN = ROOT / "static/css/zen-finance.css"


def patch(path: Path, pairs: list[tuple[str, str]], *, replace_all: bool = False) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for old, new in pairs:
        if old not in text:
            continue
        if replace_all:
            c = text.count(old)
            text = text.replace(old, new)
            n += c
        else:
            text = text.replace(old, new, 1)
            n += 1
    if n:
        path.write_text(text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)}: {n}")
    return n


def append_marker(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + marker + "\n" + block + "\n", encoding="utf-8")
    print(f"appended → {path.name}")


def main() -> None:
    append_marker(
        CSS / "strategy.css",
        "/* ── Batch10 misc pages ── */",
        """
.sc-compare-hero {
    background: linear-gradient(135deg, rgba(16, 63, 145, 0.05), rgba(139, 92, 246, 0.04));
}
.rc-title-sm { font-size: 1.2rem; margin: 0; }
.pr-holding-val { color: #4488ff; }
.pr-warn-title { color: var(--danger); }
.exp-select { max-width: 300px; }
.er-scroll { max-height: 220px; overflow-y: auto; }
.aichat-new-btn { width: 100%; }
.al-dag { min-height: 400px; border: 1px solid #ddd; background: #f8f9fa; }
.ac-type-filter { width: 140px; }
.yb-retry-btn { margin-left: 8px; }
.nlsv-badge { font-size: 0.9rem; padding: 8px 16px; }
.moments-comment-hint { font-size: 0.85rem; }
.vb-audio { max-width: 100%; }
""",
    )
    append_marker(
        CSS / "research.css",
        "/* ── Batch10 committee / agent / report ── */",
        """
.conflict-fill.w35 { width: 35%; }
.conflict-fill.w40 { width: 40%; }
.conflict-fill.w48 { width: 48%; }
.conflict-fill.w62 { width: 62%; }
.aireport-freshness-mt { margin-top: 12px; }
""",
    )
    append_marker(
        CSS / "system.css",
        "/* ── Batch10 quality / users / truth droplet ── */",
        """
.quality-fill.w40 { width: 40%; }
.um-role-muted { color: var(--muted); font-weight: 600; }
.td-droplet-pct { font-family: var(--zen-mono); font-size: 11px; color: var(--zen-text-muted); }
""",
    )
    append_marker(
        CSS_ZEN,
        "/* ── Batch10 zen terminal ── */",
        """
.zen-truth-val { color: var(--zen-accent); }
.zen-crowd-title { color: #ff4444; }
""",
    )

    patch(
        TPL / "zen_terminal.html",
        [
            ('id="truthIndex" style="color: var(--zen-accent)"', 'id="truthIndex" class="zen-card-value zen-truth-val"'),
            ('<div class="zen-card-title" style="color:#ff4444">', '<div class="zen-card-title zen-crowd-title">'),
        ],
    )
    zt = TPL / "zen_terminal.html"
    ztt = zt.read_text(encoding="utf-8")
    ztt = ztt.replace(
        'class="zen-card-value" id="truthIndex" class="zen-card-value zen-truth-val"',
        'class="zen-card-value zen-truth-val" id="truthIndex"',
    )
    zt.write_text(ztt, encoding="utf-8")

    patch(
        TPL / "user_spectrum_hub.html",
        [
            ('<h1 style="color:#fff; font-weight:800; font-size:1.5rem; margin:0 0 6px">', '<h1 class="pw-hero-title">'),
            ('<p style="color:#94a3b8; margin:0; font-size:.9rem">', '<p class="pw-hero-sub">'),
        ],
    )

    patch(
        TPL / "task_detail.html",
        [
            ('<div style="color: rgba(255,255,255,0.7)">', '<div class="sr-task-id">'),
        ],
    )

    patch(
        TPL / "strategy_compare.html",
        [
            (
                '<div class="section-shell mb-6" style="background: linear-gradient(135deg, rgba(16,63,145,0.05), rgba(139,92,246,0.04))">',
                '<div class="section-shell mb-6 sc-compare-hero">',
            ),
        ],
    )

    patch(
        TPL / "research_canvas.html",
        [
            ('<h1 class="page-title" style="font-size:1.2rem; margin:0">', '<h1 class="page-title rc-title-sm">'),
        ],
    )

    patch(
        TPL / "portfolio_resonance.html",
        [
            ('id="holdingCount" style="color: #4488ff"', 'id="holdingCount" class="value pr-holding-val"'),
            ('<div class="card-title" style="color:var(--danger)">', '<div class="card-title pr-warn-title">'),
        ],
    )
    pr = TPL / "portfolio_resonance.html"
    prt = pr.read_text(encoding="utf-8")
    prt = prt.replace(
        'class="value" id="holdingCount" class="value pr-holding-val"',
        'class="value pr-holding-val" id="holdingCount"',
    )
    pr.write_text(prt, encoding="utf-8")

    patch(
        TPL / "experiment_reporter.html",
        [
            (
                '<select id="experimentSelect" class="form-input" style="max-width: 300px">',
                '<select id="experimentSelect" class="form-input exp-select">',
            ),
        ],
    )

    patch(
        TPL / "components/stock/evidence_replay.html",
        [
            ('<div class="mt-2" style="max-height:220px; overflow-y:auto">', '<div class="mt-2 er-scroll">'),
        ],
    )

    patch(
        TPL / "ai_research_report.html",
        [
            (
                'id="aireportFreshnessStrip" class="qa-is-hidden qc-freshness-strip" aria-live="polite" style="margin-top:12px"',
                'id="aireportFreshnessStrip" class="qa-is-hidden qc-freshness-strip aireport-freshness-mt" aria-live="polite"',
            ),
        ],
    )

    patch(
        TPL / "ai_chat.html",
        [
            (
                "'<button class=\"btn-soft\" id=\"aichat-new\" style=\"width:100%;\">新建对话</button>'",
                "'<button class=\"btn-soft aichat-new-btn\" id=\"aichat-new\">新建对话</button>'",
            ),
        ],
    )

    patch(
        TPL / "agent_lab.html",
        [
            (
                '<div id="dag-container" style="min-height: 400px; border: 1px solid #ddd; background: #f8f9fa">',
                '<div id="dag-container" class="al-dag">',
            ),
        ],
    )

    patch(
        TPL / "agent_center.html",
        [
            (
                '<select class="form-input" id="typeFilter" style="width:140px">',
                '<select class="form-input ac-type-filter" id="typeFilter">',
            ),
        ],
    )

    patch(
        TPL / "users_manage.html",
        [
            (
                '<span style="color:var(--muted);font-weight:600;">',
                '<span class="um-role-muted">',
            ),
        ],
    )

    patch(
        TPL / "yanbao_hub.html",
        [
            (
                '<button type="button" class="btn-brand btn-sm" style="margin-left:8px;" data-yb-action="retry">',
                '<button type="button" class="btn-brand btn-sm yb-retry-btn" data-yb-action="retry">',
            ),
        ],
    )

    patch(
        TPL / "nl_strategy_v2.html",
        [
            (
                ' me-2 mb-2" style="font-size:0.9rem;padding:8px 16px">',
                ' me-2 mb-2 nlsv-badge">',
            ),
        ],
    )

    patch(
        TPL / "hot_sectors.html",
        [
            (
                '<div class="blocks-list" style="max-height:640px;overflow-y:auto;">',
                '<div class="blocks-list tdx-scroll">',
            ),
            (
                '<div class="table-container" style="max-height:640px;overflow-y:auto;">',
                '<div class="table-container tdx-scroll">',
            ),
        ],
    )

    patch(
        TPL / "moments.html",
        [
            (
                '<div class="text-muted" style="font-size:0.85rem" id="cHint-${pid}" class="moments-comment-hint text-muted">',
                '<div class="moments-comment-hint text-muted" id="cHint-${pid}">',
            ),
        ],
    )

    patch(
        TPL / "swarm_dashboard.html",
        [
            (
                "prog.innerHTML = '<div class=\"mini-label\" style=\"color:var(--negative);\">'",
                "prog.innerHTML = '<div class=\"mini-label swd-err\">'",
            ),
        ],
    )

    patch(
        TPL / "components/truth/truth_droplet.html",
        [
            (
                '<span id="dropletPct-{{ droplet_id }}" style="font-family:var(--zen-mono); font-size:11px; color:var(--zen-text-muted)"></span>',
                '<span id="dropletPct-{{ droplet_id }}" class="td-droplet-pct"></span>',
            ),
        ],
    )

    patch(
        TPL / "ai_investment_committee.html",
        [
            ('conflict-fill" style="width:35%"', 'conflict-fill w35"'),
            ('conflict-fill" style="width:48%"', 'conflict-fill w48"'),
            ('conflict-fill" style="width:62%"', 'conflict-fill w62"'),
            ('conflict-fill" style="width:40%"', 'conflict-fill w40"'),
        ],
    )

    patch(
        TPL / "integration_hub.html",
        [
            ('quality-fill" id="freshBar" style="width:40%"', 'quality-fill w40" id="freshBar"'),
            ('quality-fill" id="queueBar" style="width:40%"', 'quality-fill w40" id="queueBar"'),
            ('quality-fill" id="adapterBar" style="width:40%"', 'quality-fill w40" id="adapterBar"'),
            ('quality-fill" id="warmBar" style="width:40%"', 'quality-fill w40" id="warmBar"'),
        ],
    )

    patch(
        TPL / "voice_briefing.html",
        [
            ('<audio controls :src="payload.audio_url" style="max-width:100%">', '<audio controls class="vb-audio" :src="payload.audio_url">'),
        ],
    )

    print("batch10 done")


if __name__ == "__main__":
    main()
