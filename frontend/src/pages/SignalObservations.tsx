import { useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_OBSERVATIONS } from "../lib/demoCatalog";

type Observation = {
  id: string;
  symbol: string;
  name: string;
  signal_type: string;
  trigger_status: "triggered" | "pending" | "expired";
  entry_price: number;
  current_price: number;
  target_price: number;
  stop_loss: number;
  pnl_pct: number;
  created_at: string;
  updated_at: string;
};

type ObservationsData = {
  observations: Observation[];
};

const TRIGGER_LABEL: Record<string, string> = {
  triggered: "已触发",
  pending: "待触发",
  expired: "已过期",
};

const TRIGGER_CLASS: Record<string, string> = {
  triggered: "badge-success",
  pending: "badge-info",
  expired: "badge-ghost",
};

export function SignalObservationsPage() {
  const [filter, setFilter] = useState<string>("all");

  const { data, error, isLoading, mutate } = useSWR(
    "signal-observations",
    () => apiFetchV1<ObservationsData>("/signal-observations"),
    { refreshInterval: 30_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={5} />;

  const live = data?.observations ?? [];
  const isDemo = Boolean(error) || (!isLoading && !live.length);
  const observations = (isDemo ? DEMO_OBSERVATIONS : live).filter(
    (o) => filter === "all" || o.trigger_status === filter,
  );

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.signalObservations} />
      <CoreWorkflowStrip />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">信号观测</h1>
          <p className="text-sm text-slate-500">信号触发状态与入场价格追踪</p>
          <DemoBanner show={isDemo} />
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      {error ? <div className="alert alert-error">加载失败：{error.message}</div> : null}

      <div className="flex flex-wrap gap-2">
        {(["all", "pending", "triggered", "expired"] as const).map((s) => (
          <button
            key={s}
            type="button"
            className={`btn btn-sm ${filter === s ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setFilter(s)}
          >
            {s === "all" ? "全部" : TRIGGER_LABEL[s]}
          </button>
        ))}
      </div>

      {observations.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-lg font-semibold text-slate-500">暂无信号观测数据</p>
          <p className="text-sm text-slate-400 mt-2">
            {filter === "all"
              ? "添加信号策略后，观测结果将在此展示"
              : "当前筛选条件下没有观测记录"}
          </p>
        </div>
      ) : (
        <div className="glass-card overflow-x-auto p-4">
          <table className="table table-sm">
            <thead>
              <tr>
                <th>标的</th>
                <th>信号类型</th>
                <th>触发状态</th>
                <th>入场价</th>
                <th>当前价</th>
                <th>目标价</th>
                <th>止损价</th>
                <th>盈亏</th>
                <th>更新时间</th>
              </tr>
            </thead>
            <tbody>
              {observations.map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link className="link" to={`/stock/${encodeURIComponent(o.symbol)}?m=CN`}>
                      <div className="font-medium">{o.symbol}</div>
                      <div className="text-xs text-slate-500">{o.name}</div>
                    </Link>
                  </td>
                  <td><span className="badge badge-ghost badge-sm">{o.signal_type}</span></td>
                  <td>
                    <span className={`badge badge-sm ${TRIGGER_CLASS[o.trigger_status] ?? "badge-ghost"}`}>
                      {TRIGGER_LABEL[o.trigger_status] ?? o.trigger_status}
                    </span>
                  </td>
                  <td className="font-mono text-sm">{o.entry_price.toFixed(2)}</td>
                  <td className="font-mono text-sm">{o.current_price.toFixed(2)}</td>
                  <td className="font-mono text-sm text-emerald-600">{o.target_price.toFixed(2)}</td>
                  <td className="font-mono text-sm text-rose-600">{o.stop_loss.toFixed(2)}</td>
                  <td>
                    <span className={`font-mono text-sm ${o.pnl_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {o.pnl_pct >= 0 ? "+" : ""}{o.pnl_pct.toFixed(2)}%
                    </span>
                  </td>
                  <td className="text-xs text-slate-500">{o.updated_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}