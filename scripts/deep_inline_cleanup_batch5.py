"""Batch 5: ai_investment_committee, quant_lab, profile, global_radar partial."""
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
    append_marker(
        CSS / "research.css",
        "/* ── Investment committee / quant lab inline cleanup ── */",
        """
.comm-hero-row { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 20px; }
.comm-hero-title { margin: 5px 0; }
.comm-symbol-bar { display: flex; gap: 10px; background: rgba(255, 255, 255, 0.6); padding: 10px; border-radius: var(--radius-md); border: 1px solid var(--surface-border); }
.comm-input-narrow { width: 140px; border: none; background: transparent; }
.comm-select-narrow { border: none; background: transparent; width: 100px; }
.comm-verdict-title { font-weight: 900; font-size: 1.2rem; text-align: center; margin-bottom: 24px; }
.comm-verdict-label { font-size: 0.8rem; opacity: 0.8; font-weight: 800; text-transform: uppercase; }
.comm-verdict-action { font-size: 2rem; font-weight: 900; }
.comm-verdict-conf { font-size: 0.9rem; font-weight: 700; margin-top: 5px; }
.comm-vote-grid { display: grid; gap: 14px; }
.comm-verdict-foot { margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(0, 0, 0, 0.05); font-size: 0.82rem; color: var(--muted); line-height: 1.6; }
.comm-bubble-icon { font-size: 1.2rem; }
.comm-bubble-body { flex: 1; }
.comm-bubble-text { font-size: 0.95rem; line-height: 1.6; color: var(--text); }
.comm-vote-row { display: flex; align-items: center; gap: 12px; }
.comm-vote-label { font-weight: 800; width: 60px; font-size: 0.8rem; color: var(--muted); }
.comm-vote-track { flex: 1; height: 8px; border-radius: 4px; background: rgba(0, 0, 0, 0.04); overflow: hidden; }
.comm-vote-fill { height: 100%; border-radius: inherit; transition: width 1.5s ease; }
.comm-vote-val { font-weight: 900; width: 45px; text-align: right; color: var(--text); }
.ql-editor-head { display: flex; justify-content: space-between; align-items: center; }
.ql-editor-title { font-weight: 900; font-size: 1.1rem; }
.ql-editor-actions { display: flex; gap: 10px; }
.ql-symbol-input { width: 120px; }
.ql-stats-row { display: flex; gap: 12px; margin-top: 10px; }
.ql-evolve-btn { margin-left: auto; }
.ql-card-title { font-weight: 800; margin-bottom: 12px; }
.ql-op-scroll { max-height: 400px; overflow-y: auto; padding-right: 5px; }
.ql-hint-sm { font-size: 0.75rem; color: var(--muted); margin-top: 12px; line-height: 1.4; }
.ql-hint-list { font-size: 0.85rem; color: var(--muted); padding-left: 18px; line-height: 1.6; }
.ql-error { color: var(--negative); }
""",
    )
    append_marker(
        CSS / "system.css",
        "/* ── Profile inline cleanup ── */",
        """
.pf-hero-row { display: flex; align-items: center; gap: 20px; }
.pf-avatar { border-radius: 50%; border: 4px solid #fff; box-shadow: var(--shadow); }
.pf-hero-title { margin: 0; }
.pf-hero-sub { margin-top: 4px; }
.pf-notify-grid { display: grid; gap: 12px; }
.pf-form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.pf-tier-note { font-size: 0.85rem; opacity: 0.9; margin-top: 10px; }
.pf-audit-name { font-weight: 700; }
.pf-audit-action { font-size: 0.85rem; }
.pf-audit-time { font-size: 0.75rem; }
.pf-notify-label { align-items: flex-start; cursor: pointer; }
.pf-notify-title { font-weight: 700; }
.pf-notify-hint { font-size: 0.75rem; }
""",
    )
    append_marker(
        CSS / "market.css",
        "/* ── Global radar JS panel cleanup ── */",
        """
.gr-grid-gap { display: grid; gap: 12px; }
.gr-grid-gap-sm { display: grid; gap: 10px; }
.gr-flex-between { display: flex; justify-content: space-between; align-items: start; gap: 12px; }
.gr-flex-row-center { display: flex; justify-content: space-between; align-items: center; }
.gr-hint-green { padding: 12px; background: rgba(16, 185, 129, 0.08); border-radius: 8px; }
.gr-font-bold { font-weight: 700; }
""",
    )

    patch(
        TPL / "ai_investment_committee.html",
        [
            (
                '<div style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:20px">',
                '<div class="comm-hero-row">',
            ),
            ('<h1 class="page-title" style="margin:5px 0">', '<h1 class="page-title comm-hero-title">'),
            (
                '<div style="display:flex; gap:10px; background:rgba(255,255,255,0.6); padding:10px; border-radius:var(--radius-md); border:1px solid var(--surface-border)">',
                '<div class="comm-symbol-bar">',
            ),
            (
                'value="600519" style="width:140px; border:none; background:transparent"',
                'value="600519" class="input-soft comm-input-narrow"',
            ),
            (
                'class="select-soft" style="border:none; background:transparent; width:100px"',
                'class="select-soft comm-select-narrow"',
            ),
            (
                '<div style="font-weight:900; font-size:1.2rem; text-align:center; margin-bottom:24px">',
                '<div class="comm-verdict-title">',
            ),
            (
                '<div style="font-size:0.8rem; opacity:0.8; font-weight:800; text-transform:uppercase">',
                '<div class="comm-verdict-label">',
            ),
            ('<div id="finalAction" style="font-size:2rem; font-weight:900">', '<div id="finalAction" class="comm-verdict-action">'),
            (
                '<div id="confidence" style="font-size:0.9rem; font-weight:700; margin-top:5px">',
                '<div id="confidence" class="comm-verdict-conf">',
            ),
            ('id="voteStats" style="display:grid; gap:14px"', 'id="voteStats" class="comm-vote-grid"'),
            (
                '<div style="margin-top:30px; padding-top:20px; border-top:1px solid rgba(0,0,0,0.05); font-size:0.82rem; color:var(--muted); line-height:1.6">',
                '<div class="comm-verdict-foot">',
            ),
            ("'<span style=\"font-size:1.2rem;\">${step.agent_avatar}</span>'", "'<span class=\"comm-bubble-icon\">${step.agent_avatar}</span>'"),
            ("'<div style=\"flex:1\">'", "'<div class=\"comm-bubble-body\">'"),
            (
                "'<div style=\"font-size:0.95rem; line-height:1.6; color:var(--text);\">${renderMarkdownSafe(step.reasoning)}</div>'",
                "'<div class=\"comm-bubble-text\">${renderMarkdownSafe(step.reasoning)}</div>'",
            ),
            ("'<div style=\"display:flex; align-items:center; gap:12px;\">'", "'<div class=\"comm-vote-row\">'"),
            (
                "'<span style=\"font-weight:800; width:60px; font-size:0.8rem; color:var(--muted);\">${labels[k]}</span>'",
                "'<span class=\"comm-vote-label\">${labels[k]}</span>'",
            ),
            (
                "'<div style=\"flex:1; height:8px; border-radius:4px; background:rgba(0,0,0,0.04); overflow:hidden;\">'",
                "'<div class=\"comm-vote-track\">'",
            ),
            (
                "'<div style=\"height:100%; width:${val}; background:${colors[k]}; border-radius:inherit; transition:width 1.5s ease;\"></div>'",
                "'<div class=\"comm-vote-fill\" style=\"width:${val}; background:${colors[k]}\"></div>'",
            ),
            (
                "'<span style=\"font-weight:900; width:45px; text-align:right; color:var(--text);\">${val}</span>'",
                "'<span class=\"comm-vote-val\">${val}</span>'",
            ),
        ],
        replace_all=True,
    )

    patch(
        TPL / "quant_lab.html",
        [
            (
                '<div style="display:flex; justify-content:space-between; align-items:center">',
                '<div class="ql-editor-head">',
            ),
            ('<div style="font-weight:900; font-size:1.1rem">', '<div class="ql-editor-title">'),
            ('<div style="display:flex; gap:10px">', '<div class="ql-editor-actions">'),
            ('value="600519" style="width:120px"', 'value="600519" class="ql-symbol-input"'),
            (
                'id="simStats" style="display:flex; gap:12px; margin-top:10px" class="qa-is-hidden"',
                'id="simStats" class="qa-is-hidden ql-stats-row"',
            ),
            ('style="margin-left:auto"', 'class="ql-evolve-btn"'),
            ('<div style="font-weight:800; margin-bottom:12px">', '<div class="ql-card-title">'),
            (
                '<div style="max-height:400px; overflow-y:auto; padding-right:5px">',
                '<div class="ql-op-scroll">',
            ),
            (
                '<p style="font-size:0.75rem; color:var(--muted); margin-top:12px; line-height:1.4">',
                '<p class="ql-hint-sm">',
            ),
            (
                '<ul style="font-size:0.85rem; color:var(--muted); padding-left:18px; line-height:1.6">',
                '<ul class="ql-hint-list">',
            ),
            ('class="loading-tile" style="color:var(--negative)"', 'class="loading-tile ql-error"'),
        ],
        replace_all=True,
    )

    patch(
        TPL / "profile.html",
        [
            ('<div style="display:flex; align-items:center; gap:20px">', '<div class="pf-hero-row">'),
            (
                'width="80" height="80" style="border-radius:50%; border:4px solid #fff; box-shadow: var(--shadow)"',
                'width="80" height="80" class="pf-avatar"',
            ),
            ('<h1 class="page-title" style="margin:0">', '<h1 class="page-title pf-hero-title">'),
            ('<p class="page-subtitle" style="margin-top:4px">', '<p class="page-subtitle pf-hero-sub">'),
            ('id="notifyGrid" style="display:grid; gap:12px"', 'id="notifyGrid" class="pf-notify-grid"'),
            (
                '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px">',
                '<div class="pf-form-grid-2">',
            ),
            (
                '<div style="font-size:0.85rem; opacity:0.9; margin-top:10px">',
                '<div class="pf-tier-note">',
            ),
            ("'<span style=\"font-weight:700;\">${f.name}</span>'", "'<span class=\"pf-audit-name\">${f.name}</span>'"),
            (
                "'<span style=\"font-size:0.85rem;\">${it.action} · ${it.target_id || ''}</span>'",
                "'<span class=\"pf-audit-action\">${it.action} · ${it.target_id || ''}</span>'",
            ),
            (
                "'<span class=\"muted\" style=\"font-size:0.75rem;\">${it.created_at.split('T')[1].slice(0,5)}</span>'",
                "'<span class=\"muted pf-audit-time\">${it.created_at.split('T')[1].slice(0,5)}</span>'",
            ),
            (
                "'<label class=\"audit-row\" style=\"align-items:flex-start;cursor:pointer;\">'",
                "'<label class=\"audit-row pf-notify-label\">'",
            ),
            ("'<div><div style=\"font-weight:700;\">' + row.label + '</div>'", "'<div><div class=\"pf-notify-title\">' + row.label + '</div>'"),
            (
                "'<div class=\"muted\" style=\"font-size:0.75rem;\">' + row.hint + '</div></div>'",
                "'<div class=\"muted pf-notify-hint\">' + row.hint + '</div></div>'",
            ),
        ],
        replace_all=True,
    )

    patch(
        TPL / "global_radar.html",
        [
            ('<div style="display:grid; gap:12px;">', '<div class="gr-grid-gap">'),
            (
                '<div style="display:flex; justify-content:space-between; align-items:start; gap:12px;">',
                '<div class="gr-flex-between">',
            ),
            ('<div class="text-sm" style="font-weight:700;">', '<div class="text-sm gr-font-bold">'),
            (
                '<div class="text-sm" style="padding:12px; background:rgba(16,185,129,0.08); border-radius:8px;">',
                '<div class="text-sm gr-hint-green">',
            ),
            ('<strong style="color:var(--positive)">', '<strong class="text-positive">'),
            ('<div style="display:grid; gap:10px;">', '<div class="gr-grid-gap-sm">'),
            (
                '<div class="trade-plan-panel" style="display:flex; justify-content:space-between; align-items:center;">',
                '<div class="trade-plan-panel gr-flex-row-center">',
            ),
        ],
        replace_all=True,
    )

    print("batch5 done")


if __name__ == "__main__":
    main()
