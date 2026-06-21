"""Batch 9: run_history, long_term_select, ai_analysis, stock components, misc pages."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS = ROOT / "static/css/pages"
CSS_COMMON = ROOT / "static/css/common.css"


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
        "/* ── Run history / long-term select / snapshots batch9 ── */",
        """
.rh-filter-strategy { width: 160px; }
.rh-filter-market { width: 140px; }
.rh-filter-sort { width: 140px; }
.rh-run-grid { grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
.rh-modal-actions { display: flex; gap: 12px; }
.lts-hero-links { margin-top: 12px; display: flex; gap: 12px; }
.lts-form-row { display: flex; align-items: end; gap: 12px; }
.lts-report-time { font-weight: 700; margin-bottom: 10px; }
.lts-report-block { margin: 18px 0; }
.ssnap-filter-min { min-width: 220px; }
.ssnap-name-filter { width: 200px; }
.ssnap-pre-wrap { white-space: pre-wrap; }
.ssnap-symbol-filter { width: 140px; }
.sf-hint-mt { margin-top: 14px; }
.sf-row-click { cursor: pointer; }
.sf-actions { display: flex; gap: 6px; flex-wrap: wrap; }
""",
    )
    append_marker(
        CSS / "research.css",
        "/* ── AI analysis / decision replay batch9 ── */",
        """
.aa-form-grid-3 { display: grid; grid-template-columns: 1.5fr 1fr auto; gap: 16px; align-items: end; }
.aa-form-grid-2 { display: grid; grid-template-columns: 1fr 1.5fr; gap: 16px; margin-top: 16px; }
.aa-summary-min { min-height: 100px; }
.aa-evidence-wide { grid-column: span 2; }
.aa-peer-input { min-width: 120px; }
.drs-legend-investor { background: #4f46e5; }
.drs-legend-symbol { background: #22c55e; }
.drs-legend-success { background: #16a34a; }
.drs-legend-timeline { background: #38bdf8; }
.obs-hero-row { display: flex; justify-content: space-between; gap: 18px; flex-wrap: wrap; align-items: flex-end; }
.obs-freshness-mt { margin-top: 12px; }
.obs-jobs-sm { margin-top: 10px; font-size: 0.85rem; }
""",
    )
    append_marker(
        CSS / "stock-detail.css",
        "/* ── Strategy copilot / live research lab batch9 ── */",
        """
.sc-panel {
    background: linear-gradient(135deg, rgba(16, 63, 145, 0.05), rgba(23, 162, 164, 0.05));
    border: 1px solid rgba(16, 63, 145, 0.1);
}
.sc-loading { padding: 15px; border: none; background: transparent; }
.sc-exec-col { border-left: 1px solid rgba(0, 0, 0, 0.05); padding-left: 30px; }
.sc-exec-title { font-weight: 800; font-size: 0.9rem; margin-bottom: 15px; }
.sc-exec-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.lrl-panel {
    background: linear-gradient(135deg, rgba(16, 63, 145, 0.07), rgba(23, 162, 164, 0.04));
    border: 1px solid rgba(16, 63, 145, 0.15);
}
.lrl-lights { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.lrl-light-emoji { font-size: 1.5rem; font-weight: 900; }
""",
    )
    append_marker(
        CSS / "swarm.css",
        "/* ── Swarm designer batch9 ── */",
        """
.swd-preset-select { width: auto; }
.swd-symbol-input { width: 120px; }
.swd-notes-sm { font-size: 0.75rem; }
.swd-json-pre { max-height: 280px; overflow: auto; }
""",
    )
    append_marker(
        CSS / "system.css",
        "/* ── Jarvis panel / stocks manage / alert batch9 ── */",
        """
.jpp-root {
    position: fixed; bottom: 24px; right: 24px; z-index: 1900;
    max-width: 360px; width: min(360px, 92vw);
}
.jpp-card { padding: 16px; border-color: var(--brand); box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2); }
.jpp-title { color: var(--brand); }
.jpp-item { padding: 12px; }
.sm-stat-sm { font-size: 1.05rem; }
.sm-stat-path { font-size: 0.82rem; font-weight: 600; word-break: break-all; line-height: 1.35; }
.sm-load-mt { margin-top: 18px; }
.ac-select-auto { width: auto; }
.tdx-scroll { max-height: 640px; overflow-y: auto; }
.tdx-empty-pad { padding: 16px; }
""",
    )
    append_marker(
        CSS / "factor.css",
        "/* ── Factor detail batch9 ── */",
        """
.fd-bar-row { height: 100%; display: flex; align-items: flex-end; gap: 2px; }
.fd-link-plain { color: var(--text); text-decoration: none; }
.fd-name-bold { font-weight: 700; }
""",
    )
    append_marker(
        CSS / "market.css",
        "/* ── TDX blocks batch9 ── */",
        """
.tdx-scroll { max-height: 640px; overflow-y: auto; }
.tdx-empty-pad { padding: 16px; }
""",
    )
    append_marker(
        CSS_COMMON,
        "/* ── Collaboration components batch9 ── */",
        """
.ctb-panel { background: linear-gradient(135deg, rgba(23, 162, 164, 0.06), rgba(16, 63, 145, 0.04)); }
.ctb-team-select { min-width: 200px; }
.ctp-panel { background: linear-gradient(135deg, rgba(220, 53, 69, 0.05), rgba(16, 63, 145, 0.04)); }
.ctp-verdict { color: var(--brand); }
.collab-scroll-md { max-height: 400px; overflow: auto; }
.collab-scroll-sm { max-height: 320px; overflow: auto; }
.collab-challenge-input { max-width: 240px; }
""",
    )

    patch(
        TPL / "run_history.html",
        [
            ('<select class="form-input" id="filterStrategy" style="width:160px">', '<select class="form-input rh-filter-strategy" id="filterStrategy">'),
            ('<select class="form-input" id="filterMarket" style="width:140px">', '<select class="form-input rh-filter-market" id="filterMarket">'),
            ('<select class="form-input" id="filterSort" style="width:140px">', '<select class="form-input rh-filter-sort" id="filterSort">'),
            (
                '<div class="grid gap-4" id="runList" style="grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))">',
                '<div class="grid gap-4 rh-run-grid" id="runList">',
            ),
            ('<div style="display:flex; gap:12px">', '<div class="rh-modal-actions">'),
        ],
    )

    patch(
        TPL / "long_term_select.html",
        [
            ('<div style="margin-top: 12px; display: flex; gap: 12px">', '<div class="lts-hero-links">'),
            ('<div style="display:flex; align-items:end; gap:12px">', '<div class="lts-form-row">'),
            ('<div style="font-weight:700; margin-bottom: 10px;">', '<div class="lts-report-time">'),
            ('<div style="margin: 18px 0;">', '<div class="lts-report-block">'),
        ],
        replace_all=True,
    )

    patch(
        TPL / "ai_analysis.html",
        [
            (
                '<div style="display:grid; grid-template-columns: 1.5fr 1fr auto; gap:16px; align-items:end">',
                '<div class="aa-form-grid-3">',
            ),
            (
                '<div style="display:grid; grid-template-columns: 1fr 1.5fr; gap:16px; margin-top:16px">',
                '<div class="aa-form-grid-2">',
            ),
            ('id="summaryText" class="markdown-body text-lg line-height-relaxed" style="min-height:100px"', 'id="summaryText" class="markdown-body text-lg line-height-relaxed aa-summary-min"'),
            ('class="evidence-tile" style="grid-column: span 2"', 'class="evidence-tile aa-evidence-wide"'),
            ('placeholder="如 000858" style="min-width:120px"', 'placeholder="如 000858" class="input-soft aa-peer-input"'),
        ],
    )

    patch(
        TPL / "components/stock/strategy_copilot.html",
        [
            (
                'x-init="init()" style="background: linear-gradient(135deg, rgba(16,63,145,0.05), rgba(23,162,164,0.05)); border: 1px solid rgba(16,63,145,0.1)">',
                'x-init="init()">',
            ),
            ('<div class="section-shell"\n    id="strategy-copilot"', '<div class="section-shell sc-panel"\n    id="strategy-copilot"'),
            (
                'class="loading-state" style="padding:15px; border:none; background:transparent"',
                'class="loading-state sc-loading"',
            ),
            (
                '<div class="col-md-5" style="border-left: 1px solid rgba(0,0,0,0.05); padding-left:30px">',
                '<div class="col-md-5 sc-exec-col">',
            ),
            (
                '<div style="font-weight:800; font-size:0.9rem; margin-bottom:15px">',
                '<div class="sc-exec-title">',
            ),
            (
                '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px">',
                '<div class="sc-exec-grid">',
            ),
        ],
    )

    patch(
        TPL / "components/stock/live_research_lab.html",
        [
            (
                'x-init="init()" style="background:linear-gradient(135deg,rgba(16,63,145,0.07),rgba(23,162,164,0.04)); border:1px solid rgba(16,63,145,0.15)">',
                'x-init="init()">',
            ),
            ('<div class="section-shell"\n    id="live-research-lab"', '<div class="section-shell lrl-panel"\n    id="live-research-lab"'),
            (
                '<div class="mt-3" style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px">',
                '<div class="mt-3 lrl-lights">',
            ),
            (
                'x-text="lightEmoji(doc.traffic_lights[key])" style="font-size:1.5rem; font-weight:900"',
                'x-text="lightEmoji(doc.traffic_lights[key])" class="lrl-light-emoji"',
            ),
        ],
    )

    patch(
        TPL / "swarm_designer.html",
        [
            (
                '<select class="form-select form-select-sm" x-model="presetId" @change="loadPreset()" style="width:auto">',
                '<select class="form-select form-select-sm swd-preset-select" x-model="presetId" @change="loadPreset()">',
            ),
            (
                '<input type="text" class="form-control form-control-sm" x-model="topologySymbol" placeholder="标的代码" style="width:120px">',
                '<input type="text" class="form-control form-control-sm swd-symbol-input" x-model="topologySymbol" placeholder="标的代码">',
            ),
            (
                'x-text="agentTopology.topology_notes || \'\'" style="font-size:0.75rem"',
                'x-text="agentTopology.topology_notes || \'\'" class="swd-notes-sm"',
            ),
            (
                '<pre class="text-xs" x-text="jsonPreview" style="max-height:280px; overflow:auto"></pre>',
                '<pre class="text-xs swd-json-pre" x-text="jsonPreview"></pre>',
            ),
        ],
    )

    patch(
        TPL / "strategy_snapshots.html",
        [
            ('<div style="min-width: 220px">', '<div class="ssnap-filter-min">'),
            (
                '<input type="text" class="form-control form-control-sm" id="filterName" placeholder="按策略名筛选" style="width: 200px">',
                '<input type="text" class="form-control form-control-sm ssnap-name-filter" id="filterName" placeholder="按策略名筛选">',
            ),
            (
                '<pre class="small mb-2" id="rollbackSteps" style="white-space: pre-wrap"></pre>',
                '<pre class="small mb-2 ssnap-pre-wrap" id="rollbackSteps"></pre>',
            ),
            (
                '<input type="text" class="form-control form-control-sm" id="decisionFilterSymbol" placeholder="600519" style="width:140px">',
                '<input type="text" class="form-control form-control-sm ssnap-symbol-filter" id="decisionFilterSymbol" placeholder="600519">',
            ),
        ],
    )

    patch(
        TPL / "partials/jarvis_proactive_panel.html",
        [
            (
                '<div id="jarvisProactivePanel" style="position:fixed; bottom:24px; right:24px; z-index:1900; max-width:360px; width:min(360px,92vw)" class="qa-is-hidden">',
                '<div id="jarvisProactivePanel" class="qa-is-hidden jpp-root">',
            ),
            (
                '<div class="evo-card" style="padding:16px; border-color:var(--brand); box-shadow:0 12px 40px rgba(0,0,0,0.2)">',
                '<div class="evo-card jpp-card">',
            ),
            ('<strong style="color:var(--brand)">', '<strong class="jpp-title">'),
            (
                "return '<div class=\"trade-plan-panel mb-2\" style=\"padding:12px;\">'",
                "return '<div class=\"trade-plan-panel mb-2 jpp-item\">'",
            ),
        ],
    )

    patch(
        TPL / "factor_detail.html",
        [
            (
                '<div style="height:100%;display:flex;align-items:flex-end;gap:2px;">',
                '<div class="fd-bar-row">',
            ),
            (
                'href="${c.factor_id ? \'/factor/\' + c.factor_id : \'#\'}" style="color:var(--text);text-decoration:none;"',
                'href="${c.factor_id ? \'/factor/\' + c.factor_id : \'#\'}" class="fd-link-plain"',
            ),
            (
                '<span style="font-weight:700;">${c.name || c.factor_id}</span>',
                '<span class="fd-name-bold">${c.name || c.factor_id}</span>',
            ),
        ],
    )

    patch(
        TPL / "decision_replay_space.html",
        [
            ('<span style="background:#4f46e5"></span>', '<span class="drs-legend-investor"></span>'),
            ('<span style="background:#22c55e"></span>', '<span class="drs-legend-symbol"></span>'),
            ('<span style="background:#16a34a"></span>', '<span class="drs-legend-success"></span>'),
            ('<span style="background:#38bdf8"></span>', '<span class="drs-legend-timeline"></span>'),
        ],
    )

    patch(
        TPL / "observability.html",
        [
            (
                '<div style="display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; align-items:flex-end">',
                '<div class="obs-hero-row">',
            ),
            (
                'id="obsFreshnessStrip" class="qa-is-hidden qc-freshness-strip" aria-live="polite" style="margin-top:12px"',
                'id="obsFreshnessStrip" class="qa-is-hidden qc-freshness-strip obs-freshness-mt" aria-live="polite"',
            ),
            ('id="obsActiveJobs" style="margin-top:10px; font-size:0.85rem"', 'id="obsActiveJobs" class="obs-jobs-sm"'),
        ],
    )

    patch(
        TPL / "alert_center.html",
        [
            (
                '<select class="form-select form-select-sm" id="minLevel" style="width: auto">',
                '<select class="form-select form-select-sm ac-select-auto" id="minLevel">',
            ),
            (
                '<select class="form-select form-select-sm" id="category" style="width: auto">',
                '<select class="form-select form-select-sm ac-select-auto" id="category">',
            ),
            (
                '<select class="form-select form-select-sm" id="limit" style="width: auto">',
                '<select class="form-select form-select-sm ac-select-auto" id="limit">',
            ),
        ],
    )

    patch(
        TPL / "stocks_manage.html",
        [
            ('<div class="sm-stat-v" id="statLatest" style="font-size:1.05rem">', '<div class="sm-stat-v sm-stat-sm" id="statLatest">'),
            (
                '<div class="sm-stat-v" id="statDbPath" style="font-size:0.82rem; font-weight:600; word-break:break-all; line-height:1.35">',
                '<div class="sm-stat-v sm-stat-path" id="statDbPath">',
            ),
            ('<div id="loadState" class="sm-empty" style="margin-top:18px">', '<div id="loadState" class="sm-empty sm-load-mt">'),
        ],
    )

    patch(
        TPL / "signal_flag.html",
        [
            ('class="empty-hint" style="margin-top:14px"', 'class="empty-hint sf-hint-mt"'),
            ("return '<tr style=\"cursor:pointer\" data-code=\"'", "return '<tr class=\"sf-row-click\" data-code=\"'"),
            ("'<td><div style=\"display:flex;gap:6px;flex-wrap:wrap;\">'", "'<td><div class=\"sf-actions\">'"),
        ],
    )

    patch(
        TPL / "tdx_blocks.html",
        [
            ("'blocks-list' style=\"max-height:640px;overflow-y:auto;\"", "'blocks-list tdx-scroll'"),
            ("'empty-state' style=\"padding:16px;\"", "'empty-state tdx-empty-pad'"),
            ("'table-container' style=\"max-height:640px;overflow-y:auto;\"", "'table-container tdx-scroll'"),
        ],
    )

    collab_patches = [
        (
            TPL / "components/collaboration/team_context_bar.html",
            [
                (
                    'x-init="init()" style="background:linear-gradient(135deg,rgba(23,162,164,0.06),rgba(16,63,145,0.04))">',
                    'x-init="init()">',
                ),
                (
                    '<div class="section-shell"\n    id="team-context-bar"',
                    '<div class="section-shell ctb-panel"\n    id="team-context-bar"',
                ),
                (
                    '<select class="form-control form-control-sm" x-model.number="activeTeamId" @change="onTeamChange()" style="min-width:200px">',
                    '<select class="form-control form-control-sm ctb-team-select" x-model.number="activeTeamId" @change="onTeamChange()">',
                ),
            ],
        ),
        (
            TPL / "components/collaboration/cross_team_pulse.html",
            [
                (
                    'x-init="init()" style="background:linear-gradient(135deg,rgba(220,53,69,0.05),rgba(16,63,145,0.04))">',
                    'x-init="init()">',
                ),
                (
                    '<div class="section-shell"\n    id="cross-team-pulse"',
                    '<div class="section-shell ctp-panel"\n    id="cross-team-pulse"',
                ),
                ('x-show="a.meta_verdict" style="color:var(--brand)"', 'x-show="a.meta_verdict" class="ctp-verdict"'),
            ],
        ),
        (
            TPL / "components/collaboration/team_research_feed.html",
            [
                ('<div class="mt-3" style="max-height:400px; overflow:auto">', '<div class="mt-3 collab-scroll-md">'),
                (
                    '<input class="form-control form-control-sm" placeholder="逻辑挑战…" x-model="item._challenge" style="max-width:240px">',
                    '<input class="form-control form-control-sm collab-challenge-input" placeholder="逻辑挑战…" x-model="item._challenge">',
                ),
            ],
        ),
        (
            TPL / "components/collaboration/team_blackboard.html",
            [
                ('<div class="mt-3" style="max-height:320px; overflow:auto">', '<div class="mt-3 collab-scroll-sm">'),
            ],
        ),
    ]
    for path, pairs in collab_patches:
        patch(path, pairs)

    print("batch9 done")


if __name__ == "__main__":
    main()
