"""Batch 2: message_center, backtest static, stock_detail JS blocks."""
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
        CSS / "system.css",
        "/* ── Message center inline cleanup ── */",
        """
.mc-hero-row { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 16px; }
.mc-hero-actions { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.mc-worker-title { font-weight: 900; font-size: 1.1rem; margin-bottom: 20px; }
.mc-worker-section { margin-top: 24px; padding-top: 20px; border-top: 1px solid rgba(0, 0, 0, 0.05); }
.mc-section-title { font-weight: 700; margin-bottom: 12px; font-size: 0.9rem; }
.mc-section-title-sm { font-weight: 700; margin-bottom: 10px; font-size: 0.9rem; }
.mc-lookup-input { margin-bottom: 10px; }
.mc-task-detail { font-size: 0.78rem; background: rgba(0, 0, 0, 0.03); padding: 12px; border-radius: 12px; max-height: 200px; overflow: auto; }
.mc-worker-section-sm { padding-top: 16px; border-top: 1px solid rgba(0, 0, 0, 0.05); }
.mc-help-details { font-size: 0.85rem; color: var(--muted); opacity: 0.8; }
.mc-help-summary { cursor: pointer; font-weight: 700; }
.mc-help-body { line-height: 1.6; }
.mc-job-row { padding: 8px 0; border-bottom: 1px solid rgba(0, 0, 0, 0.06); }
.mc-job-title { font-weight: 700; }
.mc-job-meta { font-size: 0.75rem; }
.mc-trace-actions { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
.mc-pre-reset { margin: 0; }
""",
    )
    append_marker(
        CSS / "strategy.css",
        "/* ── Backtest inline cleanup ── */",
        """
.bt-span-2 { grid-column: span 2; }
.bt-btn-full { width: 100%; }
.bt-chart-sm { height: 240px; }
.bt-section-trades {
    background: linear-gradient(135deg, rgba(16, 63, 145, 0.04), rgba(16, 185, 129, 0.03));
}
.bt-section-duel {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.06), rgba(16, 185, 129, 0.04));
    border: 1px solid rgba(139, 92, 246, 0.15);
}
.bt-section-counter {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.04), rgba(245, 158, 11, 0.03));
    border: 1px solid rgba(239, 68, 68, 0.15);
}
.bt-table-scroll { overflow-x: auto; }
.bt-diag-pills { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.bt-checkbox-row { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.bt-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.bt-trades-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.bt-trades-table th { padding: 12px; text-align: left; font-weight: 800; background: var(--surface-strong); }
.bt-trades-table th.center { text-align: center; }
.bt-trades-table th.right { text-align: right; }
.bt-trades-table td { padding: 10px; border-bottom: 1px solid var(--surface-border); }
.bt-trades-table td.center { text-align: center; }
.bt-trades-table td.right { text-align: right; }
.bt-trades-table tr.win { background: rgba(16, 185, 129, 0.08); }
.bt-hint-green { padding: 12px; background: rgba(16, 185, 129, 0.08); border-radius: 8px; }
.bt-panel-row { display: flex; justify-content: space-between; }
.bt-grid-gap { display: grid; gap: 10px; }
""",
    )
    append_marker(
        CSS / "stock-detail.css",
        "/* ── Dynamic panel utilities ── */",
        """
.sd-grid-gap-sm { display: grid; gap: 8px; }
.sd-grid-2-gap10 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.sd-flow-score { text-align: center; padding: 16px; }
.sd-flow-score-val { font-size: 2.5rem; font-weight: 900; }
.sd-hint-blue { padding: 12px; background: rgba(59, 130, 246, 0.05); border-radius: 8px; }
.sd-hint-violet { padding: 12px; background: rgba(139, 92, 246, 0.05); border-radius: 8px; }
.sd-hint-green { padding: 12px; background: rgba(16, 185, 129, 0.06); border-radius: 8px; }
.sd-hint-risk { display: flex; align-items: center; gap: 12px; padding: 12px; background: rgba(239, 68, 68, 0.08); border-radius: 8px; }
.sd-hint-risk-icon { font-size: 24px; }
.sd-disclaimer { padding: 8px; }
.sd-stat-brand { text-align: center; padding: 8px; background: rgba(59, 130, 246, 0.08); border-radius: 8px; }
.sd-trade-positive { border-left-color: var(--positive); }
.sd-trade-negative { border-left-color: var(--negative); }
.sd-panel-compact { padding: 10px; }
.sd-chain-col { display: flex; flex-direction: column; gap: 8px; }
.sd-chain-row { display: flex; gap: 12px; align-items: start; padding: 10px; border-radius: 8px; }
.sd-chain-row--l1 { background: rgba(16, 185, 129, 0.08); }
.sd-chain-row--l2 { background: rgba(59, 130, 246, 0.04); }
.sd-chain-row--l3 { background: rgba(239, 68, 68, 0.06); }
.sd-chain-icon { font-size: 16px; }
.sd-chain-body { flex: 1; }
.sd-chain-foot { border-top: 1px solid var(--surface-border); padding-top: 12px; }
.sd-list-reset { margin: 8px 0 0 16px; padding: 0; }
.sd-news-row { padding: 8px 0; border-bottom: 1px solid rgba(0, 0, 0, 0.06); }
.sd-news-row-lg { padding: 10px 0; border-bottom: 1px solid rgba(0, 0, 0, 0.06); }
.sd-kind-muted { opacity: 0.75; margin-right: 8px; }
""",
    )

    patch(
        TPL / "message_center.html",
        [
            (
                '<div style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:16px">',
                '<div class="mc-hero-row">',
            ),
            (
                '<div style="display:flex; gap:10px; margin-bottom:12px; flex-wrap:wrap; align-items:center">',
                '<div class="mc-hero-actions">',
            ),
            (
                '<div style="font-weight:900; font-size:1.1rem; margin-bottom:20px">🛡️ Celery 运行状态</div>',
                '<div class="mc-worker-title">🛡️ Celery 运行状态</div>',
            ),
            (
                '<div style="margin-top:24px; padding-top:20px; border-top:1px solid rgba(0,0,0,0.05)">\n                <div style="font-weight:700; margin-bottom:12px; font-size:0.9rem">任务反查</div>\n                <input type="text" id="lookupId" class="input-soft" placeholder="粘贴 Task ID" style="margin-bottom:10px">',
                '<div class="mc-worker-section">\n                <div class="mc-section-title">任务反查</div>\n                <input type="text" id="lookupId" class="input-soft mc-lookup-input" placeholder="粘贴 Task ID">',
            ),
            (
                'id="taskDetailBox" class="qa-is-hidden mt-3" style="font-size:0.78rem; background:rgba(0,0,0,0.03); padding:12px; border-radius:12px; max-height:200px; overflow:auto"',
                'id="taskDetailBox" class="qa-is-hidden mt-3 mc-task-detail"',
            ),
            (
                '<div class="mt-4" style="padding-top:16px; border-top:1px solid rgba(0,0,0,0.05)">\n                <div style="font-weight:700; margin-bottom:10px; font-size:0.9rem">进行中的任务</div>',
                '<div class="mt-4 mc-worker-section-sm">\n                <div class="mc-section-title-sm">进行中的任务</div>',
            ),
            (
                '<details class="mt-4" style="font-size:0.85rem; color:var(--muted); opacity:0.8">\n            <summary style="cursor:pointer; font-weight:700">📘 任务中心说明</summary>\n            <div class="mt-2" style="line-height:1.6">',
                '<details class="mt-4 mc-help-details">\n            <summary class="mc-help-summary">📘 任务中心说明</summary>\n            <div class="mt-2 mc-help-body">',
            ),
            (
                "return '<div style=\"padding:8px 0;border-bottom:1px solid rgba(0,0,0,0.06);\">' +\n                '<div style=\"font-weight:700;\">'",
                "return '<div class=\"mc-job-row\">' +\n                '<div class=\"mc-job-title\">'",
            ),
            (
                "'<div class=\"text-muted\" style=\"font-size:0.75rem;\">进度 '",
                "'<div class=\"text-muted mc-job-meta\">进度 '",
            ),
            (
                "? '<div style=\"margin-top:10px;\"><a class=\"btn-soft btn-sm\"",
                "? '<div class=\"mc-trace-actions\"><a class=\"btn-soft btn-sm\"",
            ),
            (
                "${traceIdOf(m) ? `<div style=\"margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;\">",
                "${traceIdOf(m) ? `<div class=\"mc-trace-actions\">",
            ),
            (
                'box.innerHTML = `<pre style="margin:0">${JSON.stringify(d, null, 2)}</pre>`;',
                'box.innerHTML = `<pre class="mc-pre-reset">${JSON.stringify(d, null, 2)}</pre>`;',
            ),
        ],
    )

    patch(
        TPL / "backtest.html",
        [
            ('<div style="grid-column: span 2">', '<div class="bt-span-2">'),
            ('<button class="btn-brand" type="submit" style="width:100%">', '<button class="btn-brand bt-btn-full" type="submit">'),
            ('id="drawdownChart" style="height:240px"', 'id="drawdownChart" class="bt-chart-sm"'),
            (
                '<div class="section-shell mt-4" style="background: linear-gradient(135deg, rgba(16,63,145,0.04), rgba(16,185,129,0.03))">',
                '<div class="section-shell mt-4 bt-section-trades">',
            ),
            ('id="tradeHistoryTable" style="overflow-x:auto"', 'id="tradeHistoryTable" class="bt-table-scroll"'),
            (
                'id="diagPills" style="display:flex; flex-wrap:wrap; gap:10px; margin-top:16px"',
                'id="diagPills" class="bt-diag-pills"',
            ),
            (
                '<section class="section-shell mt-4" style="background: linear-gradient(135deg, rgba(139,92,246,0.06), rgba(16,185,129,0.04)); border:1px solid rgba(139,92,246,0.15)">',
                '<section class="section-shell mt-4 bt-section-duel">',
            ),
            (
                '<section class="section-shell mt-4" style="background: linear-gradient(135deg, rgba(239,68,68,0.04), rgba(245,158,11,0.03)); border:1px solid rgba(239,68,68,0.15)">',
                '<section class="section-shell mt-4 bt-section-counter">',
            ),
            (
                '<label style="display:flex; align-items:center; gap:8px; cursor:pointer">',
                '<label class="bt-checkbox-row">',
            ),
            (
                '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px">',
                '<div class="bt-grid-2">',
            ),
            ('if (buy) html += `<span style="color:#22c55E">🟢 买入</span><br/>`;', 'if (buy) html += `<span class="text-positive">🟢 买入</span><br/>`;'),
            ('if (sell) html += `<span style="color:#ef4444">🔴 卖出</span>`;', 'if (sell) html += `<span class="text-negative">🔴 卖出</span>`;'),
            (
                'let html = `<table style="width:100%; border-collapse:collapse; font-size:0.85rem;">',
                'let html = `<table class="bt-trades-table">',
            ),
            (
                '<tr style="background:var(--surface-strong);">\n                <th style="padding:12px; text-align:left; font-weight:800;">日期</th>\n                <th style="padding:12px; text-align:center; font-weight:800;">方向</th>\n                <th style="padding:12px; text-align:right; font-weight:800;">价格</th>\n                <th style="padding:12px; text-align:right; font-weight:800;">数量</th>\n                <th style="padding:12px; text-align:right; font-weight:800;">金额</th>\n                <th style="padding:12px; text-align:right; font-weight:800;">盈亏</th>',
                '<tr>\n                <th>日期</th>\n                <th class="center">方向</th>\n                <th class="right">价格</th>\n                <th class="right">数量</th>\n                <th class="right">金额</th>\n                <th class="right">盈亏</th>',
            ),
            (
                'html += `<tr style="border-bottom:1px solid var(--surface-border);">\n            <td style="padding:10px;">${t.date}</td>\n            <td style="padding:10px; text-align:center;">',
                'html += `<tr>\n            <td>${t.date}</td>\n            <td class="center">',
            ),
            (
                '<td style="padding:10px; text-align:right;">¥${t.price.toFixed(2)}</td>\n            <td style="padding:10px; text-align:right;">${t.shares || \'-\'}</td>\n            <td style="padding:10px; text-align:right;">¥${(t.amount || 0).toFixed(0)}</td>\n            <td style="padding:10px; text-align:right; font-weight:700; color:${t.pnl ? (t.pnl > 0 ? \'var(--positive)\' : \'var(--negative)\') : \'var(--muted)\'};">',
                '<td class="right">¥${t.price.toFixed(2)}</td>\n            <td class="right">${t.shares || \'-\'}</td>\n            <td class="right">¥${(t.amount || 0).toFixed(0)}</td>\n            <td class="right font-bold ${t.pnl ? (t.pnl > 0 ? \'text-positive\' : \'text-negative\') : \'text-muted\'}">',
            ),
            (
                'return `<tr style="${win ? \'background:rgba(16,185,129,0.08);\' : \'\'}">`',
                'return `<tr class="${win ? \'win\' : \'\'}">`',
            ),
            (
                '<div style="display:grid; gap:10px;">',
                '<div class="bt-grid-gap">',
            ),
            (
                '<div class="trade-plan-panel" style="border-left-color:var(--positive);">\n                        <div style="display:flex; justify-content:space-between;">',
                '<div class="trade-plan-panel sd-trade-positive">\n                        <div class="bt-panel-row">',
            ),
            (
                '<span class="text-sm" style="color:var(--positive);">预期 ${p.fair}</span>',
                '<span class="text-sm text-positive">预期 ${p.fair}</span>',
            ),
            (
                '<div class="text-xs" style="color:var(--warning);">💡 ${p.reason}</div>',
                '<div class="text-xs text-warning">💡 ${p.reason}</div>',
            ),
            (
                '<div class="text-sm" style="padding:12px; background:rgba(16,185,129,0.08); border-radius:8px;">',
                '<div class="text-sm bt-hint-green">',
            ),
        ],
    )

    sd = (TPL / "stock_detail.html").read_text(encoding="utf-8")
    sd_pairs = [
        (
            """            $('#liquidityAnalysis').html(`
        <div style="display: grid; gap: 12px;">
            <div class="trade-plan-panel" style="border-left-color: ${isManipulated ? 'var(--negative)' : 'var(--positive)'}">
                <div class="panel-head"><h3 class="panel-title mb-0">流动性评分</h3></div>
                <div style="text-align:center; padding: 16px;">
                    <div style="font-size:2.5rem; font-weight:900; color: ${flowScore > 60 ? 'var(--positive)' : (flowScore > 40 ? 'var(--brand)' : 'var(--negative)')}">${flowScore}</div>
                    <div class="text-sm text-muted">基于成交额/换手/涨跌幅的启发式评分</div>
                </div>
            </div>
            
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <div class="trade-plan-panel">
                    <div class="text-xs text-muted mb-2">成交额</div>
                    <div style="font-weight:700;">${amount > 0 ? (amount / 1e8).toFixed(2) + ' 亿元' : '暂无数据'}</div>
                </div>
                <div class="trade-plan-panel">
                    <div class="text-xs text-muted mb-2">换手率</div>
                    <div style="font-weight:700;">${turnover > 0 ? turnover.toFixed(2) + '%' : '—'}</div>
                </div>
            </div>
            
            <div class="text-sm" style="padding:12px; background:rgba(59,130,246,0.05); border-radius:8px;">
                <strong>💡 提示：</strong>${isManipulated ? '换手异常或价量背离，建议结合龙虎榜与盘口再确认。' : '量价结构未见明显异常（规则估算，非 Level-2 还原）。'}
            </div>
        </div>
    `);""",
            """            const flowClass = flowScore > 60 ? 'text-positive' : (flowScore > 40 ? 'text-brand' : 'text-negative');
            $('#liquidityAnalysis').html(`
        <div class="sd-grid-gap">
            <div class="trade-plan-panel ${isManipulated ? 'sd-trade-negative' : 'sd-trade-positive'}">
                <div class="panel-head"><h3 class="panel-title mb-0">流动性评分</h3></div>
                <div class="sd-flow-score">
                    <div class="sd-flow-score-val ${flowClass}">${flowScore}</div>
                    <div class="text-sm text-muted">基于成交额/换手/涨跌幅的启发式评分</div>
                </div>
            </div>
            <div class="sd-grid-2-gap10">
                <div class="trade-plan-panel">
                    <div class="text-xs text-muted mb-2">成交额</div>
                    <div class="sd-font-bold">${amount > 0 ? (amount / 1e8).toFixed(2) + ' 亿元' : '暂无数据'}</div>
                </div>
                <div class="trade-plan-panel">
                    <div class="text-xs text-muted mb-2">换手率</div>
                    <div class="sd-font-bold">${turnover > 0 ? turnover.toFixed(2) + '%' : '—'}</div>
                </div>
            </div>
            <div class="text-sm sd-hint-blue">
                <strong>💡 提示：</strong>${isManipulated ? '换手异常或价量背离，建议结合龙虎榜与盘口再确认。' : '量价结构未见明显异常（规则估算，非 Level-2 还原）。'}
            </div>
        </div>
    `);""",
        ),
        (
            """        $('#whaleTracker').html(`
        <div style="display:grid; gap:12px;">
            <div style="display:flex; align-items:center; gap:16px; padding:16px; background:rgba(236,72,153,0.08); border-radius:12px;">
                <div style="width:60px; height:60px; border-radius:50%; background:linear-gradient(135deg, #ec4899, #a855f7); display:flex; align-items:center; justify-content:center; font-size:24px;">🏦</div>
                <div style="flex:1;">
                    <div class="text-sm" style="font-weight:700;">${holderType}</div>
                    <div class="text-xs text-muted">${onLonghu ? '该股出现在最新龙虎榜快照' : '基于当日行情与成交额的规则判断'}</div>
                </div>
                <div class="badge-soft" style="background:rgba(16,185,129,0.15); color:var(--positive);">${health}</div>
            </div>
            
            <div class="trade-plan-panel">
                <div class="text-xs text-muted mb-2">当日行情</div>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
                    <div style="text-align:center; padding:8px; background:rgba(16,185,129,0.08); border-radius:8px;">
                        <div class="text-lg" style="color:${changePct >= 0 ? 'var(--positive)' : 'var(--negative)'};">${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%</div>
                        <div class="text-xs text-muted">涨跌幅</div>
                    </div>
                    <div style="text-align:center; padding:8px; background:rgba(59,130,246,0.08); border-radius:8px;">
                        <div class="text-lg">${amount > 0 ? (amount / 1e8).toFixed(2) + '亿' : '—'}</div>
                        <div class="text-xs text-muted">成交额</div>
                    </div>
                </div>
            </div>
            
            <div class="text-sm text-muted" style="padding:8px;">完整主力成本需 Level-2 / 龙虎榜席位明细，当前为公开行情启发式展示。</div>
        </div>
    `);""",
            """        $('#whaleTracker').html(`
        <div class="sd-grid-gap">
            <div class="sd-flow-row">
                <div class="sd-flow-avatar">🏦</div>
                <div class="sd-flow-body">
                    <div class="text-sm sd-font-bold">${holderType}</div>
                    <div class="text-xs text-muted">${onLonghu ? '该股出现在最新龙虎榜快照' : '基于当日行情与成交额的规则判断'}</div>
                </div>
                <div class="badge-soft sd-badge-health">${health}</div>
            </div>
            <div class="trade-plan-panel">
                <div class="text-xs text-muted mb-2">当日行情</div>
                <div class="sd-grid-2">
                    <div class="sd-stat-up">
                        <div class="text-lg ${changePct >= 0 ? 'text-positive' : 'text-negative'}">${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%</div>
                        <div class="text-xs text-muted">涨跌幅</div>
                    </div>
                    <div class="sd-stat-brand">
                        <div class="text-lg">${amount > 0 ? (amount / 1e8).toFixed(2) + '亿' : '—'}</div>
                        <div class="text-xs text-muted">成交额</div>
                    </div>
                </div>
            </div>
            <div class="text-sm text-muted sd-disclaimer">完整主力成本需 Level-2 / 龙虎榜席位明细，当前为公开行情启发式展示。</div>
        </div>
    `);""",
        ),
        (
            """    $('#patternMatchResult').html(`
        <div style="display:grid; gap:12px;">
            <div class="trade-plan-panel" style="border-left-color:var(--positive)">
                <div class="text-xs text-muted mb-2">最佳匹配</div>
                <div style="font-weight:700;">${patterns[0].date}</div>
                <div class="text-sm text-muted mt-1">相似度: <strong style="color:var(--positive)">${patterns[0].similarity}%</strong></div>
                <div class="text-sm mt-2">后续5日: <span class="${parseFloat(patterns[0].future5d) > 0 ? 'positive' : 'negative'}">${patterns[0].future5d}</span> | 后续20日: <span class="${parseFloat(patterns[0].future20d) > 0 ? 'positive' : 'negative'}">${patterns[0].future20d}</span></div>
            </div>
            <div style="display:grid; gap:8px;">
                ${patterns.slice(1).map(p => `
                    <div class="trade-plan-panel" style="padding:10px;">
                        <div class="flex justify-between">
                            <span class="text-sm">${p.date}</span>
                            <span class="text-xs text-muted">相似度 ${p.similarity}%</span>
                        </div>
                    </div>
                `).join('')}
            </div>
            <div class="text-sm" style="padding:12px; background:rgba(139,92,246,0.05); border-radius:8px;">
                <strong>💡 信心定心丸：</strong>当前走势与 ${patterns[0].date} 相似度 ${patterns[0].similarity}%，历史该点位后大概率触发反弹，建议逢低布局。
            </div>
        </div>
    `);""",
            """    $('#patternMatchResult').html(`
        <div class="sd-grid-gap">
            <div class="trade-plan-panel sd-trade-positive">
                <div class="text-xs text-muted mb-2">最佳匹配</div>
                <div class="sd-font-bold">${patterns[0].date}</div>
                <div class="text-sm text-muted mt-1">相似度: <strong class="text-positive">${patterns[0].similarity}%</strong></div>
                <div class="text-sm mt-2">后续5日: <span class="${parseFloat(patterns[0].future5d) > 0 ? 'positive' : 'negative'}">${patterns[0].future5d}</span> | 后续20日: <span class="${parseFloat(patterns[0].future20d) > 0 ? 'positive' : 'negative'}">${patterns[0].future20d}</span></div>
            </div>
            <div class="sd-grid-gap-sm">
                ${patterns.slice(1).map(p => `
                    <div class="trade-plan-panel sd-panel-compact">
                        <div class="flex justify-between">
                            <span class="text-sm">${p.date}</span>
                            <span class="text-xs text-muted">相似度 ${p.similarity}%</span>
                        </div>
                    </div>
                `).join('')}
            </div>
            <div class="text-sm sd-hint-violet">
                <strong>💡 信心定心丸：</strong>当前走势与 ${patterns[0].date} 相似度 ${patterns[0].similarity}%，历史该点位后大概率触发反弹，建议逢低布局。
            </div>
        </div>
    `);""",
        ),
        (
            "return '<div style=\"padding:8px 0;border-bottom:1px solid rgba(0,0,0,0.06);\"><strong>'",
            "return '<div class=\"sd-news-row\"><strong>'",
        ),
        (
            "return '<div style=\"padding:10px 0;border-bottom:1px solid rgba(0,0,0,0.06);\"><strong>'",
            "return '<div class=\"sd-news-row-lg\"><strong>'",
        ),
        (
            "$('#tdxBlocksInner').html('<div class=\"loading-state\" style=\"width:100%;\">正在加载通达信板块...</div>');",
            "$('#tdxBlocksInner').html('<div class=\"loading-state sd-loading-full\">正在加载通达信板块...</div>');",
        ),
        (
            "`<span style=\"opacity:.75;margin-right:8px;\">${escHtml(kindLabel(k))}</span>`",
            "`<span class=\"sd-kind-muted\">${escHtml(kindLabel(k))}</span>`",
        ),
    ]
    for old, new in sd_pairs:
        if old in sd:
            sd = sd.replace(old, new)
    (TPL / "stock_detail.html").write_text(sd, encoding="utf-8")
    print("stock_detail.html: patched")

    print("batch2 done")


if __name__ == "__main__":
    main()
