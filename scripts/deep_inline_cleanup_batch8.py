"""Batch 8: signal_observations, zen, task_center, investment managers, factor, aics, workbench."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS_PAGES = ROOT / "static/css/pages"
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
        CSS_PAGES / "strategy.css",
        "/* ── Signal observations / obs batch8 ── */",
        """
.obs-filter-select { width: auto; min-width: 160px; }
.obs-chart-h250 { height: 250px; }
.obs-coach-shell {
    background: linear-gradient(135deg, rgba(16, 63, 145, 0.06), rgba(16, 185, 129, 0.04));
    border: 1px solid rgba(16, 63, 145, 0.12);
}
.obs-summary-pad { padding: 10px; font-weight: 700; }
.obs-empty-mt8 { margin-top: 8px; }
.obs-empty-mt10 { margin-top: 10px; }
.obs-chart-label { width: 80px; }
""",
    )
    append_marker(
        CSS_ZEN,
        "/* ── Zen dashboard batch8 ── */",
        """
.zen-mt-20 { margin-top: 20px; }
.zen-stat-mb { margin-bottom: 16px; }
.zen-alert-row { padding: 8px 0; border-bottom: 1px solid var(--zen-border); font-size: 13px; }
.zen-alert-empty { color: var(--zen-text-muted); font-size: 13px; }
""",
    )
    append_marker(
        CSS_PAGES / "system.css",
        "/* ── Task center / investment managers batch8 ── */",
        """
