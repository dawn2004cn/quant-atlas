"""Batch 6: selection_result, research_pipeline, ai_hedge_fund, expert_teams, mid-count pages."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS = ROOT / "static/css/pages"


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
        print(f"{path.name}: {n}")
    return n


def append_marker(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + marker + "\n" + block + "\n", encoding="utf-8")
    print(f"appended → {path.name}")


def main() -> None:
    # ai-group-header toggle cursor
    research = CSS / "research.css"
    rt = research.read_text(encoding="utf-8")
    if "cursor: pointer" not in rt.split(".ai-group-header {", 1)[1].split("}", 1)[0]:
        rt = rt.replace(
            ".ai-group-header {\n    display: flex;",
            ".ai-group-header {\n    cursor: pointer;\n    display: flex;",
            1,
        )
        research.write_text(rt, encoding="utf-8")
        print("research.css: ai-group-header cursor")

    append_marker(
        CSS / "strategy.css",
        "/* ── Selection result inline cleanup ── */",
        """
.sr-task-id { color: rgba(255, 255, 255, 0.7); }
.sr-table-scroll { overflow-x: auto; }
.sr-score-chart {
    height: 200px; display: flex; align-items: flex-end; gap: 8px;
    padding: 16px; background: #f8fafc; border-radius: 12px;
}
.sr-score-loading { width: 100%; }
.sr-link-plain { color: var(--text); text-decoration: none; }
.sr-btn-compact { padding: 4px 10px; font-size: 0.8rem; }
.sr-bar-col { flex: 1; text-align: center; }
.sr-bar-range { font-size: 0.75rem; color: var(--muted); margin-top: 4px; }
.sr-bar-count { font-weight: 700; }
""",
    )
    append_marker(
        CSS / "research.css",
        "/* ── Research pipeline / hedge fund / expert teams cleanup ── */",
        """
