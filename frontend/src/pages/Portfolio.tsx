import { useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import type {
  PortfolioPosition,
  OptimizationResult,
  RebalanceAlert,
  RiskBudgetItem,
  PortfolioAttribution,
} from "../types/portfolio";
import { apiFetchV1 } from "../lib/api";

/* ── API Helpers ── */
function fetchSnapshot(symbols: string): Promise<{ portfolio: { total_value: number; cash: number; positions: PortfolioPosition[]; returns: { total_return_pct: number; total_pnl: number; benchmark_return_pct?: number; alpha_pct?: number } } }> {
  return apiFetchV1(`/portfolio/snapshot?symbols=${encodeURIComponent(symbols)}&cash=100000`);
}

function fetchOptimize(symbols: string[], method: string, riskAversion: number): Promise<{ optimization: OptimizationResult }> {
  return apiFetchV1("/portfolio/optimize", {
    method: "POST",
    body: JSON.stringify({ symbols, method, risk_aversion: riskAversion }),
  });
}

const DEFAULT_SYMBOLS = "600519,000858,600036,601318,000333,600900";

type Tab = "holdings" | "optimize" | "rebalance" | "attribution" | "risk";

export function PortfolioPage() {
  const { mutate } = useSWRConfig();
  const [symbolsInput, setSymbolsInput] = useState(DEFAULT_SYMBOLS);
  const [tab, setTab] = useState<Tab>("holdings");
  const [method, setMethod] = useState<"markowitz" | "black_litterman">("markowitz");
  const [riskAversion, setRiskAversion] = useState(1.0);
  const [rebalanceThreshold, setRebalanceThreshold] = useState(5);

  /* ── Data Fetching ── */
  const symbolsList = symbolsInput.split(",").map((s) => s.trim()).filter(Boolean);

  const { data: snapshot, error: snapErr, isLoading: snapLoading } = useSWR(
    ["portfolio/snapshot", symbolsList.join(",")],
    () => fetchSnapshot(symbolsList.join(",")),
    { refreshInterval: 30_000 },
  );

  const { data: optimizeData, error: optErr, isLoading: optLoading } = useSWR(
    tab === "optimize" ? ["portfolio/optimize", symbolsList.join(","), method, riskAversion] : null,
    () => fetchOptimize(symbolsList, method, riskAversion),
  );

  const { data: rebalanceData, error: rebErr, isLoading: rebLoading } = useSWR(
    tab === "rebalance" ? ["portfolio/rebalance", symbolsList.join(","), rebalanceThreshold] : null,
    () => apiFetchV1<{ rebalance: { snapshot: { total_value: number; cash: number; positions: PortfolioPosition[] }; actions: RebalanceAlert[]; holdings: PortfolioPosition[] } }>(
      `/portfolio/rebalance?symbols=${encodeURIComponent(symbolsList.join(","))}&cash=100000&threshold=${rebalanceThreshold / 100}`,
    ),
  );

  const { data: attributionData, isLoading: attrLoading } = useSWR(
    tab === "attribution" ? ["portfolio/attribution"] : null,
    () => apiFetchV1<{ attribution: PortfolioAttribution }>(
      "/portfolio/attribution?portfolio_return=8&benchmark_return=5&alpha=3",
    ),
  );

  const { data: riskData, isLoading: riskLoading } = useSWR(
    tab === "risk" ? ["portfolio/risk", symbolsList.join(",")] : null,
    () => apiFetchV1<{ risk_budget: RiskBudgetItem[] }>(
      `/portfolio/risk-budget?symbols=${encodeURIComponent(symbolsList.join(","))}`,
    ),
  );

  if (snapLoading && !snapshot) return <PageSkeleton rows={4} />;

  const positions = snapshot?.portfolio?.positions ?? [];
  const returns = snapshot?.portfolio?.returns;

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">组合管理</h1>
          <p className="text-sm text-slate-500">Markowitz 有效前沿优化 · Black-Litterman 观点融合 · 归因分析</p>
        </div>
      </div>

      {/* ── Symbol Input ── */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <label className="text-sm font-semibold text-slate-500">标的（逗号分隔）</label>
        <input
          type="text"
          className="input input-bordered input-sm flex-1 min-w-[200px]"
          value={symbolsInput}
          onChange={(e) => setSymbolsInput(e.target.value)}
        />
        <button type="button" className="btn btn-primary btn-sm" onClick={() => mutate(undefined)}>
          刷新
        </button>
      </div>

      {/* ── Stats Cards ── */}
      {snapshot && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="组合总值" value={`¥${(snapshot.portfolio.total_value ?? 0).toLocaleString()}`} note="持仓 + 现金" />
          <StatCard
            label="持仓收益"
            value={`${(returns?.total_return_pct ?? 0) >= 0 ? "+" : ""}${(returns?.total_return_pct ?? 0).toFixed(2)}%`}
            note={`¥${(returns?.total_pnl ?? 0).toLocaleString()}`}
            positive={(returns?.total_return_pct ?? 0) >= 0}
          />
          <StatCard label="基准收益" value={`${(returns?.benchmark_return_pct ?? 0).toFixed(2)}%`} note="沪深300 YTD" />
          <StatCard
            label="阿尔法"
            value={`${(returns?.alpha_pct ?? 0) >= 0 ? "+" : ""}${(returns?.alpha_pct ?? 0).toFixed(2)}%`}
            note="超额收益"
            positive={(returns?.alpha_pct ?? 0) >= 0}
          />
        </div>
      )}

      {snapErr && <div className="alert alert-error">加载失败：{snapErr.message}</div>}

      {/* ── Tabs ── */}
      <div className="tabs tabs-box">
        {(["holdings", "optimize", "rebalance", "attribution", "risk"] as Tab[]).map((t) => (
          <button key={t} type="button" className={`tab ${tab === t ? "tab-active" : ""}`} onClick={() => setTab(t)}>
            {tabLabel(t)}
          </button>
        ))}
      </div>

      {/* ── Holdings Tab ── */}
      {tab === "holdings" && (
        <section className="glass-card overflow-x-auto p-4">
          <table className="table w-full">
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>持仓</th>
                <th>现价</th>
                <th>市值</th>
                <th>权重</th>
                <th>收益</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos: PortfolioPosition) => (
                <tr key={pos.symbol}>
                  <td><code>{pos.symbol}</code></td>
                  <td>{pos.name ?? "--"}</td>
                  <td>{pos.shares}</td>
                  <td>¥{pos.price?.toFixed(2) ?? "--"}</td>
                  <td>¥{(pos.market_value ?? 0).toLocaleString()}</td>
                  <td>{(pos.weight * 100).toFixed(1)}%</td>
                  <td className={pctClass(pos.return_pct)}>
                    {pos.return_pct != null ? `${pos.return_pct >= 0 ? "+" : ""}${pos.return_pct.toFixed(2)}%` : "--"}
                  </td>
                </tr>
              ))}
              {!positions.length && (
                <tr><td colSpan={7} className="text-center text-slate-500 py-8">暂无持仓数据</td></tr>
              )}
            </tbody>
          </table>
        </section>
      )}

      {/* ── Optimize Tab ── */}
      {tab === "optimize" && (
        <section className="glass-card space-y-4 p-4">
          <div className="flex flex-wrap items-center gap-4">
            <label className="text-sm font-semibold text-slate-500">优化方法</label>
            <select className="select select-bordered select-sm" value={method} onChange={(e) => setMethod(e.target.value as "markowitz" | "black_litterman")}>
              <option value="markowitz">Markowitz（有效前沿）</option>
              <option value="black_litterman">Black-Litterman（融合观点）</option>
            </select>
            <label className="text-sm font-semibold text-slate-500">风险偏好</label>
            <select className="select select-bordered select-sm" value={riskAversion} onChange={(e) => setRiskAversion(Number(e.target.value))}>
              <option value={0.5}>保守</option>
              <option value={1.0}>平衡</option>
              <option value={2.0}>激进</option>
            </select>
          </div>

          {optLoading && <div className="text-sm text-slate-500">计算中...</div>}
          {optErr && <div className="alert alert-error">{optErr.message}</div>}

          {optimizeData?.optimization && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                  <div className="text-xs text-slate-500">预期年化收益</div>
                  <div className="text-lg font-bold text-emerald-600">{(optimizeData.optimization.expected_return * 100).toFixed(2)}%</div>
                </div>
                <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                  <div className="text-xs text-slate-500">预期年化波动</div>
                  <div className="text-lg font-bold">{(optimizeData.optimization.expected_volatility * 100).toFixed(2)}%</div>
                </div>
                <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                  <div className="text-xs text-slate-500">夏普比率</div>
                  <div className="text-lg font-bold text-brand">{optimizeData.optimization.sharpe_ratio.toFixed(3)}</div>
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-bold text-slate-500">最优配置</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(optimizeData.optimization.optimal_weights).map(([sym, weight]) => (
                    <div key={sym} className="rounded-xl bg-brand/10 px-4 py-2 text-sm font-semibold">
                      {sym}: {(weight * 100).toFixed(1)}%
                    </div>
                  ))}
                </div>
              </div>

              {/* Allocation bar */}
              <div className="flex h-6 overflow-hidden rounded-full">
                {Object.entries(optimizeData.optimization.optimal_weights).map(([sym, weight], i) => (
                  <div
                    key={sym}
                    className="flex items-center justify-center text-xs font-bold text-white"
                    style={{ width: `${weight * 100}%`, backgroundColor: ALLOC_COLORS[i % ALLOC_COLORS.length] }}
                    title={`${sym}: ${(weight * 100).toFixed(1)}%`}
                  >
                    {(weight * 100) > 8 ? `${sym} ${(weight * 100).toFixed(0)}%` : null}
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {/* ── Rebalance Tab ── */}
      {tab === "rebalance" && (
        <section className="glass-card space-y-4 p-4">
          <div className="flex items-center gap-3">
            <label className="text-sm font-semibold text-slate-500">偏离度阈值</label>
            <select className="select select-bordered select-sm" value={rebalanceThreshold} onChange={(e) => setRebalanceThreshold(Number(e.target.value))}>
              <option value={2}>2%</option>
              <option value={5}>5%</option>
              <option value={10}>10%</option>
            </select>
          </div>

          {rebLoading && <div className="text-sm text-slate-500">计算中...</div>}
          {rebErr && <div className="alert alert-error">{rebErr.message}</div>}

          {rebalanceData?.rebalance && (
            <>
              <div className="overflow-x-auto">
                <table className="table w-full">
                  <thead>
                    <tr><th>标的</th><th>当前权重</th><th>目标权重</th><th>偏离</th><th>操作</th><th>金额</th></tr>
                  </thead>
                  <tbody>
                    {(rebalanceData.rebalance.actions ?? []).map((a: RebalanceAlert) => (
                      <tr key={a.symbol}>
                        <td><code>{a.symbol}</code></td>
                        <td>{(a.current_weight * 100).toFixed(1)}%</td>
                        <td>{(a.target_weight * 100).toFixed(1)}%</td>
                        <td className={pctClass(a.deviation)}>{a.deviation >= 0 ? "+" : ""}{(a.deviation * 100).toFixed(2)}%</td>
                        <td>
                          <span className={`badge ${a.action === "buy" ? "badge-success" : a.action === "sell" ? "badge-warning" : "badge-ghost"}`}>
                            {actionLabel(a.action)}
                          </span>
                        </td>
                        <td>¥{Math.abs(a.amount).toLocaleString()}</td>
                      </tr>
                    ))}
                    {!rebalanceData.rebalance.actions?.length && (
                      <tr><td colSpan={6} className="py-8 text-center text-slate-500">当前组合无需再平衡</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}

      {/* ── Attribution Tab ── */}
      {tab === "attribution" && (
        <section className="glass-card space-y-4 p-4">
          {attrLoading && <div className="text-sm text-slate-500">加载中...</div>}
          {attributionData?.attribution && (
            <div className="grid grid-cols-3 gap-3">
              <AttributionCard label="组合收益" value={`${(attributionData.attribution.portfolio_return * 100).toFixed(2)}%`} />
              <AttributionCard label="基准收益" value={`${(attributionData.attribution.benchmark_return * 100).toFixed(2)}%`} />
              <AttributionCard label="超额阿尔法" value={`${(attributionData.attribution.alpha * 100).toFixed(2)}%`} positive={attributionData.attribution.alpha >= 0} />
            </div>
          )}
        </section>
      )}

      {/* ── Risk Tab ── */}
      {tab === "risk" && (
        <section className="glass-card space-y-4 p-4">
          {riskLoading && <div className="text-sm text-slate-500">加载中...</div>}
          {riskData?.risk_budget && (
            <div className="overflow-x-auto">
              <table className="table w-full">
                <thead>
                  <tr><th>标的</th><th>风险贡献</th><th>边际风险</th><th>Component VaR</th></tr>
                </thead>
                <tbody>
                  {riskData.risk_budget.map((r: RiskBudgetItem) => (
                    <tr key={r.symbol}>
                      <td><code>{r.symbol}</code></td>
                      <td>{(r.contribution_pct * 100).toFixed(1)}%</td>
                      <td>{r.marginal_risk.toFixed(4)}</td>
                      <td>{r.component_var.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

/* ── Sub-components ── */

function StatCard({ label, value, note, positive }: { label: string; value: string; note: string; positive?: boolean }) {
  return (
    <div className={`glass-card rounded-2xl p-4 ${positive === true ? "border-emerald-200" : positive === false ? "border-rose-200" : ""}`}>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-black ${positive === true ? "text-emerald-600" : positive === false ? "text-rose-600" : ""}`}>{value}</div>
      <div className="text-xs text-slate-400">{note}</div>
    </div>
  );
}

function AttributionCard({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="rounded-xl bg-slate-100 p-4 dark:bg-slate-800">
      <div className="text-xs font-semibold text-slate-500">{label}</div>
      <div className={`text-xl font-bold ${positive === true ? "text-emerald-600" : positive === false ? "text-rose-600" : ""}`}>{value}</div>
    </div>
  );
}

function pctClass(value?: number) {
  if (value == null) return "";
  return value >= 0 ? "text-emerald-600" : "text-rose-600";
}

function tabLabel(tab: Tab): string {
  switch (tab) {
    case "holdings": return "持仓";
    case "optimize": return "优化";
    case "rebalance": return "再平衡";
    case "attribution": return "归因";
    case "risk": return "风险预算";
  }
}

function actionLabel(action: "buy" | "sell" | "hold"): string {
  switch (action) {
    case "buy": return "买入";
    case "sell": return "卖出";
    case "hold": return "持有";
  }
}

const ALLOC_COLORS = ["#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e"];