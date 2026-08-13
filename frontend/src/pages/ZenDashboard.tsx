import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_ZEN } from "../lib/demoCatalog";

type ZenData = {
  pnl?: { daily?: number; total?: number };
  holdings?: Array<{ symbol: string; shares: number; value: number; change_pct: number }>;
  recent_trades?: Array<{ symbol: string; side: string; quantity: number; price: number; time: string }>;
};

export default function ZenDashboard() {
  const { data, error, isLoading, mutate } = useSWR<ZenData>("/zen/dashboard", apiFetchV1, { refreshInterval: 15000 });

  const liveHoldings = data?.holdings ?? [];
  const isDemo = Boolean(error) || (!isLoading && (!data || !liveHoldings.length));
  const view = isDemo ? DEMO_ZEN : data;
  const pnl = view?.pnl;
  const holdings = view?.holdings ?? [];
  const trades = view?.recent_trades ?? [];

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.zenDashboard} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">禅意看板</h1>
          <p className="text-[var(--quant-muted)] text-sm">极简持仓概览</p>
          <DemoBanner show={isDemo} />
        </div>
        <button type="button" className="btn-brand btn-sm" onClick={() => mutate()}>刷新</button>
      </div>

      {isLoading && !data && !isDemo ? <div className="quant-card p-6 text-center text-[var(--quant-muted)]">加载中...</div> : null}

      {(view && (!isLoading || isDemo)) ? (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="quant-card p-5">
              <div className="text-xs text-[var(--quant-muted)] mb-1">当日盈亏</div>
              <div className={`text-3xl font-bold mono ${(pnl?.daily ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>
                {pnl?.daily !== undefined ? `${pnl.daily >= 0 ? "+" : ""}${pnl.daily.toFixed(2)}%` : "—"}
              </div>
            </div>
            <div className="quant-card p-5">
              <div className="text-xs text-[var(--quant-muted)] mb-1">累计盈亏</div>
              <div className={`text-3xl font-bold mono ${(pnl?.total ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>
                {pnl?.total !== undefined ? `${pnl.total >= 0 ? "+" : ""}${pnl.total.toFixed(2)}%` : "—"}
              </div>
            </div>
          </div>

          <div className="quant-card p-5">
            <h2 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider mb-3">主要持仓</h2>
            {holdings.length === 0 ? <p className="text-[var(--quant-muted)] text-sm">暂无持仓</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-[var(--quant-muted)] border-b border-[var(--quant-border)]"><th className="text-left py-2">标的</th><th className="text-right py-2">持仓</th><th className="text-right py-2">市值</th><th className="text-right py-2">涨跌幅</th></tr></thead>
                  <tbody>{holdings.map((h, i) => (
                    <tr key={i} className="border-b border-[var(--quant-border)]/50"><td className="py-2 mono"><Link className="link" to={`/stock/${encodeURIComponent(h.symbol)}?m=CN`}>{h.symbol}</Link></td><td className="py-2 text-right">{h.shares}</td><td className="py-2 text-right mono">¥{h.value.toLocaleString()}</td><td className={`py-2 text-right mono ${h.change_pct >= 0 ? "text-green-500" : "text-red-500"}`}>{h.change_pct >= 0 ? "+" : ""}{h.change_pct.toFixed(2)}%</td></tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </div>

          <div className="quant-card p-5">
            <h2 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider mb-3">最近交易</h2>
            {trades.length === 0 ? <p className="text-[var(--quant-muted)] text-sm">暂无交易</p> : (
              <div className="space-y-2">{trades.map((t, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-[var(--quant-border)]/30">
                  <div className="flex items-center gap-3"><span className={`px-2 py-0.5 rounded text-xs font-medium ${t.side === "buy" ? "bg-green-500/20 text-green-600" : "bg-red-500/20 text-red-600"}`}>{t.side === "buy" ? "买入" : "卖出"}</span><span className="mono font-medium">{t.symbol}</span><span className="text-sm text-[var(--quant-muted)]">{t.quantity} @ {t.price.toFixed(2)}</span></div>
                  <span className="text-xs text-[var(--quant-muted)]">{t.time}</span>
                </div>
              ))}</div>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            {["调仓", "定投", "报告"].map((action) => (
              <button key={action} type="button" className="quant-card p-4 text-center hover:bg-[var(--quant-surface)] transition-colors cursor-pointer">
                <div className="text-sm font-medium">{action}</div>
              </button>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
