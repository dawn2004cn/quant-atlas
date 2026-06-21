"""Deep inline style cleanup: workbench, portfolio, stock_detail static, feature_retired."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS = ROOT / "static/css"

COMMON_MARKER = "/* ── Shared link / layout utilities (inline cleanup) ── */"
WORKBENCH_MARKER = "/* ── Inline cleanup utilities ── */"
PORTFOLIO_MARKER = "/* ── Inline cleanup utilities ── */"


def append_if_missing(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + marker + "\n" + block + "\n", encoding="utf-8")
    print(f"appended {marker[:40]}... → {path.name}")


def patch_file(rel: str, replacements: list[tuple[str, str]]) -> int:
    path = TPL / rel
    text = path.read_text(encoding="utf-8")
    n = 0
    for old, new in replacements:
        if old not in text:
            continue
        text = text.replace(old, new)
        n += 1
    if n:
        path.write_text(text, encoding="utf-8")
        print(f"{rel}: {n} replacements")
    return n


def main() -> None:
    append_if_missing(
        CSS / "common.css",
        COMMON_MARKER,
        """
.link-block { text-decoration: none; color: inherit; display: block; }
.icon-inline-mid { margin-right: 6px; vertical-align: middle; }
.text-88 { font-size: 0.88rem; }
.text-82 { font-size: 0.82rem; }
.text-78 { font-size: 0.78rem; }
.empty-state-pad { padding: 40px 20px; text-align: center; }
.mt-8px { margin-top: 8px; }
.ml-8px { margin-left: 8px; }
.scroll-panel-320 { max-height: 320px; overflow-y: auto; }
.flex-wrap-gap-8 { display: flex; flex-wrap: wrap; gap: 8px; }
.flex-wrap-gap-10 { display: flex; flex-wrap: wrap; gap: 10px; }
.btn-compact { padding: 6px 12px; font-size: 0.82rem; }
.btn-soft-compact { padding: 8px 16px; font-size: 0.86rem; }
.cursor-pointer { cursor: pointer; }
.feature-retired-card { max-width: 36rem; margin: 4rem auto; padding: 2rem; border: 1px solid var(--surface-border); border-radius: 12px; }
.feature-retired-card h1 { font-size: 1.35rem; margin-bottom: 0.75rem; }
.feature-retired-card p { color: var(--muted); line-height: 1.6; }
.feature-retired-card .fr-meta { margin-top: 1rem; font-size: 0.9rem; }
.feature-retired-card .fr-actions { margin-top: 1.5rem; }
.feature-retired-card .fr-actions .btn-soft + .btn-soft { margin-left: 0.5rem; }
.zen-nav-spacer { flex: 1; }
""",
    )
    append_if_missing(
        CSS / "pages/workbench.css",
        WORKBENCH_MARKER,
        """
.wb-hero-title { font-size: 2.5rem; margin: 0 0 8px; }
.wb-decision-copy { line-height: 1.45; }
.wb-decision-list { max-width: 100%; margin: 0; padding-left: 1.1rem; color: var(--muted); line-height: 1.45; }
.wb-trio-center { justify-content: center; margin-top: 12px; }
.wb-trio-flush { margin: 0; }
.wb-psychology-banner { margin-bottom: 16px; }
.wb-mini-list-pad { padding-left: 1rem; }
.wb-glass-compact { padding: 12px; margin-bottom: 10px; border-radius: 16px; }
.wb-badge-tiny { font-size: 0.7rem; margin-left: 6px; }
""",
    )
    append_if_missing(
        CSS / "pages/portfolio.css",
        PORTFOLIO_MARKER,
        """
.pf-select-risk { min-width: 140px; }
.pf-section-spaced { margin-top: 8px; }
.pf-alloc-bar-lg { margin-bottom: 20px; height: 12px; border-radius: 6px; }
.pf-frontier-flex { margin-top: 20px; display: flex; align-items: center; justify-content: center; color: var(--muted); }
.pf-import-field { margin-bottom: 12px; }
.pf-form-label { display: block; margin-bottom: 8px; font-weight: 600; }
.pf-form-label-sm { display: block; margin-bottom: 4px; font-weight: 600; }
.pf-file-input { width: 100%; padding: 8px; }
.pf-header-sub { color: rgba(255, 255, 255, 0.7); }
.pf-table-scroll-x { overflow-x: auto; }
.pf-alert-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--surface-border); }
.pf-frontier-title { font-size: 1.1rem; font-weight: 700; }
.pf-frontier-muted { color: var(--muted); margin-top: 4px; }
.pf-frontier-sharpe { margin-top: 8px; }
.pf-holding-link { color: var(--text); text-decoration: none; }
.pf-holding-name { font-weight: 700; }
.pf-btn-detail { padding: 4px 10px; font-size: 0.8rem; }
""",
    )
    append_if_missing(
        CSS / "pages/stock-detail.css",
        "/* ── Score / loading utilities ── */",
        """
