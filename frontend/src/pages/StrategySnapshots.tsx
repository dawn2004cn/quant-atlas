import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

type SnapshotRun = {
  run_id: string;
  strategy_name: string;
  symbol: string;
  created_at: string;
  metrics: {
    total_return_pct?: number;
    annual_return_pct?: number;
    sharpe?: number;
    max_drawdown_pct?: number;
  };
  status: string;
};

function fmtPct(v?: number | null): string {
  if (v == null) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function StrategySnapshotsPage() {
  const [limit, setLimit] = useState(50);

  const { data, error, isLoading } = useSWR(
    ["strategy-snapshots", limit],
    () => apiFetchV1<{ items: SnapshotRun[] }>(`/strategy/snapshots?limit=${limit}`),
    { refreshInterval: 60_000 },
  );

  const items = data?.items ?? [];

  if (isLoading && !items.length) return <PageSkeleton rows={4} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">策略快照</h1>
          <p className="text-sm text-slate-500">历史回测快照记录</p>
        </div>
        <select className="select select-bordered select-sm" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
          <option value={20}>20条</option>
          <option value={50}>50条</option>
          <option value={100}>100条</option>
        </select>
      </div>

      {error && <div className="alert alert-error">{error.message}</div>}

      <section className="glass-card overflow-x-auto p-4">
        <table className="table w-full">
          <thead>
            <tr><th>策略</th><th>标的</th><th>总收益</th><th>年化收益</th><th>夏普比</th><th>最大回撤</th><th>状态</th><th>时间</th></tr>
          </thead>
          <tbody>
            {items.map((r: SnapshotRun) => (
              <tr key={r.run_id}>
                <td className="font-semibold">{r.strategy_name}</td>
                <td><code>{r.symbol}</code></td>
                <td className={r.metrics.total_return_pct != null && r.metrics.total_return_pct >= 0 ? "text-emerald-600" : "text-rose-600"}>{fmtPct(r.metrics.total_return_pct)}</td>
                <td>{fmtPct(r.metrics.annual_return_pct)}</td>
                <td>{r.metrics.sharpe?.toFixed(2) ?? "--"}</td>
                <td className="text-rose-600">{r.metrics.max_drawdown_pct != null ? `${Math.abs(r.metrics.max_drawdown_pct).toFixed(2)}%` : "--"}</td>
                <td><span className={`badge ${r.status === "completed" ? "badge-success" : "badge-ghost"}`}>{r.status}</span></td>
                <td className="text-xs text-slate-500">{r.created_at ? new Date(r.created_at).toLocaleString("zh-CN") : "--"}</td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={8} className="py-8 text-center text-slate-500">暂无快照记录</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  );
}