import { useParams } from "react-router-dom";
import { useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import type { PortfolioPosition, OptimizationResult, RebalanceAlert } from "../types/portfolio";

type PortfolioDetailData = {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  total_value: number;
  cash: number;
  positions: PortfolioPosition[];
  metrics?: {
    sharpe?: number;
    volatility?: number;
    max_drawdown?: number;
    alpha?: number;
    sortino?: number;
  };
  rebalance_alerts?: RebalanceAlert[];
};

/* ── Helpers ── */
function fmtPct(v?: number | null): string {
  if (v == null) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function pctClass(v?: number | null): string {
  if (v == null) return "";
  return v >= 0 ? "text-emerald-600" : "text-rose-600";
}

export function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState<"holdings" | "optimize" | "rebalance">("holdings");
  const [symbolsInput, setSymbolsInput] = useState("");
  const [method, setMethod] = useState<"markowitz" | "black_litterman">("markowitz");
  const [riskAversion, setRiskAversion] = useState(1.0);

  const { data, error, isLoading } = useSWR(
    id ? ["portfolio-detail", id] : null,
    () => apiFetchV1<PortfolioDetailData>(`/portfolio/${encodeURIComponent(id ?? "")}`),
    { refreshInterval: 30_000 },
  );

  const symbols = symbolsInput || (data?.positions ?? []).map((p) => p.symbol).join(",");
  const symbolsList = symbols.split(",").map((s) => s.trim()).filter(Boolean);

  const { data: optData, isLoading: optLoading } = useSWR(
    tab === "optimize" && symbolsList.length ? ["detail-optimize", id, symbolsList.join(","), method, riskAversion] : null,
    () => apiFetchV1<{ optimization: OptimizationResult }>("/portfolio/optimize", {
      method: "POST",
      body: JSON.stringify({ symbols: symbolsList, method, risk_aversion: riskAversion }),
    }),
  );

  const { data: rebData, isLoading: rebLoading } = useSWR(
    tab === "rebalance" && symbolsList.length ? ["detail-rebalance", id, symbolsList.join(",")] : null,
    () => apiFetchV1<{ actions: RebalanceAlert[] }>(`/portfolio/rebalance?symbols=${encodeURIComponent(symbolsList.join(","))}&cash=${data?.cash ?? 100000}&threshold=0.05`),
  );

  if (isLoading) return <PageSkeleton rows={4} />;
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">组合不存在</div>;

  const positions = data.positions ?? [];
  const metrics = data.metrics;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.portfolioDetail} />
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{data.name ?? `组合 #${id}`}</h1>
          <p className="text-sm text-slate-500">{data.description ?? ""} · 创建于 {data.created_at ? new Date(data.created_at).toLocaleDateString("zh-CN") : "--"}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-black">¥{(data.total_value ?? 0).toLocaleString()}</div>
          <div className="text-xs text-slate-500">总价值</div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="glass-card rounded-2xl p-3"><div className="text-xs text-slate-500">现金</div><div className="text-lg font-bold">¥{(data.cash ?? 0).toLocaleString()}</div></div>
        <div className="glass-card rounded-2xl p-3"><div className="text-xs text-slate-500">夏普比</div><div className="text-lg font-bold">{metrics?.sharpe?.toFixed(2) ?? "--"}</div></div>
        <div className="glass-card rounded-2xl p-3"><div className="text-xs text-slate-500">波动率</div><div className="text-lg font-bold">{metrics?.volatility != null ? `${metrics.volatility.toFixed(2)}%` : "--"}</div></div>
        <div className="glass-card rounded-2xl p-3"><div className="text-xs text-slate-500">最大回撤</div><div className="text-lg font-bold text-rose-600">{metrics?.max_drawdown != null ? `${Math.abs(metrics.max_drawdown).toFixed(2)}%` : "--"}</div></div>
      </div>

      {/* Tabs */}
      <div className="tabs tabs-box">
        {(["holdings", "optimize", "rebalance"] as const).map((t) => (
          <button key={t} type="button" className={`tab ${tab === t ? "tab-active" : ""}`} onClick={() => setTab(t)}>
            {t === "holdings" ? "持仓" : t === "optimize" ? "优化" : "再平衡"}
          </button>
        ))}
      </div>

      {/* Holdings Tab */}
      {tab === "holdings" && (
        <section className="glass-card overflow-x-auto p-4">
          <div className="mb-3 flex items-center gap-2">
            <input type="text" className="input input-bordered input-sm flex-1" placeholder="符号（逗号分隔）" value={symbolsInput} onChange={(e) => setSymbolsInput(e.target.value)} />
          </div>
          <table className="table w-full">
            <thead>
              <tr><th>代码</th><th>名称</th><th>持仓</th><th>价格</th><th>市值</th><th>权重</th><th>收益</th></tr>
            </thead>
            <tbody>
              {positions.map((pos: PortfolioPosition) => (
                <tr key={pos.symbol}>
                  <td><code>{pos.symbol}</code></td>
                  <td className="font-medium">{pos.name ?? "--"}</td>
                  <td>{pos.shares}</td>
                  <td>¥{pos.price?.toFixed(2) ?? "--"}</td>
                  <td>¥{(pos.market_value ?? 0).toLocaleString()}</td>
                  <td>{(pos.weight * 100).toFixed(1)}%</td>
                  <td className={pctClass(pos.return_pct)}>{fmtPct(pos.return_pct)}</td>
                </tr>
              ))}
              {!positions.length && <tr><td colSpan={7} className="py-8 text-center text-slate-500">暂无持仓</td></tr>}
            </tbody>
          </table>
        </section>
      )}

      {/* Optimize Tab */}
      {tab === "optimize" && (
        <section className="glass-card space-y-4 p-4">
          <div className="flex flex-wrap items-center gap-4">
            <input type="text" className="input input-bordered input-sm flex-1" placeholder="符号" value={symbolsInput || symbols} onChange={(e) => setSymbolsInput(e.target.value)} />
            <select className="select select-bordered select-sm" value={method} onChange={(e) => setMethod(e.target.value as "markowitz" | "black_litterman")}>
              <option value="markowitz">Markowitz</option>
              <option value="black_litterman">Black-Litterman</option>
            </select>
            <select className="select select-bordered select-sm" value={riskAversion} onChange={(e) => setRiskAversion(Number(e.target.value))}>
              <option value={0.5}>保守</option>
              <option value={1.0}>平衡</option>
              <option value={2.0}>激进</option>
            </select>
          </div>
          {optLoading && <div className="text-sm text-slate-500">计算中...</div>}
          {optData?.optimization && (
            <>
              <div className="flex flex-wrap gap-2">
                {Object.entries(optData.optimization.optimal_weights).map(([sym, w]) => (
                  <div key={sym} className="rounded-xl bg-brand/10 px-4 py-2 text-sm font-semibold">{sym}: {(w * 100).toFixed(1)}%</div>
                ))}
              </div>
              <div className="flex h-6 overflow-hidden rounded-full">
                {Object.entries(optData.optimization.optimal_weights).map(([sym, w], i) => (
                  <div key={sym} className="flex items-center justify-center text-xs font-bold text-white" style={{ width: `${w * 100}%`, backgroundColor: ["#6366f1","#8b5cf6","#a855f7","#d946ef","#ec4899","#f43f5e","#f97316","#eab308","#22c55e"][i % 9] }}>
                    {(w * 100) > 8 ? `${sym}` : null}
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {/* Rebalance Tab */}
      {tab === "rebalance" && (
        <section className="glass-card overflow-x-auto p-4">
          {rebLoading && <div className="text-sm text-slate-500">计算中...</div>}
          {rebData?.actions?.length ? (
            <table className="table w-full">
              <thead><tr><th>代码</th><th>当前权重</th><th>目标权重</th><th>偏离</th><th>操作</th><th>金额</th></tr></thead>
              <tbody>
                {rebData.actions.map((a: RebalanceAlert) => (
                  <tr key={a.symbol}>
                    <td><code>{a.symbol}</code></td>
                    <td>{(a.current_weight * 100).toFixed(1)}%</td>
                    <td>{(a.target_weight * 100).toFixed(1)}%</td>
                    <td className={pctClass(a.deviation)}>{(a.deviation * 100).toFixed(2)}%</td>
                    <td><span className={`badge ${a.action === "buy" ? "badge-success" : a.action === "sell" ? "badge-warning" : "badge-ghost"}`}>{a.action === "buy" ? "买入" : a.action === "sell" ? "卖出" : "持有"}</span></td>
                    <td>¥{Math.abs(a.amount).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-8 text-center text-sm text-slate-500">无需再平衡</div>
          )}
        </section>
      )}
    </div>
  );
}