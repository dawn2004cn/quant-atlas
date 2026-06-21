import { useState } from "react";
import useSWR from "swr";
import { apiFetchV1 } from "../lib/api";
import type { BacktestCompareRow } from "../types/backtest";

/* ── API ── */
function compareStrategies(symbol: string, strategies: string[], start: string, end: string): Promise<{ comparisons: BacktestCompareRow[]; winner?: string | null }> {
  return apiFetchV1("/strategies/backtest/compare", {
    method: "POST",
    body: JSON.stringify({ symbol, strategies, start, end, initial_capital: 100_000 }),
  });
}

function fmtPct(v?: number | null): string {
  if (v == null) return "--";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2)}%`;
}

const DEFAULT_STRATEGIES = ["双均线策略", "MACD金叉", "RSI超卖反转", "布林带突破"];

export function StrategyComparePage() {
  const [symbol, setSymbol] = useState("600519");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");
  const [strategies, setStrategies] = useState(DEFAULT_STRATEGIES.join("\n"));

  const stratList = strategies.split("\n").map((s) => s.trim()).filter(Boolean);

  const { data, error, isLoading, mutate } = useSWR(
    stratList.length ? ["compare", symbol, startDate, endDate, stratList.join(",")] : null,
    () => compareStrategies(symbol, stratList, startDate, endDate),
  );

  const rows = data?.comparisons ?? [];
  const winner = data?.winner;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">策略对比</h1>
          <p className="text-sm text-slate-500">多策略同标的回测对比</p>
        </div>
      </div>

      {/* Controls */}
      <div className="glass-card flex flex-wrap items-end gap-4 p-4">
        <div className="flex-1 min-w-[120px]">
          <label className="text-xs font-semibold text-slate-500">标的</label>
          <input type="text" className="input input-bordered input-sm w-full" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        </div>
        <div className="flex-1 min-w-[140px]">
          <label className="text-xs font-semibold text-slate-500">开始日期</label>
          <input type="date" className="input input-bordered input-sm w-full" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div className="flex-1 min-w-[140px]">
          <label className="text-xs font-semibold text-slate-500">结束日期</label>
          <input type="date" className="input input-bordered input-sm w-full" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500">&nbsp;</label>
          <button type="button" className="btn btn-primary btn-sm w-full" onClick={() => mutate()}>对比</button>
        </div>
      </div>

      {/* Strategies input */}
      <div className="glass-card p-4">
        <label className="text-xs font-semibold text-slate-500">策略名称（每行一个）</label>
        <textarea className="textarea textarea-bordered mt-1 w-full text-sm" rows={4} value={strategies} onChange={(e) => setStrategies(e.target.value)} />
      </div>

      {error && <div className="alert alert-error">{error.message}</div>}
      {isLoading && <div className="text-sm text-slate-500">对比计算中...</div>}

      {/* Results */}
      {rows.length > 0 && (
        <>
          {winner && (
            <div className="rounded-xl bg-emerald-50 p-4 dark:bg-emerald-950/30">
              <span className="font-bold text-emerald-700 dark:text-emerald-400">最优策略：{winner}</span>
            </div>
          )}

          <section className="glass-card overflow-x-auto p-4">
            <table className="table w-full">
              <thead>
                <tr>
                  <th>策略</th>
                  <th>状态</th>
                  <th>总收益</th>
                  <th>年化收益</th>
                  <th>夏普比</th>
                  <th>最大回撤</th>
                  <th>胜率</th>
                  <th>交易次数</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r: BacktestCompareRow) => (
                  <tr key={r.strategy_name} className={winner === r.strategy_name ? "bg-emerald-50 dark:bg-emerald-950/20" : ""}>
                    <td className="font-semibold">{r.strategy_name}</td>
                    <td><span className={`badge ${r.status === "ok" ? "badge-success" : "badge-error"}`}>{r.status}</span></td>
                    <td className={pctClass2(r.total_return)}>{fmtPct(r.total_return)}</td>
                    <td className={pctClass2(r.annual_return)}>{fmtPct(r.annual_return)}</td>
                    <td>{r.sharpe?.toFixed(2) ?? "--"}</td>
                    <td className="text-rose-600">{r.max_drawdown != null ? `${(r.max_drawdown * 100).toFixed(2)}%` : "--"}</td>
                    <td>{r.win_rate != null ? `${(r.win_rate * 100).toFixed(1)}%` : "--"}</td>
                    <td>{r.trade_count ?? "--"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  );
}

function pctClass2(v?: number | null): string {
  if (v == null) return "";
  return v >= 0 ? "text-emerald-600" : "text-rose-600";
}