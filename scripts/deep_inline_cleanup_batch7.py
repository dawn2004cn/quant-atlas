"""Batch 7: components + mid-count pages (resonance_meter, shadow, nl_strategy, etc.)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS_PAGES = ROOT / "static/css/pages"
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
        CSS_PAGES / "stock-detail.css",
        "/* ── Resonance meter component ── */",
        """
.rm-panel {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.06), rgba(139, 92, 246, 0.04));
    border: 1px solid rgba(59, 130, 246, 0.15);
}
.rm-grid { display: grid; gap: 12px; }
.rm-score-row { display: flex; align-items: center; gap: 16px; padding: 16px; border-radius: 12px; }
.rm-score-ring {
    width: 60px; height: 60px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
}
.rm-score-val { font-size: 22px; font-weight: 900; color: #fff; }
.rm-score-body { flex: 1; }
.rm-signal-label { font-weight: 700; }
.rm-factor-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; }
.rm-factor-card { text-align: center; }
.rm-factor-signal { font-weight: 700; }
""",
    )
    append_marker(
        CSS_PAGES / "system.css",
        "/* ── Shadow account / NL strategy cleanup ── */",
        """
.sh-upload-title { font-weight: 700; font-size: 1.1rem; }
.sh-upload-actions { display: flex; gap: 12px; margin-top: 16px; justify-content: center; }
.sh-step-title { font-weight: 700; }
.behavior-bar-fill.w40 { width: 40%; }
.behavior-bar-fill.w55 { width: 55%; }
.behavior-bar-fill.w65 { width: 65%; }
.behavior-bar-fill.w70 { width: 70%; }
.nl-toolbar { display: flex; gap: 16px; margin-top: 20px; }
.nl-market-select { width: 140px; }
.nl-symbol-input { width: 140px; }
.nl-actions { display: flex; gap: 10px; }
.nl-sub-hint { font-size: 0.85rem; color: var(--text-muted); }
.nl-tab-row { margin-bottom: 12px; }
.nl-summary-box {
    padding: 12px; background: var(--surface-raised); border-radius: 8px; font-size: 0.9rem;
}
""",
    )
    append_marker(
        CSS_PAGES / "portfolio.css",
        "/* ── Attribution dashboard cleanup ── */",
        """
.ad-toolbar { gap: 0.5rem; }
.ad-input-sm { width: 140px; }
.ad-select-auto { width: auto; }
.ad-chart-h240 { height: 240px; }
.ad-chart-h280 { height: 280px; }
.ad-metric-lg { font-size: 1.5rem; }
""",
    )
    append_marker(
        CSS_PAGES / "research.css",
        "/* ── Swarm / wizard / signal obs cleanup ── */",
        """
