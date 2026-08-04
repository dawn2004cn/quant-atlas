import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { fetchMlflowRuns } from "../lib/api";
import type { MlflowRun } from "../types/mlflow";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

function formatPct(value: number | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  const pct = Math.abs(value) <= 1 ? value * 100 : value;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

function formatDate(ms: number | undefined) {
  if (!ms) return "—";
  const d = new Date(ms);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

function mapRun(run: MlflowRun) {
  const metrics = run.metrics ?? {};
  const params = run.params ?? {};
  const totalReturn = metrics.total_return;
  let returnsPct = totalReturn;
  if (returnsPct != null && Math.abs(returnsPct) <= 1) {
    returnsPct *= 100;
  }
  return {
    id: run.run_id,
    name: run.run_name || `${params.strategy_name ?? "strategy"} - ${params.symbol ?? ""}`,
    strategy: params.strategy_name ?? run.run_name ?? "—",
    symbol: params.symbol ?? "—",
    date: formatDate(run.start_time),
    returns: returnsPct,
    sharpe: metrics.sharpe ?? metrics.sharpe_ratio,
    maxdd: metrics.max_drawdown ?? metrics.max_drawdown_pct,
    uiUrl: run.ui_url,
    params,
  };
}

export function RunHistoryPage() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const { data, error, isLoading, mutate } = useSWR("mlflow-run-history", () =>
    fetchMlflowRuns(50),
  );

  const runs = useMemo(
    () => (data?.runs ?? []).map(mapRun),
    [data?.runs],
  );

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 4) next.add(id);
      return next;
    });
  }

  const compareHref = useMemo(() => {
    const picked = runs.filter((r) => selected.has(r.id));
    const symbols = [...new Set(picked.map((r) => r.symbol).filter((s) => s && s !== "—"))];
    if (picked.length < 2 || symbols.length !== 1) return null;
    const strategies = [...new Set(picked.map((r) => r.strategy))].join(",");
    const params = new URLSearchParams({
      symbol: symbols[0],
      strategies,
    });
    const start = picked[0]?.params?.start;
    const end = picked[0]?.params?.end;
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    return `/backtest?${params.toString()}&duel=1`;
  }, [runs, selected]);

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.runHistory} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">回测历史</h1>
          <p className="text-sm text-zinc-500">
            MLflow 实验记录 · <code>/api/v1/mlflow/runs</code>
          </p>
        </div>
        <button type="button" className="rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:bg-zinc-800/60 hover:text-zinc-200" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      {isLoading ? <p className="text-zinc-500">加载中…</p> : null}
      {error ? (
        <p className="text-error">加载失败：{error instanceof Error ? error.message : "unknown"}</p>
      ) : null}
      {!isLoading && data && !data.available ? (
        <Panel className="p-6 text-sm text-zinc-500">
          MLflow 未配置。请设置 <code>MLFLOW_TRACKING_URI</code> 并完成一次回测后重试。
          也可使用<a className="link mx-1" href="/run-history">经典版历史页</a>。
        </Panel>
      ) : null}

      {data?.available && runs.length === 0 ? (
        <Panel className="p-6 text-sm text-zinc-500">暂无回测记录。</Panel>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        {runs.map((run) => {
          const isSelected = selected.has(run.id);
          const positive = (run.returns ?? 0) >= 0;
          return (
            <button
              key={run.id}
              type="button"
              className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 text-left p-4 transition ${isSelected ? "ring-2 ring-brand" : ""}`}
              onClick={() => toggle(run.id)}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-semibold">{run.name}</div>
                  <div className="text-xs text-zinc-500">{run.date}</div>
                </div>
                <input type="checkbox" readOnly checked={isSelected} />
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center text-sm">
                <div>
                  <div className={positive ? "text-emerald-400" : "text-rose-400"}>
                    {formatPct(run.returns)}
                  </div>
                  <div className="text-xs text-zinc-500">总收益</div>
                </div>
                <div>
                  <div>{run.sharpe != null ? Number(run.sharpe).toFixed(2) : "—"}</div>
                  <div className="text-xs text-zinc-500">夏普</div>
                </div>
                <div>
                  <div className="text-rose-400">{formatPct(run.maxdd)}</div>
                  <div className="text-xs text-zinc-500">最大回撤</div>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span className="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold bg-zinc-800/60 text-zinc-400">{run.strategy}</span>
                <span className="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold bg-zinc-800/60 text-zinc-400">{run.symbol}</span>
                {run.uiUrl ? (
                  <a
                    className="link"
                    href={run.uiUrl}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    MLflow
                  </a>
                ) : null}
              </div>
            </button>
          );
        })}
      </div>

      {selected.size >= 2 ? (
        <Panel className="flex flex-wrap items-center justify-between gap-3 p-4">
          <span className="text-sm">已选 {selected.size} 条（最多 4 条）</span>
          {compareHref ? (
            <Link className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30 transition-colors hover:bg-emerald-500/20" to={compareHref}>
              在回测页对决
            </Link>
          ) : (
            <span className="text-xs text-zinc-500">对比需选择同一标的的记录</span>
          )}
        </Panel>
      ) : null}
    </div>
  );
}
