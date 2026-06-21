"""Batch 3: stock_detail remainder, retail_assistant, stock_selector."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS = ROOT / "static/css/pages"


def patch(path: Path, pairs: list[tuple[str, str]]) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for old, new in pairs:
        if old not in text:
            continue
        text = text.replace(old, new)
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
        CSS / "stock-detail.css",
        "/* ── Copilot / misc inline cleanup ── */",
        """
.sd-lhb-badge-hist { background: linear-gradient(135deg, #6c757d, #495057); }
.sd-trade-muted { border-left-color: var(--muted); }
.sd-peer-links { font-size: 0.85rem; color: var(--brand); }
.sd-copilot-row { display: flex; align-items: center; gap: 15px; }
.sd-copilot-score { font-size: 2.4rem; color: var(--brand); }
.sd-copilot-body { flex: 1; }
.sd-copilot-name { font-weight: 900; font-size: 1.1rem; color: var(--text); }
.sd-copilot-reason { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
.sd-copilot-badges { display: flex; gap: 10px; margin-top: 12px; }
.sd-badge-7 { font-size: 0.7rem; }
.sd-badge-65 { font-size: 0.65rem; }
.sd-copilot-alt { margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0, 0, 0, 0.05); }
.sd-copilot-alt-title { font-size: 0.75rem; color: var(--muted); margin-bottom: 6px; }
.sd-copilot-alt-list { display: flex; gap: 8px; flex-wrap: wrap; }
.sd-risk-score-val { font-size: 1.4rem; color: var(--brand); }
.sd-fin-table { font-size: 0.85rem; }
.sd-empty-sm { font-size: 0.8rem; }
""",
    )
    append_marker(
        CSS / "system.css",
        "/* ── Retail assistant inline cleanup ── */",
        """
.ra-quick-shell { padding: 16px 20px; }
.ra-card-free { background: linear-gradient(135deg, rgba(240, 242, 245, 0.94), rgba(248, 250, 252, 0.98)); }
.ra-card-pro {
    background: linear-gradient(135deg, rgba(16, 63, 145, 0.06), rgba(16, 63, 145, 0.12));
    border: 2px solid var(--brand);
}
.ra-card-vip {
    background: linear-gradient(135deg, rgba(180, 83, 9, 0.06), rgba(180, 83, 9, 0.12));
    border: 2px solid #b45309;
}
.ra-price { font-size: 1.8rem; font-weight: 900; margin: 12px 0; }
.ra-price-unit { font-size: 0.9rem; font-weight: 400; }
.ra-current-label { margin-top: 16px; color: var(--muted); font-size: 0.9rem; }
.ra-pill-rec { background: var(--brand); color: #fff; }
.ra-btn-full { margin-top: 16px; width: 100%; }
.ra-btn-vip {
    margin-top: 16px;
    width: 100%;
    background: #b45309;
    color: #fff;
    border-color: #b45309;
}
.ra-card-spaced { margin-bottom: 10px; }
.ra-suggestion { color: var(--brand); }
.ra-mini-list { font-size: 0.85rem; }
.ra-mini-row { padding: 4px 0; border-bottom: 1px solid rgba(0, 0, 0, 0.05); }
.ra-lifecycle-row { font-size: 0.85rem; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ra-dismiss-hint { font-size: 0.75rem; }
""",
    )
    append_marker(
        CSS / "strategy.css",
        "/* ── Stock selector inline cleanup ── */",
        """
.ss-hero-links { margin-top: 12px; display: flex; gap: 12px; }
.ss-radio-row { display: flex; gap: 14px; align-items: center; padding: 10px 0; }
.ss-radio-label { display: flex; gap: 6px; align-items: center; cursor: pointer; }
.ss-radio-label input { accent-color: var(--brand); }
.ss-section-lego {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.06), rgba(16, 185, 129, 0.04));
    border: 1px solid rgba(245, 158, 11, 0.15);
}
.ss-preset-row { display: flex; gap: 10px; flex-wrap: wrap; }
.ss-badge-preset { cursor: pointer; }
.ss-strategy-meta { font-size: 0.85em; opacity: 0.7; }
.ss-result-actions { margin-top: 16px; display: flex; gap: 12px; }
""",
    )

    patch(
        TPL / "stock_detail.html",
        [
            (
                'html += `<div class="lhb-badge" style="background:linear-gradient(135deg,#6c757d,#495057);">历史上榜记录</div>`;',
                'html += `<div class="lhb-badge sd-lhb-badge-hist">历史上榜记录</div>`;',
            ),
            (
                '<div class="trade-plan-panel" style="border-left-color: ${i.severity === \'高\' ? \'var(--negative)\' : i.severity === \'中\' ? \'var(--warning)\' : \'var(--muted)\'}">',
                '<div class="trade-plan-panel ${i.severity === \'高\' ? \'sd-trade-negative\' : i.severity === \'中\' ? \'sd-trade-warn\' : \'sd-trade-muted\'}">',
            ),
            (
                '<ul class="mb-0 mt-2" style="font-size:0.85rem;color:var(--brand);">',
                '<ul class="mb-0 mt-2 sd-peer-links">',
            ),
            (
                """            box.innerHTML = `
                <div style="display:flex; align-items:center; gap:15px;">
                    <div class="meter-score" style="font-size:2.4rem; color:var(--brand);">${pick.fit_score || '--'}</div>
                    <div style="flex:1">
                        <div style="font-weight:900; font-size:1.1rem; color:var(--text);">${pick.name || '策略分析中'}</div>
                        <div style="font-size:0.85rem; color:var(--muted); margin-top:4px;">${pick.reason || ''}</div>
                    </div>
                </div>
                <div style="display:flex; gap:10px; margin-top:12px;">
                    <span class="badge-soft" style="font-size:0.7rem">波动环境: ${d.volatility_regime || '--'}</span>
                    <span class="badge-soft" style="font-size:0.7rem">趋势特征: ${d.trend_regime || '--'}</span>
                </div>
            `;""",
                """            box.innerHTML = `
                <div class="sd-copilot-row">
                    <div class="meter-score sd-copilot-score">${pick.fit_score || '--'}</div>
                    <div class="sd-copilot-body">
                        <div class="sd-copilot-name">${pick.name || '策略分析中'}</div>
                        <div class="sd-copilot-reason">${pick.reason || ''}</div>
                    </div>
                </div>
                <div class="sd-copilot-badges">
                    <span class="badge-soft sd-badge-7">波动环境: ${d.volatility_regime || '--'}</span>
                    <span class="badge-soft sd-badge-7">趋势特征: ${d.trend_regime || '--'}</span>
                </div>
            `;""",
            ),
            (
                """                box.innerHTML += `
                    <div style="margin-top:12px;padding-top:12px;border-top:1px solid rgba(0,0,0,0.05);">
                        <div style="font-size:0.75rem;color:var(--muted);margin-bottom:6px;">备选策略:</div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            ${d.alternatives.map(a => `<span class="badge-soft" style="font-size:0.65rem">${a.name} (${a.fit_score})</span>`).join('')}
                        </div>
                    </div>
                `;""",
                """                box.innerHTML += `
                    <div class="sd-copilot-alt">
                        <div class="sd-copilot-alt-title">备选策略:</div>
                        <div class="sd-copilot-alt-list">
                            ${d.alternatives.map(a => `<span class="badge-soft sd-badge-65">${a.name} (${a.fit_score})</span>`).join('')}
                        </div>
                    </div>
                `;""",
            ),
            (
                "'<div class=\"mb-2\">风控评分 <b style=\"font-size:1.4rem;color:var(--brand);\">'",
                "'<div class=\"mb-2\">风控评分 <b class=\"sd-risk-score-val\">'",
            ),
            (
                "$('#financialTable').html(`<table class=\"table table-sm table-bordered\" style=\"font-size:0.85rem;\">${tableHtml}</table>`);",
                "$('#financialTable').html(`<table class=\"table table-sm table-bordered sd-fin-table\">${tableHtml}</table>`);",
            ),
            (
                "$(selector).html(html || '<div class=\"empty-state\" style=\"font-size:0.8rem;\">暂无数据</div>');",
                "$(selector).html(html || '<div class=\"empty-state sd-empty-sm\">暂无数据</div>');",
            ),
        ],
    )

    patch(
        TPL / "retail_assistant.html",
        [
            ('id="raQuickActions" style="padding:16px 20px"', 'id="raQuickActions" class="ra-quick-shell"'),
            ('<div class="ra-grid" style="grid-template-columns: repeat(3, minmax(0, 1fr))">', '<div class="ra-grid">'),
            (
                '<div class="ra-card" style="background:linear-gradient(135deg,rgba(240,242,245,0.94),rgba(248,250,252,0.98))">',
                '<div class="ra-card ra-card-free">',
            ),
            ('<div style="font-size:1.8rem; font-weight:900; margin:12px 0">免费</div>', '<div class="ra-price">免费</div>'),
            (
                '<div style="margin-top:16px; color:var(--muted); font-size:0.9rem">当前级别</div>',
                '<div class="ra-current-label">当前级别</div>',
            ),
            (
                '<div class="ra-card" style="background:linear-gradient(135deg,rgba(16,63,145,0.06),rgba(16,63,145,0.12)); border:2px solid var(--brand)">',
                '<div class="ra-card ra-card-pro">',
            ),
            (
                '<h3>Pro <span class="ra-pill" style="background:var(--brand); color:#fff">推荐</span></h3>',
                '<h3>Pro <span class="ra-pill ra-pill-rec">推荐</span></h3>',
            ),
            (
                '<div style="font-size:1.8rem; font-weight:900; margin:12px 0">¥99<span style="font-size:0.9rem; font-weight:400">/月</span></div>',
                '<div class="ra-price">¥99<span class="ra-price-unit">/月</span></div>',
            ),
            (
                'data-toast-type="info" style="margin-top:16px; width:100%">立即升级</button>',
                'data-toast-type="info" class="btn-brand ra-btn-full">立即升级</button>',
                # only first occurrence - pro button
            ),
            (
                '<div class="ra-card" style="background:linear-gradient(135deg,rgba(180,83,9,0.06),rgba(180,83,9,0.12)); border:2px solid #b45309">',
                '<div class="ra-card ra-card-vip">',
            ),
            (
                '<div style="font-size:1.8rem; font-weight:900; margin:12px 0">¥299<span style="font-size:0.9rem; font-weight:400">/月</span></div>',
                '<div class="ra-price">¥299<span class="ra-price-unit">/月</span></div>',
            ),
            (
                'style="margin-top:16px; width:100%; background:#b45309; color:#fff; border-color:#b45309">立即升级</button>',
                'class="btn-soft ra-btn-vip">立即升级</button>',
            ),
            (
                "return '<div class=\"ra-card\" style=\"margin-bottom:10px;\"><h3>'",
                "return '<div class=\"ra-card ra-card-spaced\"><h3>'",
            ),
            (
                "'<div class=\"text-xs mt-1\" style=\"color:var(--brand);\">'",
                "'<div class=\"text-xs mt-1 ra-suggestion\">'",
            ),
            (
                '<div class="mt-2" style="font-size:0.85rem">',
                '<div class="mt-2 ra-mini-list">',
            ),
            (
                '<div style="padding:4px 0;border-bottom:1px solid rgba(0,0,0,0.05)">',
                '<div class="ra-mini-row">',
            ),
            (
                '<div class="mt-2" style="font-size:0.85rem;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">',
                '<div class="mt-2 ra-lifecycle-row">',
            ),
            (
                '<span class="text-muted" style="font-size:0.75rem;">关闭后页面横幅仍可见</span>',
                '<span class="text-muted ra-dismiss-hint">关闭后页面横幅仍可见</span>',
            ),
        ],
    )

    # Fix Pro button - first button might have gotten wrong class if replace failed
    ra = (TPL / "retail_assistant.html").read_text(encoding="utf-8")
    ra = ra.replace(
        '<button class="btn-brand" type="button" data-ra-action="toast" data-toast-msg="Pro 订阅开发中，请添加微信: quant_atlas 详谈" data-toast-type="info" style="margin-top:16px; width:100%">立即升级</button>',
        '<button class="btn-brand ra-btn-full" type="button" data-ra-action="toast" data-toast-msg="Pro 订阅开发中，请添加微信: quant_atlas 详谈" data-toast-type="info">立即升级</button>',
    )
    (TPL / "retail_assistant.html").write_text(ra, encoding="utf-8")

    patch(
        TPL / "stock_selector.html",
        [
            (
                '<div style="margin-top: 12px; display: flex; gap: 12px">',
                '<div class="ss-hero-links">',
            ),
            (
                '<div style="display:flex; gap:14px; align-items:center; padding:10px 0">',
                '<div class="ss-radio-row">',
            ),
            (
                '<label style="display:flex; gap:6px; align-items:center; cursor:pointer">',
                '<label class="ss-radio-label">',
            ),
            ('checked style="accent-color:var(--brand)">', 'checked>'),
            ('value="mid" style="accent-color:var(--brand)">', 'value="mid">'),
            ('value="short" style="accent-color:var(--brand)">', 'value="short">'),
            (
                '<section class="section-shell" style="background: linear-gradient(135deg, rgba(245,158,11,0.06), rgba(16,185,129,0.04)); border:1px solid rgba(245,158,11,0.15)">',
                '<section class="section-shell ss-section-lego">',
            ),
            (
                '<div style="display:flex; gap:10px; flex-wrap:wrap">',
                '<div class="ss-preset-row">',
            ),
            (
                'tabindex="0" style="cursor:pointer">',
                'tabindex="0" class="ss-badge-preset">',
            ),
            (
                'id="strategyInfo" style="font-size:0.85em; opacity:0.7"',
                'id="strategyInfo" class="ss-strategy-meta"',
            ),
            (
                '<div style="margin-top: 16px; display: flex; gap: 12px">',
                '<div class="ss-result-actions">',
            ),
        ],
    )

    print("batch3 done")


if __name__ == "__main__":
    main()