.sd-score-warn { color: var(--warning); }
.sd-trade-warn { border-left-color: var(--warning); }
.sd-loading-full { width: 100%; }
""",
    )

    # feature_retired
    (TPL / "feature_retired.html").write_text(
        """{% extends "layouts/minimal_base.html" %}
{% block title %}功能已下线 — Quant Atlas{% endblock %}
{% block body_class %}minimal-shell-body feature-retired-body{% endblock %}
{% block content %}
<section class="feature-retired-card">
    <h1>功能已战略下线</h1>
    <p>
        <strong>{{ feature_label }}</strong> 属于审计 P3「战略削减」范围，默认不再对用户开放，以避免误导性演示或过度工程能力干扰核心量化工作流。
    </p>
    <p class="fr-meta">
        开发/内测如需临时启用，可在环境中设置 <code>{{ env_hint }}</code> 后重启服务。
    </p>
    <p class="fr-actions">
        <a href="/" class="btn-soft">返回首页</a>
        <a href="/market-panorama" class="btn-soft">全市场行情</a>
    </p>
</section>
{% endblock %}
""",
        encoding="utf-8",
    )
    print("feature_retired.html rewritten")

    patch_file(
        "layouts/zen_base.html",
        [('      <div style="flex:1"></div>', '      <div class="zen-nav-spacer"></div>')],
    )

    patch_file(
        "daily_workbench.html",
        [
            ('style="margin-bottom:16px"', 'class="wb-psychology-banner"'),
            ('<h1 class="page-title" style="font-size: 2.5rem; margin: 0 0 8px">', '<h1 class="page-title wb-hero-title">'),
            ('id="decisionAction" style="line-height:1.45"', 'id="decisionAction" class="wb-decision-copy text-sm text-muted mt-2 px-1"'),
            ('id="decisionEvidence" style="max-width:100%; margin:0; padding-left:1.1rem; color:var(--muted); line-height:1.45"',
             'id="decisionEvidence" class="wb-decision-list text-left text-xs mt-2 px-2"'),
            ('id="decisionReasons" style="max-width:100%; margin:0; padding-left:1.1rem; color:var(--muted); line-height:1.45"',
             'id="decisionReasons" class="wb-decision-list text-left text-xs mt-2 px-2"'),
            ('class="qc-trio-actions" style="justify-content:center; margin-top:12px"', 'class="qc-trio-actions wb-trio-center"'),
            ('class="wb-layout-label" style="margin-left:8px"', 'class="wb-layout-label ml-8px"'),
            ('class="qc-trio-actions" style="margin:0"', 'class="qc-trio-actions wb-trio-flush"'),
            ("style=\"text-decoration:none;color:inherit;display:block;\"", 'class="link-block"'),
            ('class="wb-mini-list" style="padding-left:1rem;"', 'class="wb-mini-list wb-mini-list-pad"'),
            ('class="badge-soft" style="font-size:0.7rem;margin-left:6px;"', 'class="badge-soft wb-badge-tiny"'),
            ("class=\"glass-panel\" style=\"padding:12px;margin-bottom:10px;border-radius:16px;\"", 'class="glass-panel wb-glass-compact"'),
            ("style=\"font-size:0.78rem;\"", 'class="text-warning-78"'),
            ("'<div style=\"font-weight:800;color:var(--text);\">'", "'<div class=\"font-bold\">'"),
            ("style=\"color:' + hc + '\"", "class=\"font-bold\" style=\"color:' + hc + '\""),
        ],
    )

    patch_file(
        "portfolio.html",
        [
            ('style="margin-right:6px; vertical-align:middle"', 'class="icon-inline-mid"'),
            ('id="riskAversion" class="select-soft" style="min-width:140px"', 'id="riskAversion" class="select-soft pf-select-risk"'),
            ('id="optHint" style="font-size:0.88rem"', 'id="optHint" class="text-88 text-muted"'),
            ('id="btnRefresh" style="padding:6px 12px; font-size:0.82rem"', 'id="btnRefresh" class="btn-soft btn-mini btn-compact"'),
            ('class="table-responsive" style="max-height:320px; overflow-y:auto"', 'class="table-responsive scroll-panel-320"'),
            ('<span class="text-muted" style="font-size:0.82rem">偏离度></span>', '<span class="text-muted text-82">偏离度></span>'),
            ('class="text-center text-muted" style="padding:40px 20px"', 'class="text-center text-muted empty-state-pad"'),
            ('class="glass-panel" style="margin-top:8px"', 'class="glass-panel pf-section-spaced"'),
            ('<span class="text-muted" style="font-size:0.82rem">预期收益 vs 波动率</span>', '<span class="text-muted text-82">预期收益 vs 波动率</span>'),
            ('id="optimalAlloc" style="margin-bottom:20px; height:12px; border-radius:6px"', 'id="optimalAlloc" class="alloc-bar pf-alloc-bar-lg"'),
            ('id="optimalWeights" style="display:flex; flex-wrap:wrap; gap:8px"', 'id="optimalWeights" class="flex-wrap-gap-8"'),
            ('id="frontierChart" style="margin-top:20px; display:flex; align-items:center; justify-content:center; color:var(--muted)"',
             'id="frontierChart" class="frontier-chart pf-frontier-flex"'),
            ("panel.html('<div class=\"text-center text-muted\" style=\"padding:40px 20px;\">暂无偏离提醒</div>')",
             "panel.html('<div class=\"text-center text-muted empty-state-pad\">暂无偏离提醒</div>')"),
            ('<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(19,32,45,0.06);">',
             '<div class="pf-alert-row">'),
            ('chart.html(`<div style="text-align:center;">',
             'chart.html(`<div class="pf-frontier-summary">'),
            ('<div style="font-size:1.1rem;font-weight:700;">', '<div class="pf-frontier-title">'),
            ('<div style="color:var(--muted);margin-top:4px;">', '<div class="pf-frontier-muted">'),
            ('<div style="margin-top:8px;">', '<div class="pf-frontier-sharpe">'),
        ],
    )

    patch_file(
        "portfolio_detail.html",
        [
            ('<div style="margin-bottom:12px">\n            <label style="display:block; margin-bottom:8px; font-weight:600">上传 Excel 文件</label>\n            <input type="file" id="tradeFile" accept=".xls,.xlsx" style="width:100%; padding:8px">',
             '<div class="pf-import-field">\n            <label class="pf-form-label">上传 Excel 文件</label>\n            <input type="file" id="tradeFile" accept=".xls,.xlsx" class="pf-file-input">'),
            ('<div style="margin-bottom:12px">\n            <label style="display:block; margin-bottom:4px; font-weight:600">或手动输入交易记录</label>',
             '<div class="pf-import-field">\n            <label class="pf-form-label-sm">或手动输入交易记录</label>'),
            ('<div style="color: rgba(255,255,255,0.7)">组合ID:', '<div class="pf-header-sub">组合ID:'),
            ('<div style="overflow-x: auto">', '<div class="pf-table-scroll-x">'),
            ('style="color:var(--text);text-decoration:none;"', 'class="pf-holding-link"'),
            ('<td style="font-weight:700;">', '<td class="pf-holding-name">'),
            ('class="btn-soft" style="padding:4px 10px;font-size:0.8rem;"', 'class="btn-soft pf-btn-detail"'),
        ],
    )

    # stock_detail static blocks
    sd = (TPL / "stock_detail.html").read_text(encoding="utf-8")
    whale_old = """    <div id="whaleTracker">
        <div style="display:grid; gap:12px">
            <div style="display:flex; align-items:center; gap:16px; padding:16px; background:rgba(236,72,153,0.08); border-radius:12px">
                <div style="width:60px; height:60px; border-radius:50%; background:linear-gradient(135deg, #ec4899, #a855f7); display:flex; align-items:center; justify-content:center; font-size:24px">🏦</div>
                <div style="flex:1">
                    <div class="text-sm" style="font-weight:700">机构主导型</div>
                    <div class="text-xs text-muted">近期 60% 的上涨由机构资金驱动</div>
                </div>
                <div class="badge-soft" style="background:rgba(16,185,129,0.15); color:var(--positive)">健康</div>
            </div>
            
            <div class="trade-plan-panel">
                <div class="text-xs text-muted mb-2">资金流向</div>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px">
                    <div style="text-align:center; padding:8px; background:rgba(16,185,129,0.08); border-radius:8px">
                        <div class="text-lg" style="color:var(--positive)">↑ 2.3亿</div>
                        <div class="text-xs text-muted">5日主力净流入</div>
                    </div>
                    <div style="text-align:center; padding:8px; background:rgba(239,68,68,0.08); border-radius:8px">
                        <div class="text-lg" style="color:var(--negative)">↓ 8500万</div>
                        <div class="text-xs text-muted">今日主力净流出</div>
                    </div>
                </div>
            </div>
            
            <div class="trade-plan-panel" style="border-left-color:var(--warning)">
                <div class="text-xs text-muted mb-2">筹码集中度预警</div>
                <div class="text-sm"><strong>⚠️ 筹码开始分散</strong></div>
                <div class="text-xs text-muted">过去 10 日股东户数增加 12%，主力可能正在撤离</div>
            </div>
        </div>
    </div>"""
    whale_new = """    <div id="whaleTracker">
        <div class="loading-state">正在加载主力追踪...</div>
    </div>"""
    if whale_old in sd:
        sd = sd.replace(whale_old, whale_new)

    sd_repls = [
        ('class="btn-soft" style="padding:8px 16px; font-size:0.86rem"', 'class="btn-soft btn-soft-compact"'),
        ('id="tdxBlocksInner" class="mt-3" style="display:flex;flex-wrap:wrap;gap:10px"', 'id="tdxBlocksInner" class="mt-3 flex-wrap-gap-10"'),
        ('<div class="section-shell" style="background: linear-gradient(135deg, rgba(59,130,246,0.05), rgba(16,185,129,0.03)); border:1px solid rgba(59,130,246,0.1)">',
         '<div class="section-shell sd-section--blue">'),
        ('<div class="section-shell" style="background: linear-gradient(135deg, rgba(236,72,153,0.05), rgba(168,85,247,0.03)); border:1px solid rgba(236,72,153,0.15)">',
         '<div class="section-shell sd-section--pink">'),
        ('<div class="section-shell" style="background: linear-gradient(135deg, rgba(139,92,246,0.05), rgba(16,63,145,0.03)); border:1px solid rgba(139,92,246,0.1)">',
         '<div class="section-shell sd-section--violet">'),
        ('<div class="section-shell" style="background: linear-gradient(135deg, rgba(16,185,129,0.04), rgba(59,130,246,0.03)); border:1px solid rgba(16,185,129,0.15)">',
         '<div class="section-shell sd-section--green">'),
        ('<div class="section-shell" style="background: linear-gradient(135deg, rgba(99,102,241,0.05), rgba(139,92,246,0.04)); border:1px solid rgba(99,102,241,0.15)">',
         '<div class="section-shell sd-section--indigo">'),
        ('<div class="section-shell" style="background: linear-gradient(135deg, rgba(16,185,129,0.05), rgba(245,158,11,0.04)); border:1px solid rgba(16,185,129,0.15)">',
         '<div class="section-shell sd-section--emerald">'),
        ('<div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:12px; margin-top:12px">',
         '<div class="sd-grid-3">'),
        ('<strong style="color:var(--warning)">6.5/10</strong>', '<strong class="sd-score-warn">6.5/10</strong>'),
        ('class="qa-is-hidden text-center py-2" style="color:var(--muted)"', 'class="qa-is-hidden text-center py-2 sd-kline-loading"'),
        ("style=\"cursor:pointer;\"", 'class="cursor-pointer"'),
        ("style=\"cursor:default;\"", ""),
        ("'<div class=\"loading-state\" style=\"width:100%;\">'", "'<div class=\"loading-state sd-loading-full\">'"),
    ]
    for old, new in sd_repls:
        sd = sd.replace(old, new)
    (TPL / "stock_detail.html").write_text(sd, encoding="utf-8")
    print("stock_detail.html patched")

    # Fix workbench psychology banner duplicate class if broken
    wb = (TPL / "daily_workbench.html").read_text(encoding="utf-8")
    wb = wb.replace(
        'class="qa-is-hidden qc-ux-banner qc-ux-banner--danger" role="alert" class="wb-psychology-banner"',
        'class="qa-is-hidden qc-ux-banner qc-ux-banner--danger wb-psychology-banner" role="alert"',
    )
    (TPL / "daily_workbench.html").write_text(wb, encoding="utf-8")

    print("deep inline cleanup done")


if __name__ == "__main__":
    main()
