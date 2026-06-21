"""Batch 4: alpha_factory, marketplace, committee, factor_evolution, moments."""
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
            count = text.count(old)
            text = text.replace(old, new)
            n += count
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


def patch_alpha_factory() -> None:
    append_marker(
        CSS / "alpha-factory.css",
        "/* ── Inline cleanup utilities ── */",
        """
.af-hero-links { margin-top: 16px; }
.af-data-note { margin-top: 16px; padding: 12px; background: rgba(255, 255, 255, 0.1); border-radius: 12px; font-size: 0.8rem; }
.af-data-list { margin: 8px 0 0; padding-left: 20px; }
.af-mt-8 { margin-top: 8px; }
.af-mt-12 { margin-top: 12px; }
.af-mt-16 { margin-top: 16px; }
.af-mb-8 { margin-bottom: 8px; }
.af-goal-hint { font-size: 0.8rem; color: rgba(255, 255, 255, 0.5); }
.af-desc-box { margin-top: 8px; font-size: 0.85rem; color: var(--muted); }
.af-formula-wrap { margin-top: 8px; }
.af-formula-label { font-size: 0.8rem; color: var(--muted); margin-right: 8px; }
.af-btn-chip { padding: 4px 10px; font-size: 0.75rem; margin: 2px; }
.af-flex-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.af-date-input { width: 180px; }
.af-select-flex { flex: 1; min-width: 200px; }
.af-select-auto { width: auto; }
.af-btn-lg { padding: 14px 32px; font-size: 1rem; }
.af-btn-md { padding: 14px 32px; }
.af-result-title { font-size: 1.2rem; font-weight: 800; margin-bottom: 16px; }
.af-filter-wrap { margin-bottom: 16px; }
.af-muted-p { color: var(--muted); margin-bottom: 20px; }
.af-result-mt { margin-top: 20px; }
.af-actions-row { display: flex; gap: 16px; margin-bottom: 24px; }
.af-font-bold { font-weight: 800; }
.af-text-success { font-weight: 800; color: #10b981; }
.af-text-danger { font-weight: 800; color: #ef4444; }
.af-text-warn { margin-top: 8px; color: #f59e0b; }
.af-box-purple { margin: 8px 0; padding: 8px; background: rgba(124, 58, 237, 0.1); border-radius: 8px; }
.af-text-violet { font-size: 1.2rem; color: #7c3aed; margin-bottom: 12px; }
.af-text-muted-sm { color: var(--muted); font-size: 0.85rem; }
""",
    )
    p = TPL / "alpha_factory.html"
    patch(
        p,
        [
            ('<div style="margin-top: 16px">\n                <a href=', '<div class="af-hero-links">\n                <a href='),
            (
                '<div style="margin-top: 16px; padding: 12px; background: rgba(255,255,255,0.1); border-radius: 12px; font-size: 0.8rem">',
                '<div class="af-data-note">',
            ),
            ('<ul style="margin: 8px 0 0 0; padding-left: 20px">', '<ul class="af-data-list">'),
            ('<div style="margin-top: 8px">\n                    <strong>产生数据方式：</strong>', '<div class="af-mt-8">\n                    <strong>产生数据方式：</strong>'),
            ('<span style="font-size:0.8rem; color:rgba(255,255,255,0.5)">', '<span class="af-goal-hint">'),
            ('id="goalDescription" style="margin-top:8px; font-size:0.85rem; color:var(--muted)"', 'id="goalDescription" class="af-desc-box"'),
            ('<div style="margin-top: 8px">\n                        <span style="font-size: 0.8rem; color: var(--muted); margin-right: 8px">', '<div class="af-formula-wrap">\n                        <span class="af-formula-label">'),
            (' style="padding: 4px 10px; font-size: 0.75rem; margin: 2px"', ' class="af-btn-chip"'),
            ('<div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">', '<div class="af-flex-row">'),
            ('style="width: 180px"', 'class="af-date-input"'),
            ('<span style="color: var(--muted)">至</span>', '<span class="text-muted">至</span>'),
            ('id="searchSpace" style="flex: 1; min-width: 200px"', 'id="searchSpace" class="af-select-flex"'),
            ('style="padding: 14px 32px; font-size: 1rem"', 'class="af-btn-lg"'),
            ('<h3 style="font-size: 1.2rem; font-weight: 800; margin-bottom: 16px">', '<h3 class="af-result-title">'),
            ('<div style="margin-bottom: 16px">', '<div class="af-filter-wrap">'),
            ('id="filterRegime" style="width: auto"', 'id="filterRegime" class="af-select-auto"'),
            ('<p style="color: var(--muted); margin-bottom: 20px">', '<p class="af-muted-p">'),
            ('style="padding: 14px 32px; margin-top: 16px"', 'class="af-btn-md af-mt-16"'),
            ('style="padding: 14px 32px"', 'class="af-btn-md"'),
            ('style="margin-top: 20px"', 'class="af-result-mt"'),
            ('<div style="display: flex; gap: 16px; margin-bottom: 24px">', '<div class="af-actions-row">'),
        ],
        replace_all=True,
    )
    # JS / dynamic HTML patterns
    js_pairs = [
        ('<div style="font-weight: 800; color: #ef4444;">', '<div class="af-text-danger">'),
        ('<div style="font-weight: 800; color: #10b981;">', '<div class="af-text-success">'),
        ('<div style="font-weight: 800;">', '<div class="af-font-bold">'),
        ('<div style="margin-top: 8px; color: #f59e0b;">', '<div class="af-mt-8 af-text-warn">'),
        ('<div style="margin-top: 8px; color: var(--muted);">', '<div class="af-mt-8 text-muted">'),
        ('<div style="margin-top: 8px;">', '<div class="af-mt-8">'),
        ('<div style="color: var(--muted);">', '<div class="text-muted">'),
        ('<div style="font-size: 0.85rem; color: var(--muted); margin-top: 8px;">', '<div class="af-text-muted-sm af-mt-8">'),
        ('<span style="color: var(--muted); font-size: 0.85rem;">', '<span class="af-text-muted-sm">'),
        ('<div style="font-size: 1.2rem; color: #7c3aed; margin-bottom: 12px;">', '<div class="af-text-violet">'),
        ('<div style="font-weight: 800; margin-bottom: 8px;">', '<div class="af-font-bold af-mb-8">'),
        ('<div style="margin: 8px 0; padding: 8px; background: rgba(124,58,237,0.1); border-radius: 8px;">', '<div class="af-box-purple">'),
        ('<div style="margin-top: 12px;">', '<div class="af-mt-12">'),
        ('<div style="margin-top: 16px; color: var(--muted);">', '<div class="af-mt-16 text-muted">'),
    ]
    patch(p, js_pairs, replace_all=True)