.tc-jobs-sm { font-size: 0.85rem; }
.tc-hint-muted { color: var(--text-muted); font-size: 0.85rem; }
.tc-steps-mt { margin-top: 10px; }
.tc-pre {
    margin: 8px 0 0; font-size: 0.75rem; white-space: pre-wrap; word-break: break-all;
}
.im-hero-links { margin-top: 12px; display: flex; gap: 12px; }
.im-intro { margin-top: 8px; line-height: 1.65; font-size: 0.92rem; }
.im-controls-mt { margin-top: 14px; }
.im-period-select { max-width: 180px; }
.im-id-sub { font-size: 12px; }
.im-cell-sm { font-size: 0.88rem; }
.pmd-hero-flex { flex: 1; min-width: 220px; }
.pmd-title { margin-bottom: 6px; }
.pmd-tagline { font-weight: 700; margin-bottom: 6px; }
.pmd-bio { margin-top: 12px; }
.pmd-date-input { max-width: 190px; }
.pmd-equity-svg { width: 100%; height: 240px; display: block; }
.pmd-chart-note { margin-top: 8px; }
.pw-hero-title { color: #fff; font-weight: 800; font-size: 1.5rem; margin: 0 0 6px; }
.pw-hero-sub { color: #94a3b8; margin: 0; font-size: 0.9rem; }
.pw-hint { font-size: 0.85rem; color: #94a3b8; margin: 0 0 12px; }
.pw-feed-scroll { max-height: 320px; }
.pw-form-mt { margin-top: 12px; }
""",
    )
    append_marker(
        CSS_PAGES / "factor.css",
        "/* ── Factor repository batch8 ── */",
        """
.fr-hero-sub { color: rgba(255, 255, 255, 0.7); }
.fr-empty-title { margin-bottom: 12px; }
.fr-empty-hint { font-size: 0.85rem; color: var(--muted); }
.fr-card-link { text-decoration: none; color: inherit; }
.fr-meta { font-size: 0.85rem; color: var(--muted); }
.fr-tag-brand { background: rgba(16, 63, 145, 0.1); color: var(--brand); }
""",
    )
    append_marker(
        CSS_PAGES / "research.css",
        "/* ── AI committee selection batch8 ── */",
        """
.aics-symbol-mt { margin-top: 4px; }
.aics-actions-mt { margin-top: 10px; }
.aics-change-mt { margin-top: 8px; font-weight: 900; }
.aics-group-count { margin: 4px 0 8px; }
.aics-rationale-mt { margin-top: 4px; }
.aics-strategy-dim { opacity: 0.45; }
""",
    )

    patch(
        TPL / "signal_observations.html",
        [
            (
                'id="obsSourceFilter" class="form-input" aria-label="按来源筛选" style="width:auto; min-width:160px"',
                'id="obsSourceFilter" class="form-input obs-filter-select" aria-label="按来源筛选"',
            ),
            ('id="returnChart" class="chart-container" style="height:250px"', 'id="returnChart" class="chart-container obs-chart-h250"'),
            (
                '<section class="section-shell" style="background: linear-gradient(135deg, rgba(16,63,145,0.06), rgba(16,185,129,0.04)); border: 1px solid rgba(16,63,145,0.12)">',
                '<section class="section-shell obs-coach-shell">',
            ),
            ('id="positionSummary" style="padding:10px; font-weight:700"', 'id="positionSummary" class="obs-summary-pad"'),
            ("'<div class=\"empty-state\" style=\"margin-top:8px;'>", "'<div class=\"empty-state obs-empty-mt8\">'"),
            ("'<div class=\"empty-state\" style=\"margin-top:10px;'>", "'<div class=\"empty-state obs-empty-mt10\">'"),
            (
                "'<span class=\"text-xs text-muted\" style=\"width:80px;\">'",
                "'<span class=\"text-xs text-muted obs-chart-label\">'",
            ),
        ],
    )

    patch(
        TPL / "zen_dashboard.html",
        [
            ('class="zen-grid zen-grid-2" style="margin-top:20px"', 'class="zen-grid zen-grid-2 zen-mt-20"'),
            ('class="zen-stat" style="margin-bottom:16px"', 'class="zen-stat zen-stat-mb"'),
            ('class="zen-glass-card zen-fade-in zen-fade-in-d3" id="zenMarket" style="margin-top:20px"', 'class="zen-glass-card zen-fade-in zen-fade-in-d3 zen-mt-20" id="zenMarket"'),
            (
                '`<div style="padding:8px 0;border-bottom:1px solid var(--zen-border);font-size:13px">',
                '`<div class="zen-alert-row">',
            ),
            (
                "'<div style=\"color:var(--zen-text-muted);font-size:13px\">No recent alerts</div>'",
                "'<div class=\"zen-alert-empty\">No recent alerts</div>'",
            ),
        ],
    )
    patch(
        TPL / "zen_dashboard.html",
        [('class="zen-stat" style="margin-bottom:16px"', 'class="zen-stat zen-stat-mb"')],
        replace_all=True,
    )

    patch(
        TPL / "task_center.html",
        [
            ('id="tcActiveJobs" class="mt-3" style="font-size:0.85rem"', 'id="tcActiveJobs" class="mt-3 tc-jobs-sm"'),
            (
                '<span style="color: var(--text-muted); font-size: 0.85rem">',
                '<span class="tc-hint-muted">',
            ),
            ("'? '<div class=\"qc-task-steps\" style=\"margin-top:10px;\">' +", "'? '<div class=\"qc-task-steps tc-steps-mt\">' +"),
            (
                "'<pre style=\"margin:8px 0 0;font-size:0.75rem;white-space:pre-wrap;word-break:break-all\">'",
                "'<pre class=\"tc-pre\">'",
            ),
        ],
    )
    patch(
        TPL / "task_center.html",
        [
            (
                "'<pre style=\"margin:8px 0 0;font-size:0.75rem;white-space:pre-wrap;word-break:break-all\">'",
                "'<pre class=\"tc-pre\">'",
            ),
        ],
        replace_all=True,
    )

    patch(
        TPL / "investment_managers.html",
        [
            ('<div style="margin-top: 12px; display: flex; gap: 12px">', '<div class="im-hero-links">'),
            (
                '<p class="text-muted" style="margin-top:8px; line-height:1.65; font-size:0.92rem">',
                '<p class="text-muted im-intro">',
            ),
            ('<div class="pm-controls" style="margin-top:14px">', '<div class="pm-controls im-controls-mt">'),
            ('id="period" class="select-soft" style="max-width:180px"', 'id="period" class="select-soft im-period-select"'),
            (
                '<div class="text-muted" style="font-size:12px;">',
                '<div class="text-muted im-id-sub">',
            ),
            ('class="text-muted" style="font-size:0.88rem"', 'class="text-muted im-cell-sm"'),
        ],
    )
    patch(
        TPL / "investment_managers.html",
        [('class="text-muted" style="font-size:0.88rem"', 'class="text-muted im-cell-sm"')],
        replace_all=True,
    )

    patch(
        TPL / "investment_manager_detail.html",
        [
            ('<div style="flex:1; min-width:220px">', '<div class="pmd-hero-flex">'),
            ('id="pmName" style="margin-bottom:6px"', 'id="pmName" class="pmd-title"'),
            ('id="pmTagline" style="font-weight:700; margin-bottom:6px"', 'id="pmTagline" class="pmd-tagline"'),
            ('id="pmBio" style="margin-top:12px"', 'id="pmBio" class="pmd-bio"'),
            ('id="date" class="input-soft" type="date" style="max-width:190px"', 'id="date" class="input-soft pmd-date-input" type="date"'),
            (
                'preserveAspectRatio="none" style="width:100%; height:240px; display:block"',
                'preserveAspectRatio="none" class="pmd-equity-svg"',
            ),
            (
                '<div class="text-muted" style="margin-top:8px">',
                '<div class="text-muted pmd-chart-note">',
            ),
        ],
    )

    patch(
        TPL / "factor_repository.html",
        [
            ('<p style="color: rgba(255,255,255,0.7)">', '<p class="fr-hero-sub">'),
            ('<div style="margin-bottom: 12px;">', '<div class="fr-empty-title">'),
            (
                '<div style="font-size: 0.85rem; color: var(--muted);">',
                '<div class="fr-empty-hint">',
            ),
            (
                'class="factor-card" style="text-decoration:none;color:inherit;"',
                'class="factor-card fr-card-link"',
            ),
            (
                '<div style="font-size:0.85rem; color:var(--muted);">',
                '<div class="fr-meta">',
            ),
            (
                '<span class="factor-tag" style="background:rgba(16,63,145,0.1);color:var(--brand);">',
                '<span class="factor-tag fr-tag-brand">',
            ),
        ],
    )

    patch(
        TPL / "ai_committee_selection.html",
        [
            (
                '<div class="aics-muted" style="margin-top:4px;">',
                '<div class="aics-muted aics-symbol-mt">',
            ),
            ('<div style="margin-top:10px;">', '<div class="aics-actions-mt">'),
            (
                '" style="margin-top:8px;font-weight:900;">',
                ' aics-change-mt">',
            ),
            (
                '<div class="aics-muted" style="margin:4px 0 8px;">',
                '<div class="aics-muted aics-group-count">',
            ),
            (
                'return `<div class="aics-strategy-item" style="${active ? \'\' : \'opacity:.45;\'}">`',
                'return `<div class="aics-strategy-item${active ? \'\' : \' aics-strategy-dim\'}">`',
            ),
            (
                '<div class="aics-muted" style="margin-top:4px;">${esc(stock.rationale)}</div>',
                '<div class="aics-muted aics-rationale-mt">${esc(stock.rationale)}</div>',
            ),
        ],
    )

    patch(
        TPL / "professional_workbench.html",
        [
            ('<h1 style="color:#fff; font-weight:800; font-size:1.5rem; margin:0 0 6px">', '<h1 class="pw-hero-title">'),
            (
                '<p style="color:#94a3b8; margin:0; font-size:.9rem">',
                '<p class="pw-hero-sub">',
            ),
            (
                '<p style="font-size:.85rem; color:#94a3b8; margin:0 0 12px">',
                '<p class="pw-hint">',
            ),
            ('id="rtFeed" style="max-height:320px"', 'id="rtFeed" class="pw-feed-scroll"'),
            ('<div class="pw-form pw-grid" style="margin-top:12px">', '<div class="pw-form pw-grid pw-form-mt">'),
        ],
    )

    patch(
        TPL / "data_lake_health.html",
        [
            ('style="margin-top:16px"', 'class="mt-16"'),
            ('style="display:flex; gap:12px; flex-wrap:wrap"', 'class="flex-wrap-gap-12"'),
        ],
        replace_all=True,
    )

    print("batch8 done")


if __name__ == "__main__":
    main()