.swd-freshness { margin: 12px 0; }
.swd-active-jobs { font-size: 0.85rem; margin-bottom: 12px; }
.swd-toolbar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.swd-progress-mt { margin-top: 12px; }
.swd-log-row { margin: 10px 0; display: flex; gap: 8px; flex-wrap: wrap; }
.swd-dag-svg { position: absolute; left: 0; top: 0; width: 100%; height: 100%; pointer-events: none; }
.swd-err { color: var(--negative); }
.sw-risk-select {
    width: 100%; text-align: left; background: white; color: black; border: 1px solid #ccc;
}
.sw-preview-btn { width: 100%; margin-bottom: 1rem; }
.sw-badge-ai {
    background: #ffd700; font-size: 0.7rem; padding: 2px 5px; border-radius: 4px; margin-left: 5px;
}
.sw-err { color: red; }
.sw-synth-banner { margin-top: 12px; padding: 8px 12px; font-size: 0.85rem; }
.sw-preview-foot { font-size: 0.7rem; color: #999; margin-top: 1rem; }
.so-toolbar { display: flex; gap: 8px; flex-wrap: wrap; }
""",
    )

    patch(
        TPL / "components/stock/resonance_meter.html",
        [
            (
                'x-init="init()" style="background: linear-gradient(135deg, rgba(59,130,246,0.06), rgba(139,92,246,0.04)); border:1px solid rgba(59,130,246,0.15)"',
                'x-init="init()" class="rm-panel"',
            ),
            ('<div style="display:grid; gap:12px">', '<div class="rm-grid">'),
            (
                '<div : style="display:flex; align-items:center; gap:16px; padding:16px; border-radius:12px">',
                '<div class="rm-score-row" :style="scoreStyle">',
            ),
            (
                '<div style="width:60px; height:60px; border-radius:50%; display:flex; align-items:center; justify-content:center">',
                '<div class="rm-score-ring">',
            ),
            (
                '<span x-text="(data.resonance_score || 0) + \'%\'" style="font-size:22px; font-weight:900; color:#fff"></span>',
                '<span x-text="(data.resonance_score || 0) + \'%\'" class="rm-score-val"></span>',
            ),
            ('<div style="flex:1">', '<div class="rm-score-body">'),
            (
                '<div class="text-lg" x-text="data.signal_label || \'观望\'" style="font-weight:700"></div>',
                '<div class="text-lg rm-signal-label" x-text="data.signal_label || \'观望\'"></div>',
            ),
            (
                '<div style="display:grid; grid-template-columns: repeat(auto-fit,minmax(100px,1fr)); gap:10px">',
                '<div class="rm-factor-grid">',
            ),
            ('<div class="trade-plan-panel" style="text-align:center">', '<div class="trade-plan-panel rm-factor-card">'),
            (
                '<div class="text-sm" x-text="signalText(d)" style="font-weight:700"></div>',
                '<div class="text-sm rm-factor-signal" x-text="signalText(d)"></div>',
            ),
        ],
    )

    patch(
        TPL / "shadow_account.html",
        [
            (
                '<div style="font-weight: 700; font-size: 1.1rem">',
                '<div class="sh-upload-title">',
            ),
            (
                '<div style="display:flex; gap:12px; margin-top:16px; justify-content:center">',
                '<div class="sh-upload-actions">',
            ),
            ('behavior-bar-fill" style="width:65%"', 'behavior-bar-fill w65"'),
            ('behavior-bar-fill" style="width:70%"', 'behavior-bar-fill w70"'),
            ('behavior-bar-fill" style="width:55%"', 'behavior-bar-fill w55"'),
            ('behavior-bar-fill" style="width:40%"', 'behavior-bar-fill w40"'),
            ('<div style="font-weight:700">', '<div class="sh-step-title">'),
        ],
    )
    patch(
        TPL / "shadow_account.html",
        [('<div style="font-weight:700">', '<div class="sh-step-title">')],
        replace_all=True,
    )

    patch(
        TPL / "nl_strategy.html",
        [
            ('<div style="display:flex; gap:16px; margin-top:20px">', '<div class="nl-toolbar">'),
            ('id="marketType" class="form-input" style="width:140px"', 'id="marketType" class="form-input nl-market-select"'),
            (
                'value="600519" style="width:140px"',
                'value="600519" class="nl-symbol-input"',
            ),
            ('<div style="display:flex; gap:10px">', '<div class="nl-actions">'),
            (
                '<p class="page-subtitle" style="font-size:0.85rem; color:var(--text-muted)">',
                '<p class="page-subtitle nl-sub-hint">',
            ),
            ('<div class="d-flex gap-2" style="margin-bottom:12px">', '<div class="d-flex gap-2 nl-tab-row">'),
            (
                'id="strategySummary" style="padding:12px; background:var(--surface-raised); border-radius:8px; font-size:0.9rem"',
                'id="strategySummary" class="nl-summary-box"',
            ),
        ],
    )
    # Fix duplicate class on symbol input if any
    nl = TPL / "nl_strategy.html"
    nl_text = nl.read_text(encoding="utf-8")
    nl_text = nl_text.replace(
        'class="form-input" placeholder="股票代码" value="600519" class="nl-symbol-input"',
        'class="form-input nl-symbol-input" placeholder="股票代码" value="600519"',
    )
    nl.write_text(nl_text, encoding="utf-8")

    patch(
        TPL / "attribution_dashboard.html",
        [
            ('class="d-flex align-items-center flex-wrap" style="gap: 0.5rem"', 'class="d-flex align-items-center flex-wrap ad-toolbar"'),
            (
                'placeholder="策略名" style="width: 140px"',
                'placeholder="策略名" class="ad-input-sm"',
            ),
            ('id="periodSelect" style="width: auto"', 'id="periodSelect" class="ad-select-auto"'),
            ('id="styleChart" style="height: 240px"', 'id="styleChart" class="ad-chart-h240"'),
            ('id="factorChart" style="height: 280px"', 'id="factorChart" class="ad-chart-h280"'),
            ('id="sectorChart" style="height: 280px"', 'id="sectorChart" class="ad-chart-h280"'),
            ('id="slippageAvg" style="font-size: 1.5rem"', 'id="slippageAvg" class="ad-metric-lg"'),
            ('id="slippageDrag" style="font-size: 1.5rem"', 'id="slippageDrag" class="ad-metric-lg"'),
            ('id="slippageOrders" style="font-size: 1.5rem"', 'id="slippageOrders" class="ad-metric-lg"'),
        ],
    )
    # Fix attribution duplicate class on input
    ad = TPL / "attribution_dashboard.html"
    ad_text = ad.read_text(encoding="utf-8")
    ad_text = ad_text.replace(
        'class="form-control form-control-sm" id="strategyNameInput" value="我的策略" placeholder="策略名" class="ad-input-sm"',
        'class="form-control form-control-sm ad-input-sm" id="strategyNameInput" value="我的策略" placeholder="策略名"',
    )
    ad.write_text(ad_text, encoding="utf-8")

    patch(
        TPL / "swarm_dashboard.html",
        [
            (
                'id="swarmFreshnessStrip" class="qa-is-hidden qc-freshness-strip" aria-live="polite" style="margin:12px 0"',
                'id="swarmFreshnessStrip" class="qa-is-hidden qc-freshness-strip swd-freshness" aria-live="polite"',
            ),
            (
                'id="swarmActiveJobs" style="font-size:0.85rem; margin-bottom:12px"',
                'id="swarmActiveJobs" class="swd-active-jobs"',
            ),
            (
                '<div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px">',
                '<div class="swd-toolbar">',
            ),
            ('id="swarmRunProgress" style="margin-top:12px"', 'id="swarmRunProgress" class="swd-progress-mt"'),
            (
                '<svg style="position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;">',
                '<svg class="swd-dag-svg">',
            ),
            (
                '<div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap;">',
                '<div class="swd-log-row">',
            ),
            (
                "'<div class=\"mini-label\" style=\"color:var(--negative);\">'",
                "'<div class=\"mini-label swd-err\">'",
            ),
        ],
    )

    patch(
        TPL / "strategy_wizard.html",
        [
            (
                '<select id="risk_level" class="btn" style="width: 100%; text-align: left; background: white; color: black; border: 1px solid #ccc">',
                '<select id="risk_level" class="btn sw-risk-select">',
            ),
            (
                'data-wizard-action="run-preview" type="button" style="width: 100%; margin-bottom: 1rem"',
                'data-wizard-action="run-preview" type="button" class="sw-preview-btn"',
            ),
            (
                "' <span style=\"background:#ffd700; font-size:0.7rem; padding:2px 5px; border-radius:4px; margin-left:5px;\">AI 推荐</span>'",
                "' <span class=\"sw-badge-ai\">AI 推荐</span>'",
            ),
            ("'<p style=\"color:red;\">'", "'<p class=\"sw-err\">'"),
            (
                'style="margin-top:12px;padding:8px 12px;font-size:0.85rem;"',
                'class="sw-synth-banner"',
            ),
            (
                '<p style="font-size: 0.7rem; color: #999; margin-top: 1rem;">',
                '<p class="sw-preview-foot">',
            ),
        ],
    )
    patch(
        TPL / "strategy_wizard.html",
        [("'<p style=\"color:red;\">'", "'<p class=\"sw-err\">'")],
        replace_all=True,
    )

    patch(
        TPL / "signal_observations.html",
        [('<div style="display:flex; gap:8px; flex-wrap:wrap">', '<div class="so-toolbar">')],
        replace_all=True,
    )

    patch(
        TPL / "task_center.html",
        [('<div style="display:flex; gap:12px; flex-wrap:wrap">', '<div class="flex-wrap-gap-12">')],
        replace_all=True,
    )

    print("batch7 done")


if __name__ == "__main__":
    main()