def patch_marketplace() -> None:
    append_marker(
        CSS / "marketplace.css",
        "/* ── Inline cleanup utilities ── */",
        """
.mp-hero-title { color: #fff; font-weight: 800; font-size: 1.6rem; margin-bottom: 8px; }
.mp-hero-sub { color: #94a3b8; margin: 0; }
.mp-tab-link { text-decoration: none; }
.mp-count-label { font-size: 0.8rem; }
.mp-scroll-x { overflow-x: auto; }
.mp-scroll-x-mb { overflow-x: auto; margin-bottom: 16px; }
.mp-btn-block { width: 100%; padding: 10px; }
.mp-btn-block-mb { width: 100%; padding: 10px; margin-bottom: 16px; }
.mp-stat-spaced { margin-bottom: 20px; }
.mp-stat-xl { font-size: 2.5rem; }
.mp-header-inline { padding: 0 0 12px; border: none; }
.mp-header-gov-end { margin-left: auto; }
.mp-gov-label { font-size: 0.75rem; }
.mp-header-border-top { border-top: 1px solid rgba(124, 58, 237, 0.15); }
.mp-modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6); z-index: 9998; align-items: center; justify-content: center; }
.mp-modal-overlay:not(.qa-is-hidden) { display: flex; }
.mp-modal-panel { background: #1a1a2e; border-radius: 16px; padding: 24px; max-width: 640px; width: 92%; max-height: 80vh; overflow: auto; border: 1px solid rgba(124, 58, 237, 0.3); }
.mp-modal-panel-sm { background: #1a1a2e; border-radius: 16px; padding: 24px; max-width: 480px; width: 90%; border: 1px solid rgba(124, 58, 237, 0.3); }
.mp-modal-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
.mp-modal-title { color: #fff; margin: 0; }
.mp-modal-title-mb { color: #fff; margin: 0 0 12px; }
.mp-pre-tall { max-height: 60vh; white-space: pre-wrap; }
.mp-pre-med { max-height: 200px; }
.mp-modal-actions { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
.mp-modal-actions-row { display: flex; gap: 8px; margin-top: 12px; }
.mp-link-plain { text-decoration: none; }
.mp-link-inline { display: inline-block; text-decoration: none; }
.mp-td-muted { font-size: 0.8rem; color: #64748b; }
.mp-td-ellipsis { max-width: 140px; overflow: hidden; text-overflow: ellipsis; }
.mp-td-ellipsis-lg { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
.mp-td-mono-sm { font-size: 0.7rem; font-family: monospace; }
.mp-td-mono { font-family: monospace; }
.mp-td-date { font-size: 0.75rem; }
""",
    )
    p = TPL / "marketplace.html"
    patch(
        p,
        [
            ('<h1 style="color:#fff; font-weight:800; font-size:1.6rem; margin-bottom:8px">', '<h1 class="mp-hero-title">'),
            ('<p style="color:#94a3b8; margin:0">', '<p class="mp-hero-sub">'),
            ('style="text-decoration:none">⚡ SPA 治理</a>', 'class="mp-tab mp-tab-link">⚡ SPA 治理</a>'),
            ('id="listingCount" style="font-size:0.8rem"', 'id="listingCount" class="mp-count-label text-muted"'),
            ('<div style="overflow-x:auto; margin-bottom:16px">', '<div class="mp-scroll-x-mb">'),
            ('<div style="overflow-x:auto">', '<div class="mp-scroll-x">'),
            ('style="width:100%; padding:10px"', 'class="mp-btn-block"'),
            ('style="width:100%; padding:10px; margin-bottom:16px"', 'class="mp-btn-block-mb"'),
            ('class="mp-stat-card" style="margin-bottom:20px"', 'class="mp-stat-card mp-stat-spaced"'),
            ('id="walletBalanceDetail" style="font-size:2.5rem"', 'id="walletBalanceDetail" class="mp-stat-value mp-stat-xl"'),
            ('id="govStatsLabel" style="font-size:0.8rem"', 'id="govStatsLabel" class="mp-count-label text-muted"'),
            ('class="mp-card-header" style="padding:0 0 12px; border:none"', 'class="mp-card-header mp-header-inline"'),
            ('style="margin-left:auto"', 'class="mp-header-gov-end"'),
            ('style="font-size:0.75rem"', 'class="mp-gov-label"'),
            ('class="mp-card-header" style="border-top:1px solid rgba(124,58,237,.15)"', 'class="mp-card-header mp-header-border-top"'),
            (
                'id="govDetailModal" style="position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:9998; align-items:center; justify-content:center" class="qa-is-hidden"',
                'id="govDetailModal" class="qa-is-hidden mp-modal-overlay"',
            ),
            (
                'id="mlflowRunModal" style="position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:9998; align-items:center; justify-content:center" class="qa-is-hidden"',
                'id="mlflowRunModal" class="qa-is-hidden mp-modal-overlay"',
            ),
            (
                'id="disclosureModal" style="position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:9998; align-items:center; justify-content:center" class="qa-is-hidden"',
                'id="disclosureModal" class="qa-is-hidden mp-modal-overlay"',
            ),
            (
                '<div style="background:#1a1a2e; border-radius:16px; padding:24px; max-width:640px; width:92%; max-height:80vh; overflow:auto; border:1px solid rgba(124,58,237,.3)">',
                '<div class="mp-modal-panel">',
            ),
            (
                '<div style="background:#1a1a2e; border-radius:16px; padding:24px; max-width:480px; width:90%; border:1px solid rgba(124,58,237,.3)">',
                '<div class="mp-modal-panel-sm">',
            ),
            (
                '<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:12px">',
                '<div class="mp-modal-head">',
            ),
            ('<h3 style="color:#fff; margin:0">', '<h3 class="mp-modal-title">'),
            ('<h3 style="color:#fff; margin:0 0 12px">', '<h3 class="mp-modal-title-mb">'),
            ('class="mp-out" style="max-height:60vh; white-space:pre-wrap"', 'class="mp-out mp-pre-tall"'),
            ('id="disclosureBody" style="max-height:200px"', 'id="disclosureBody" class="mp-out mp-pre-med"'),
            (
                '<div style="margin-top:12px; display:flex; flex-wrap:wrap; gap:8px">',
                '<div class="mp-modal-actions">',
            ),
            (
                '<div style="display:flex; gap:8px; margin-top:12px">',
                '<div class="mp-modal-actions-row">',
            ),
            ('style="text-decoration:none">打开 MLflow UI</a>', 'class="mp-link-plain">打开 MLflow UI</a>'),
            ('style="display:inline-block; text-decoration:none">打开 SPA 治理深链</a>', 'class="mp-link-inline">打开 SPA 治理深链</a>'),
            ('<td style="font-size:0.8rem;color:#64748b;">', '<td class="mp-td-muted">'),
            ('<td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;">', '<td class="mp-td-ellipsis">'),
            ('<td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;">', '<td class="mp-td-ellipsis-lg">'),
            ('style="font-family:monospace;">', 'class="mp-td-mono">'),
            ('<td style="font-size:0.7rem;font-family:monospace;">', '<td class="mp-td-mono-sm">'),
            ('<td style="font-size:0.75rem;">', '<td class="mp-td-date">'),
        ],
        replace_all=True,
    )