.rp-hero-row { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 16px; }
.rp-hero-actions { display: flex; gap: 10px; margin-bottom: 12px; }
.rp-freshness-mt { margin-top: 12px; }
.rp-active-jobs { margin-top: 10px; font-size: 0.85rem; }
.rp-shell-full { height: 100%; }
.rp-runs-scroll { max-height: 360px; overflow-y: auto; }
.rp-theater-wrap {
    width: 100%; height: min(42vh, 420px); border-radius: 22px; overflow: hidden;
    border: 1px solid rgba(19, 32, 45, 0.08);
    background: linear-gradient(180deg, #0f172a, #1e293b); margin-bottom: 12px;
}
.rp-theater-canvas { width: 100%; height: 100%; display: block; }
.rp-hint-muted { font-size: 0.85rem; color: var(--muted); line-height: 1.7; }
.rp-code-sm { font-size: 0.7rem; }
.rp-td-bold { font-weight: 700; }
.ahf-run-btn { padding: 16px 40px; font-size: 1.1rem; }
.ahf-result-title { font-size: 1.3rem; font-weight: 800; margin-bottom: 4px; }
.ahf-result-sub { color: var(--muted); font-size: 0.9rem; }
.ahf-signal-meta { color: var(--muted); font-size: 0.8rem; }
.ahf-ready-msg { color: #059669; font-weight: 700; }
.et-toolbar { display: flex; gap: 12px; margin-top: 20px; }
.et-search { max-width: 300px; }
.et-filter { width: 140px; }
.et-modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.et-modal-title { margin: 0; font-weight: 800; }
.et-label { font-weight: 600; font-size: 0.85rem; }
.et-modal-actions { display: flex; gap: 12px; margin-top: 16px; }
.et-btn-flex { flex: 1; }
""",
    )

    patch(
        TPL / "selection_result.html",
        [
            ('<div style="color: rgba(255,255,255,0.7)">', '<div class="sr-task-id">'),
            ('<div style="overflow-x: auto">', '<div class="sr-table-scroll">'),
            (
                '<div id="scoreDistribution" style="height: 200px; display: flex; align-items: flex-end; gap: 8px; padding: 16px; background: #f8fafc; border-radius: 12px">',
                '<div id="scoreDistribution" class="sr-score-chart">',
            ),
            ('<div class="empty-state" style="width:100%">', '<div class="empty-state sr-score-loading">'),
            (
                '<a href="/stock/${s.code}?m=CN" style="color:var(--text);text-decoration:none;">',
                '<a href="/stock/${s.code}?m=CN" class="sr-link-plain">',
            ),
            (
                'class="btn-soft" style="padding:4px 10px;font-size:0.8rem;"',
                'class="btn-soft sr-btn-compact"',
            ),
            ('<div style="flex:1;text-align:center;">', '<div class="sr-bar-col">'),
            (
                '<div style="font-size:0.75rem;color:var(--muted);margin-top:4px;">',
                '<div class="sr-bar-range">',
            ),
            ('<div style="font-weight:700;">', '<div class="sr-bar-count">'),
        ],
    )
    patch(
        TPL / "selection_result.html",
        [
            (
                'class="btn-soft" style="padding:4px 10px;font-size:0.8rem;"',
                'class="btn-soft sr-btn-compact"',
            ),
        ],
        replace_all=True,
    )

    patch(
        TPL / "research_pipeline.html",
        [
            (
                '<div style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:16px">',
                '<div class="rp-hero-row">',
            ),
            ('<div style="display:flex; gap:10px; margin-bottom:12px">', '<div class="rp-hero-actions">'),
            (
                'id="rpFreshnessStrip" class="qa-is-hidden qc-freshness-strip" aria-live="polite" style="margin-top:12px"',
                'id="rpFreshnessStrip" class="qa-is-hidden qc-freshness-strip rp-freshness-mt" aria-live="polite"',
            ),
            ('id="rpActiveJobs" style="margin-top:10px; font-size:0.85rem"', 'id="rpActiveJobs" class="rp-active-jobs"'),
            ('<div class="section-shell" style="height:100%">', '<div class="section-shell rp-shell-full">'),
            (
                '<div class="runs-table-wrap mt-3" style="max-height:360px; overflow-y:auto">',
                '<div class="runs-table-wrap mt-3 rp-runs-scroll">',
            ),
            (
                '<div id="theaterCanvasWrap" style="width:100%; height:min(42vh,420px); border-radius:22px; overflow:hidden; border:1px solid rgba(19,32,45,0.08); background:linear-gradient(180deg,#0f172a,#1e293b); margin-bottom:12px">',
                '<div id="theaterCanvasWrap" class="rp-theater-wrap">',
            ),
            (
                '<canvas id="theaterCanvas" style="width:100%; height:100%; display:block"></canvas>',
                '<canvas id="theaterCanvas" class="rp-theater-canvas"></canvas>',
            ),
            (
                '<div style="font-size:0.85rem; color:var(--muted); line-height:1.7">',
                '<div class="rp-hint-muted">',
            ),
            ('<code style="font-size:0.7rem;">', '<code class="rp-code-sm">'),
            ('<td style="font-weight:700;">', '<td class="rp-td-bold">'),
        ],
        replace_all=True,
    )

    patch(
        TPL / "ai_hedge_fund.html",
        [
            (
                'class="ai-group-header" data-ahf-action="toggle-group" style="cursor: pointer"',
                'class="ai-group-header" data-ahf-action="toggle-group"',
            ),
            (
                '<button class="btn-brand" data-ahf-action="run-analysis" type="button" style="padding: 16px 40px; font-size: 1.1rem">',
                '<button class="btn-brand ahf-run-btn" data-ahf-action="run-analysis" type="button">',
            ),
            (
                '<h3 style="font-size: 1.3rem; font-weight: 800; margin-bottom: 4px">',
                '<h3 class="ahf-result-title">',
            ),
            (
                '<p style="color: var(--muted); font-size: 0.9rem">',
                '<p class="ahf-result-sub">',
            ),
            (
                '<span style="color: var(--muted); font-size: 0.8rem;">',
                '<span class="ahf-signal-meta">',
            ),
            (
                '<span style="color: #059669; font-weight: 700;">策略已就绪，可进入交易决策</span>',
                '<span class="ahf-ready-msg">策略已就绪，可进入交易决策</span>',
            ),
        ],
    )
    patch(
        TPL / "ai_hedge_fund.html",
        [
            (
                'class="ai-group-header" data-ahf-action="toggle-group" style="cursor: pointer"',
                'class="ai-group-header" data-ahf-action="toggle-group"',
            ),
        ],
        replace_all=True,
    )

    patch(
        TPL / "expert_teams.html",
        [
            ('<div style="display:flex; gap:12px; margin-top:20px">', '<div class="et-toolbar">'),
            (
                'id="searchTeam" class="form-input" placeholder="🔍 搜索团队..." style="max-width:300px"',
                'id="searchTeam" class="form-input et-search" placeholder="🔍 搜索团队..."',
            ),
            ('id="categoryFilter" class="form-input" style="width:140px"', 'id="categoryFilter" class="form-input et-filter"'),
            (
                '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px">',
                '<div class="et-modal-head">',
            ),
            ('<h3 id="runModalTitle" style="margin:0; font-weight:800">', '<h3 id="runModalTitle" class="et-modal-title">'),
            ('<label style="font-weight:600; font-size:0.85rem">', '<label class="et-label">'),
            ('<div style="display:flex; gap:12px; margin-top:16px">', '<div class="et-modal-actions">'),
            (
                'data-et-action="close-modal" type="button" style="flex:1"',
                'data-et-action="close-modal" type="button" class="et-btn-flex"',
            ),
            (
                'data-et-action="run-team" type="button" style="flex:1"',
                'data-et-action="run-team" type="button" class="et-btn-flex"',
            ),
        ],
    )
    patch(
        TPL / "expert_teams.html",
        [('<label style="font-weight:600; font-size:0.85rem">', '<label class="et-label">')],
        replace_all=True,
    )

    mid_pages: dict[str, list[tuple[str, str]]] = {
        "shadow_account.html": [
            ('style="cursor:pointer"', 'class="sh-cursor"'),
        ],
        "nl_strategy.html": [
            ('style="display:flex; gap:12px; flex-wrap:wrap"', 'class="flex-wrap-gap-12"'),
            ('style="flex:1; min-width:200px"', 'class="flex-1-min-200"'),
        ],
        "attribution_dashboard.html": [
            ('style="display:grid; gap:16px"', 'class="grid-gap-16"'),
            ('style="font-weight:700"', 'class="font-bold"'),
        ],
        "swarm_dashboard.html": [
            ('style="display:flex; gap:12px; flex-wrap:wrap"', 'class="flex-wrap-gap-12"'),
        ],
        "strategy_wizard.html": [
            ('style="margin-top:16px"', 'class="mt-16"'),
            ('style="display:flex; gap:12px"', 'class="flex-gap-12"'),
        ],
        "signal_observations.html": [
            ('style="display:flex; gap:8px; flex-wrap:wrap"', 'class="flex-wrap-gap-8"'),
        ],
        "task_center.html": [
            ('style="display:flex; gap:12px; flex-wrap:wrap"', 'class="flex-wrap-gap-12"'),
        ],
    }

    append_marker(
        ROOT / "static/css/common.css",
        "/* ── Batch6 utility classes ── */",
        """
.flex-wrap-gap-8 { display: flex; gap: 8px; flex-wrap: wrap; }
.flex-wrap-gap-12 { display: flex; gap: 12px; flex-wrap: wrap; }
.flex-gap-12 { display: flex; gap: 12px; }
.flex-1-min-200 { flex: 1; min-width: 200px; }
.grid-gap-16 { display: grid; gap: 16px; }
.font-bold { font-weight: 700; }
.mt-16 { margin-top: 16px; }
.sh-cursor { cursor: pointer; }
""",
    )

    for fname, pairs in mid_pages.items():
        p = TPL / fname
        if p.exists():
            patch(p, pairs, replace_all=True)

    print("batch6 done")


if __name__ == "__main__":
    main()
