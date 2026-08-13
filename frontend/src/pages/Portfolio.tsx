import { useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { DemoBanner } from "../components/DemoBanner";
import { DEMO_PORTFOLIO } from "../lib/demoCatalog";
import type {
  PortfolioPosition,
  OptimizationResult,
  RebalanceAlert,
  RiskBudgetItem,
} from "../types/portfolio";
import { apiFetchV1 } from "../lib/api";

/* ── API ── */
type SnapshotPayload = {
  portfolio: {
    total_value: number;
    cash: number;
    positions: PortfolioPosition[];
    returns: {
      total_return_pct: number;
      total_pnl: number;
      benchmark_return_pct?: number;
      alpha_pct?: number;
    };
  };
  risk_budget?: RiskBudgetItem[];
  optimize_summary?: OptimizationResult | null;
};

function fetchSnapshot(symbols: string): Promise<SnapshotPayload> {
  const q = new URLSearchParams({
    symbols,
    cash: "100000",
    include: "risk_budget,optimize_summary",
  });
  return apiFetchV1(`/portfolio/snapshot?${q.toString()}`);
}

const DEFAULT_SYMBOLS = "600519,000858,600036,601318,000333,600900";
const ALLOC_COLORS = ["#10b981","#3b82f6","#8b5cf6","#d946ef","#ec4899","#f43f5e","#f97316","#eab308","#06b6d4"];

type Tab = "holdings" | "optimize" | "rebalance" | "risk";

function fmtPct(v?: number | null, signed = false): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${signed && v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function pctClass(v?: number | null): string {
  if (v == null) return "text-zinc-400";
  return v >= 0 ? "text-emerald-400" : "text-rose-400";
}

function MetricCard({ label, value, note, positive, negative }: { label: string; value: string; note: string; positive?: boolean; negative?: boolean }) {
  return (
    <div className="rounded-xl bg-zinc-900/50 p-4 ring-1 ring-zinc-800/50">
      <div className="text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">{label}</div>
      <div className={`mt-1 text-2xl font-black font-mono tabular-nums ${
        positive ? "text-emerald-400" : negative ? "text-rose-400" : "text-zinc-100"
      }`}>{value}</div>
      <div className="mt-0.5 text-xs text-zinc-600">{note}</div>
    </div>
  );
}

/* ── Surface wrapper ── */
function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

function OptimizePanel({
  optimization,
}: {
  optimization: OptimizationResult;
}) {
  const vol = optimization.expected_volatility ?? (optimization as { volatility?: number }).volatility ?? 0;
  const weights = optimization.optimal_weights ?? {};
  return (
    <>
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-zinc-800/40 p-3">
          <div className="text-[10px] font-mono uppercase text-zinc-500">预期年化收益</div>
          <div className="mt-1 text-lg font-bold font-mono tabular-nums text-emerald-400">{((optimization.expected_return ?? 0) * 100).toFixed(2)}%</div>
        </div>
        <div className="rounded-lg bg-zinc-800/40 p-3">
          <div className="text-[10px] font-mono uppercase text-zinc-500">预期年化波动</div>
          <div className="mt-1 text-lg font-bold font-mono tabular-nums text-zinc-200">{(vol * 100).toFixed(2)}%</div>
        </div>
        <div className="rounded-lg bg-zinc-800/40 p-3">
          <div className="text-[10px] font-mono uppercase text-zinc-500">夏普比率</div>
          <div className="mt-1 text-lg font-bold font-mono tabular-nums text-emerald-400">{(optimization.sharpe_ratio ?? 0).toFixed(3)}</div>
        </div>
      </div>

      <div>
        <p className="mb-2 text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">最优配置</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(weights).map(([sym, w]) => (
            <span key={sym} className="rounded-md bg-emerald-500/10 px-3 py-1.5 font-mono text-xs text-emerald-400">
              {sym} {(w * 100).toFixed(1)}%
            </span>
          ))}
        </div>
      </div>

      <div className="flex h-5 overflow-hidden rounded-full">
        {Object.entries(weights).map(([sym, w], i) => (
          <div key={sym} className="flex items-center justify-center text-[9px] font-bold text-white" style={{ width: `${w * 100}%`, backgroundColor: ALLOC_COLORS[i % ALLOC_COLORS.length] }}>
            {(w * 100) > 8 ? `${sym}` : null}
          </div>
        ))}
      </div>
    </>
  );
}

export function PortfolioPage() {
  const { mutate } = useSWRConfig();
  const [symbolsInput, setSymbolsInput] = useState(DEFAULT_SYMBOLS);
  const [tab, setTab] = useState<Tab>("holdings");
  const [method, setMethod] = useState<"markowitz" | "black_litterman">("markowitz");
  const [riskAversion, setRiskAversion] = useState(1.0);
  const [rebalanceThreshold, setRebalanceThreshold] = useState(5);

  const symbolsList = symbolsInput.split(",").map((s) => s.trim()).filter(Boolean);

  const { data: snapshot, error: snapErr, isLoading: snapLoading } = useSWR(
    ["portfolio/snapshot", symbolsList.join(",")],
    () => fetchSnapshot(symbolsList.join(",")),
    { refreshInterval: 30_000 },
  );

  const needsCustomOptimize = tab === "optimize" && (method !== "markowitz" || riskAversion !== 1.0);
  const { data: optimizeData, error: optErr, isLoading: optLoading } = useSWR(
    needsCustomOptimize ? ["portfolio/optimize", symbolsList.join(","), method, riskAversion] : null,
    () => apiFetchV1<{ optimization: OptimizationResult }>("/portfolio/optimize", {
      method: "POST",
      body: JSON.stringify({ symbols: symbolsList, method, risk_aversion: riskAversion }),
    }),
  );

  const { data: rebalanceData, error: rebErr, isLoading: rebLoading } = useSWR(
    tab === "rebalance" ? ["portfolio/rebalance", symbolsList.join(","), rebalanceThreshold] : null,
    () => apiFetchV1<{ rebalance: { actions: RebalanceAlert[] } }>(
      `/portfolio/rebalance?symbols=${encodeURIComponent(symbolsList.join(","))}&cash=100000&threshold=${rebalanceThreshold / 100}`,
    ),
  );

  if (snapLoading && !snapshot) return <PageSkeleton rows={4} />;

  const livePositions = snapshot?.portfolio?.positions ?? [];
  const isDemo = Boolean(snapErr) || livePositions.length === 0;
  const display = isDemo ? DEMO_PORTFOLIO : snapshot;
  const positions = display?.portfolio?.positions ?? [];
  const returns = display?.portfolio?.returns;
  const embeddedOpt = snapshot?.optimize_summary ?? null;
  const optimization =
    (needsCustomOptimize ? optimizeData?.optimization : null) ??
    (tab === "optimize" ? embeddedOpt : null);
  const riskBudget = (isDemo ? DEMO_PORTFOLIO.risk_budget : snapshot?.risk_budget) ?? [];

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.portfolio} />
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">
          Portfolio Management
        </div>
        <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">组合管理</h1>
        <DemoBanner show={isDemo} />
      </div>

      {/* Symbol input */}
      <Panel className="flex flex-wrap items-center gap-3 p-4">
        <label className="text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
          标的
        </label>
        <input
          type="text"
          value={symbolsInput}
          onChange={(e) => setSymbolsInput(e.target.value)}
          className="flex-1 rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200 placeholder-zinc-600 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20 min-w-[200px]"
        />
        <button type="button" onClick={() => mutate(undefined)} className="rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:bg-zinc-800/60 hover:text-zinc-200">
          刷新
        </button>
      </Panel>

      {snapErr && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
          加载失败：{snapErr.message}
        </div>
      )}

      {/* Metric cards */}
      {display && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricCard label="组合总值" value={`¥${(display.portfolio.total_value ?? 0).toLocaleString()}`} note="持仓 + 现金" />
          <MetricCard label="持仓收益" value={fmtPct(returns?.total_return_pct, true)} note={`¥${(returns?.total_pnl ?? 0).toLocaleString()}`} positive={(returns?.total_return_pct ?? 0) >= 0} negative={(returns?.total_return_pct ?? 0) < 0} />
          <MetricCard label="基准收益" value={fmtPct(returns?.benchmark_return_pct)} note="沪深300 YTD" />
          <MetricCard label="阿尔法" value={fmtPct(returns?.alpha_pct, true)} note="超额收益" positive={(returns?.alpha_pct ?? 0) >= 0} negative={(returns?.alpha_pct ?? 0) < 0} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-px rounded-lg bg-zinc-800/60 p-0.5 w-fit">
        {(["holdings", "optimize", "rebalance", "risk"] as Tab[]).map((t) => (
          <button key={t} type="button" onClick={() => setTab(t)}
            className={`rounded-md px-4 py-1.5 text-xs font-medium transition-all ${
              tab === t ? "bg-zinc-800 text-zinc-200 shadow-sm" : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t === "holdings" ? "持仓" : t === "optimize" ? "优化" : t === "rebalance" ? "再平衡" : "风险预算"}
          </button>
        ))}
      </div>

      {/* Holdings */}
      {tab === "holdings" && (
        <Panel className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800/60 text-left text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
                <th className="px-4 py-3">代码</th>
                <th className="px-4 py-3">名称</th>
                <th className="px-4 py-3 text-right">持仓</th>
                <th className="px-4 py-3 text-right">现价</th>
                <th className="px-4 py-3 text-right">市值</th>
                <th className="px-4 py-3 text-right">权重</th>
                <th className="px-4 py-3 text-right">收益</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/30">
              {positions.map((pos: PortfolioPosition) => (
                <tr key={pos.symbol} className="transition-colors hover:bg-zinc-800/30">
                  <td className="px-4 py-3 font-mono text-xs text-zinc-400">{pos.symbol}</td>
                  <td className="px-4 py-3 font-medium text-zinc-200">{pos.name ?? "--"}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{pos.shares}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">¥{pos.price?.toFixed(2) ?? "--"}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">¥{(pos.market_value ?? 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{(pos.weight * 100).toFixed(1)}%</td>
                  <td className={`px-4 py-3 text-right font-mono tabular-nums font-semibold ${pctClass(pos.return_pct)}`}>{fmtPct(pos.return_pct, true)}</td>
                </tr>
              ))}
              {!positions.length && (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-sm text-zinc-600">暂无持仓数据</td></tr>
              )}
            </tbody>
          </table>
        </Panel>
      )}

      {/* Optimize */}
      {tab === "optimize" && (
        <Panel className="space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-4">
            <select className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200" value={method} onChange={(e) => setMethod(e.target.value as "markowitz" | "black_litterman")}>
              <option value="markowitz">Markowitz</option>
              <option value="black_litterman">Black-Litterman</option>
            </select>
            <select className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200" value={riskAversion} onChange={(e) => setRiskAversion(Number(e.target.value))}>
              <option value={0.5}>保守</option>
              <option value={1.0}>平衡</option>
              <option value={2.0}>激进</option>
            </select>
          </div>

          {optLoading && <p className="text-sm text-zinc-500">计算中...</p>}
          {optErr && <p className="text-sm text-rose-400">{optErr.message}</p>}

          {optimization && <OptimizePanel optimization={optimization} />}
          {!optLoading && !optimization && (
            <p className="text-sm text-zinc-600">暂无优化摘要，请调整参数后重试</p>
          )}
        </Panel>
      )}

      {/* Rebalance */}
      {tab === "rebalance" && (
        <Panel className="space-y-4 p-5">
          <div className="flex items-center gap-3">
            <label className="text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">偏离度阈值</label>
            <select className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200" value={rebalanceThreshold} onChange={(e) => setRebalanceThreshold(Number(e.target.value))}>
              <option value={2}>2%</option>
              <option value={5}>5%</option>
              <option value={10}>10%</option>
            </select>
          </div>

          {rebLoading && <p className="text-sm text-zinc-500">计算中...</p>}
          {rebErr && <p className="text-sm text-rose-400">{rebErr.message}</p>}

          {rebalanceData?.rebalance && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800/60 text-left text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
                    <th className="px-4 py-3">标的</th>
                    <th className="px-4 py-3 text-right">当前权重</th>
                    <th className="px-4 py-3 text-right">目标权重</th>
                    <th className="px-4 py-3 text-right">偏离</th>
                    <th className="px-4 py-3 text-right">操作</th>
                    <th className="px-4 py-3 text-right">金额</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/30">
                  {(rebalanceData.rebalance.actions ?? []).map((a: RebalanceAlert) => (
                    <tr key={a.symbol} className="transition-colors hover:bg-zinc-800/30">
                      <td className="px-4 py-3 font-mono text-xs text-zinc-400">{a.symbol}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{(a.current_weight * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{(a.target_weight * 100).toFixed(1)}%</td>
                      <td className={`px-4 py-3 text-right font-mono tabular-nums font-semibold ${pctClass(a.deviation)}`}>{a.deviation >= 0 ? "+" : ""}{(a.deviation * 100).toFixed(2)}%</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${
                          a.action === "buy" ? "bg-emerald-500/10 text-emerald-400" :
                          a.action === "sell" ? "bg-rose-500/10 text-rose-400" :
                          "bg-zinc-800/60 text-zinc-500"
                        }`}>{a.action === "buy" ? "买入" : a.action === "sell" ? "卖出" : "持有"}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">¥{Math.abs(a.amount).toLocaleString()}</td>
                    </tr>
                  ))}
                  {!rebalanceData.rebalance.actions?.length && (
                    <tr><td colSpan={6} className="px-4 py-12 text-center text-sm text-zinc-600">当前组合无需再平衡</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}

      {/* Risk */}
      {tab === "risk" && (
        <Panel className="space-y-4 p-5">
          {!riskBudget.length && <p className="text-sm text-zinc-500">暂无风险预算（随组合快照加载）</p>}
          {!!riskBudget.length && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800/60 text-left text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
                    <th className="px-4 py-3">标的</th>
                    <th className="px-4 py-3 text-right">风险贡献</th>
                    <th className="px-4 py-3 text-right">边际风险</th>
                    <th className="px-4 py-3 text-right">Component VaR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/30">
                  {riskBudget.map((r: RiskBudgetItem) => {
                    const contrib =
                      r.contribution_pct ??
                      (r.risk_contribution_pct != null ? r.risk_contribution_pct / 100 : r.weight ?? 0);
                    const marginal = r.marginal_risk ?? r.marginal_var ?? 0;
                    const cvar = r.component_var ?? r.var_contribution ?? 0;
                    return (
                    <tr key={r.symbol} className="transition-colors hover:bg-zinc-800/30">
                      <td className="px-4 py-3 font-mono text-xs text-zinc-400">{r.symbol}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{(contrib * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{Number(marginal).toFixed(4)}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{Number(cvar).toFixed(4)}</td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}
    </div>
  );
}