def patch_committee_dashboard() -> None:
    append_marker(
        CSS / "research.css",
        "/* ── Committee dashboard inline cleanup ── */",
        """
.acd-hero-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
.acd-hero-caption { font-size: 0.85rem; opacity: 0.8; margin-bottom: 8px; }
.acd-hero-title { font-size: 2rem; margin: 0 0 8px; }
.acd-hero-sub { opacity: 0.8; margin: 0; }
.acd-hero-meta { text-align: right; }
.acd-risk-meta { margin-top: 12px; font-size: 0.9rem; opacity: 0.8; }
.acd-section-title { margin-bottom: 16px; }
.acd-market-name { font-weight: 700; margin-bottom: 8px; }
.regime-badge-sm { font-size: 0.8rem; }
.acd-capital-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; text-align: center; }
.acd-cap-label { font-size: 0.8rem; color: var(--muted); }
.acd-placeholder { color: var(--muted); font-size: 0.9rem; }
.acd-cta-center { text-align: center; margin: 30px 0; }
.acd-stock-grid { display: grid; gap: 12px; }
.acd-trade-wrap { margin-top: 30px; }
.acd-trade-box { background: var(--surface); border-radius: 12px; overflow: hidden; }
.acd-trade-empty { padding: 20px; color: var(--muted); }
.acd-suggestion-pill { padding: 8px 12px; background: var(--surface-strong); border-radius: 8px; margin-bottom: 8px; }
.acd-stock-row { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: var(--surface); border-radius: 12px; border-left: 4px solid var(--brand); }
.acd-stock-main { }
.acd-stock-name { font-weight: 800; font-size: 1.1rem; }
.acd-stock-strategy { font-size: 0.85rem; color: var(--muted); }
.acd-stock-price { text-align: right; }
.acd-stock-price-val { font-weight: 700; }
.acd-stock-levels { font-size: 0.8rem; color: var(--muted); }
.acd-empty-center { padding: 20px; text-align: center; color: var(--muted); }
.acd-regime-icon { font-size: 1.8rem; }
""",
    )
    p = TPL / "ai_committee_dashboard.html"
    patch(
        p,
        [
            (
                '<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px">',
                '<div class="acd-hero-row">',
            ),
            (
                '<div style="font-size:0.85rem; opacity:0.8; margin-bottom:8px">INVESTMENT COMMITTEE SYSTEM</div>',
                '<div class="acd-hero-caption">INVESTMENT COMMITTEE SYSTEM</div>',
            ),
            ('<h1 style="font-size:2rem; margin:0 0 8px 0">', '<h1 class="acd-hero-title">'),
            ('<p style="opacity:0.8; margin:0">全市场分析', '<p class="acd-hero-sub">全市场分析'),
            ('<div style="text-align:right">', '<div class="acd-hero-meta">'),
            (
                '<div style="margin-top:12px; font-size:0.9rem; opacity:0.8">',
                '<div class="acd-risk-meta">',
            ),
            ('<h3 style="margin-bottom:16px">', '<h3 class="acd-section-title">'),
            ('<div style="font-weight:700; margin-bottom:8px">', '<div class="acd-market-name">'),
            ('regime-sideways" style="font-size:0.8rem"', 'regime-sideways regime-badge-sm"'),
            (
                '<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:20px; text-align:center">',
                '<div class="acd-capital-grid">',
            ),
            ('<div style="font-size:0.8rem; color:var(--muted)">', '<div class="acd-cap-label">'),
            (
                '<div style="color:var(--muted); font-size:0.9rem">点击"开始分析"',
                '<div class="acd-placeholder">点击"开始分析"',
            ),
            ('<div style="text-align:center; margin: 30px 0">', '<div class="acd-cta-center">'),
            ('id="selectedStocks" style="display:grid; gap:12px"', 'id="selectedStocks" class="acd-stock-grid"'),
            ('<div style="margin-top:30px">', '<div class="acd-trade-wrap">'),
            (
                'id="tradeHistory" style="background:var(--surface); border-radius:12px; overflow:hidden"',
                'id="tradeHistory" class="acd-trade-box"',
            ),
            (
                '<div style="padding:20px; color:var(--muted)">暂无交易记录</div>',
                '<div class="acd-trade-empty">暂无交易记录</div>',
            ),
            (
                '`<div style="padding:8px 12px; background:var(--surface-strong); border-radius:8px; margin-bottom:8px;">${s}</div>`',
                '`<div class="acd-suggestion-pill">${s}</div>`',
            ),
            (
                """<div style="display:flex; justify-content:space-between; align-items:center; padding:16px; background:var(--surface); border-radius:12px; border-left:4px solid var(--brand);">""",
                '<div class="acd-stock-row">',
            ),
            ('<div style="font-weight:800; font-size:1.1rem;">', '<div class="acd-stock-name">'),
            ('<div style="font-size:0.85rem; color:var(--muted);">策略:', '<div class="acd-stock-strategy">策略:'),
            ('<div style="text-align:right;">', '<div class="acd-stock-price">'),
            ('<div style="font-weight:700;">¥${', '<div class="acd-stock-price-val">¥${'),
            (
                '<div style="font-size:0.8rem; color:var(--muted);">止损:',
                '<div class="acd-stock-levels">止损:',
            ),
            (
                "'<div style=\"padding:20px; text-align:center; color:var(--muted);\">当前市场不适合操作</div>'",
                "'<div class=\"acd-empty-center\">当前市场不适合操作</div>'",
            ),
            ("'<span style=\"font-size:1.8rem;\">'", "'<span class=\"acd-regime-icon\">'"),
        ],
        replace_all=True,
    )


def patch_factor_evolution() -> None:
    append_marker(
        CSS / "factor.css",
        "/* ── Factor evolution inline cleanup ── */",
        """
.fe-status-indicator { position: absolute; top: 20px; left: 20px; z-index: 10; font-weight: 700; }
.fe-legend-panel { position: absolute; bottom: 20px; left: 20px; z-index: 10; background: rgba(255, 255, 255, 0.6); padding: 10px; border-radius: 12px; border: 1px solid rgba(0, 0, 0, 0.05); }
.fe-dot-blue { background: #3b82f6; }
.fe-dot-violet { background: #8b5cf6; }
.fe-dot-amber { background: #f59e0b; }
.fe-stats-title { font-weight: 800; margin-bottom: 12px; }
.fe-stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.fe-btn-full { width: 100%; margin-top: 15px; }
.fe-node-id { font-size: 0.75rem; color: var(--muted); }
.fe-node-meta { font-size: 0.72rem; color: var(--muted); margin-top: 4px; }
.fe-field-title { font-weight: 700; margin-top: 16px; }
.fe-input-full { width: 100%; margin-top: 6px; }
.fe-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px; }
.fe-grid-2-sm { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
.fe-btn-evolve { width: 100%; margin-top: 10px; }
.fe-hint-title { font-weight: 700; margin-bottom: 8px; }
.fe-hint-list { font-size: 0.85rem; color: var(--muted); padding-left: 18px; line-height: 1.6; }
""",
    )
    patch(
        TPL / "factor_evolution.html",
        [
            ('id="statusIndicator" style="position:absolute; top:20px; left:20px; z-index:10; font-weight:700"', 'id="statusIndicator" class="fe-status-indicator"'),
            (
                '<div style="position:absolute; bottom:20px; left:20px; z-index:10; background:rgba(255,255,255,0.6); padding:10px; border-radius:12px; border:1px solid rgba(0,0,0,0.05)">',
                '<div class="fe-legend-panel">',
            ),
            ('style="background:#3b82f6"', 'class="fe-dot-blue"'),
            ('style="background:#8b5cf6"', 'class="fe-dot-violet"'),
            ('style="background:#f59e0b"', 'class="fe-dot-amber"'),
            ('<div style="font-weight:800; margin-bottom:12px">', '<div class="fe-stats-title">'),
            ('<div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px">', '<div class="fe-stats-grid">'),
            ('style="width:100%; margin-top:15px"', 'class="fe-btn-full"'),
            ('id="nodeId" style="font-size:0.75rem; color:var(--muted)"', 'id="nodeId" class="fe-node-id"'),
            ('id="nodeExpMeta" style="font-size:0.72rem; color:var(--muted); margin-top:4px"', 'id="nodeExpMeta" class="fe-node-meta"'),
            ('<div style="font-weight:700; margin-top:16px">', '<div class="fe-field-title">'),
            ('autocomplete="off" / style="width:100%; margin-top:6px"', 'autocomplete="off" class="fe-input-full"'),
            ('<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:16px">', '<div class="fe-grid-2">'),
            ('<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px">', '<div class="fe-grid-2-sm">'),
            ('data-fe-action="evolve" style="width:100%; margin-top:10px"', 'data-fe-action="evolve" class="fe-btn-evolve"'),
            ('<div style="font-weight:700; margin-bottom:8px">', '<div class="fe-hint-title">'),
            ('<ul style="font-size:0.85rem; color:var(--muted); padding-left:18px; line-height:1.6">', '<ul class="fe-hint-list">'),
        ],
        replace_all=True,
    )


def patch_moments() -> None:
    append_marker(
        CSS / "user.css",
        "/* ── Moments inline cleanup ── */",
        """
.moments-hero { background: linear-gradient(135deg, rgba(16, 63, 145, 0.05), rgba(16, 185, 129, 0.03)); border: 1px solid rgba(16, 63, 145, 0.1); }
.moments-btn-more { font-size: 0.88rem; padding: 6px 12px; }
.moments-cancel { padding: 4px 10px; font-size: 0.82rem; vertical-align: middle; }
.moments-hint { font-size: 0.8rem; }
.moments-help-pad { padding: 12px 16px; }
.moments-att-pdf { display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 4px; font-size: 0.7rem; padding: 6px; text-align: center; background: rgba(239, 68, 68, 0.06); }
.moments-att-file { display: flex; align-items: center; justify-content: center; font-size: 0.75rem; padding: 4px; text-align: center; background: rgba(100, 116, 139, 0.06); }
.moments-att-name { word-break: break-all; max-width: 100%; }
.moments-att-link { color: var(--brand); font-weight: 700; }
.moments-head-right { text-align: right; }
.moments-comments { display: none; }
.moments-comment-hint { font-size: 0.85rem; }
.moments-comment-send { font-size: 0.88rem; }
.moments-empty { padding: 18px; }
.moments-no-comments { padding: 10px 2px; font-size: 0.88rem; }
""",
    )
    p = TPL / "moments.html"
    patch(
        p,
        [
            (
                'class="section-shell card" style="background: linear-gradient(135deg, rgba(16,63,145,0.05), rgba(16,185,129,0.03)); border:1px solid rgba(16,63,145,0.1)"',
                'class="section-shell card moments-hero"',
            ),
            ('id="btnMore" class="btn-soft" type="button" style="font-size:0.88rem; padding:6px 12px"', 'id="btnMore" class="btn-soft moments-btn-more" type="button"'),
            (
                'class="qa-is-hidden composer-cancel btn-soft" id="composerCancel" style="padding:4px 10px; font-size:0.82rem; vertical-align:middle"',
                'class="qa-is-hidden composer-cancel btn-soft moments-cancel" id="composerCancel"',
            ),
            ('id="postHint" style="font-size:0.8rem"', 'id="postHint" class="moments-hint text-muted mono"'),
            ('class="moments-help section-shell card" style="padding:12px 16px"', 'class="moments-help section-shell card moments-help-pad"'),
            (
                'class="cell" style="display:flex;align-items:center;justify-content:center;flex-direction:column;gap:4px;font-size:0.7rem;padding:6px;text-align:center;background:rgba(239,68,68,0.06)"',
                'class="cell moments-att-pdf"',
            ),
            ('<span style="word-break:break-all;max-width:100%"><a href="${url}" target="_blank" rel="noopener" style="color:var(--brand);font-weight:700">', '<span class="moments-att-name"><a href="${url}" target="_blank" rel="noopener" class="moments-att-link">'),
            (
                'class="cell" style="display:flex;align-items:center;justify-content:center;font-size:0.75rem;padding:4px;text-align:center;background:rgba(100,116,139,0.06)"',
                'class="cell moments-att-file"',
            ),
            (
                'style="color:var(--brand);font-weight:700">${name||\'附件\'}</a></div>`',
                'class="moments-att-link">${name||\'附件\'}</a></div>`',
            ),
            ('<div style="text-align:right">', '<div class="moments-head-right">'),
            ('id="c-${pid}" style="display:none"', 'id="c-${pid}" class="moments-comments"'),
            ('id="cHint-${pid}">加载评论中…</div>', 'id="cHint-${pid}" class="moments-comment-hint text-muted">加载评论中…</div>'),
            ('type="button" style="font-size:0.88rem">发送</button>', 'type="button" class="moments-comment-send">发送</button>'),
            ('class="text-center text-muted" style="padding:18px">暂无动态</div>', 'class="text-center text-muted moments-empty">暂无动态</div>'),
            ("list.html('<div class=\"text-muted\" style=\"padding:10px 2px;font-size:0.88rem\">暂无评论</div>')", "list.html('<div class=\"text-muted moments-no-comments\">暂无评论</div>')"),
        ],
        replace_all=True,
    )


def main() -> None:
    patch_alpha_factory()
    patch_marketplace()
    patch_committee_dashboard()
    patch_factor_evolution()
    patch_moments()
    print("batch4 done")


if __name__ == "__main__":
    main()
