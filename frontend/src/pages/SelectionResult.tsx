import { useState } from "react";
import { useParams } from "react-router-dom";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types ── */
type SelectionCandidate = {
  symbol: string;
  name?: string;
  score: number;
  rank: number;
  reason?: string;
  expected_return_pct?: number;
  risk_level?: string;
  strategy_name?: string;
  indicators?: Record<string, number>;
};

type SelectionResultData = {
  task_id: string;
  status: string;
  created_at: string;
  completed_at?: string;
  strategy_name?: string;
  total_candidates: number;
  candidates: SelectionCandidate[];
};

/* ── Format helpers ── */
function fmtPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function fmtDate(iso?: string): string {
  if (!iso) return "--";
  try {
    return new Date(iso).toLocaleString("zh-CN");
  } catch {
    return iso;
  }
}

function riskBadge(level?: string): string {
  switch (level?.toLowerCase()) {
    case "低":
    case "low":
      return "badge-success";
    case "中":
    case "medium":
      return "badge-warning";
    case "高":
    case "high":
      return "badge-error";
    default:
      return "badge-ghost";
  }
}

/* ── Component ── */
export function SelectionResultPage() {
  const { taskId = "" } = useParams();
  const [sortBy, setSortBy] = useState<"score" | "expected_return" | "rank">(
    "score",
  );

  const { data, error, isLoading } = useSWR(
    taskId ? ["selection/result", taskId] : null,
    () => apiFetchV1<SelectionResultData>(`/selection/result/${encodeURIComponent(taskId)}`),
    { refreshInterval: taskId ? 10_000 : undefined },
  );

  if (isLoading) return <PageSkeleton rows={4} />;

  if (error) {
    return (
      <div className="space-y-5">
        <h1 className="text-2xl font-bold">选股结果</h1>
        <div className="alert alert-error">加载失败：{error.message}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-5">
        <h1 className="text-2xl font-bold">选股结果</h1>
        <div className="alert alert-warning">未找到该选股任务数据</div>
      </div>
    );
  }

  const candidates = [...(data.candidates ?? [])].sort((a, b) => {
    switch (sortBy) {
      case "expected_return":
        return (b.expected_return_pct ?? 0) - (a.expected_return_pct ?? 0);
      case "rank":
        return (a.rank ?? 999) - (b.rank ?? 999);
      case "score":
      default:
        return (b.score ?? 0) - (a.score ?? 0);
    }
  });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">选股结果</h1>
          <p className="text-sm text-slate-500">
            {data.strategy_name ? `策略：${data.strategy_name} | ` : ""}
            共 {data.total_candidates ?? candidates.length} 只候选标的
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>任务状态：</span>
          <span
            className={`badge ${
              data.status === "completed" ? "badge-success" : "badge-ghost"
            }`}
          >
            {data.status}
          </span>
          <span>创建于 {fmtDate(data.created_at)}</span>
        </div>
      </div>

      {/* Status info for in-progress tasks */}
      {data.status !== "completed" && (
        <div className="alert alert-info">
          任务正在执行中（{data.status}），结果将自动刷新…
        </div>
      )}

      {/* Toolbar */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <span className="text-xs text-slate-500">排序：</span>
        <select
          className="select select-bordered select-sm"
          value={sortBy}
          onChange={(e) =>
            setSortBy(e.target.value as "score" | "expected_return" | "rank")
          }
        >
          <option value="score">综合评分</option>
          <option value="expected_return">预期收益</option>
          <option value="rank">排名</option>
        </select>
      </div>

      {/* Candidate Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {candidates.map((c: SelectionCandidate) => (
          <div
            key={`${c.symbol}-${c.rank}`}
            className="glass-card rounded-2xl p-4 space-y-3"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand/10 text-xs font-bold text-brand">
                    {c.rank}
                  </span>
                  <code className="text-sm">{c.symbol}</code>
                </div>
                <div className="mt-1 text-sm font-medium">{c.name ?? "--"}</div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-brand">
                  {c.score.toFixed(1)}
                </div>
                <div className="text-xs text-slate-500">综合评分</div>
              </div>
            </div>

            {/* Expected return & risk */}
            <div className="flex gap-4 text-xs">
              {c.expected_return_pct != null && (
                <div>
                  <span className="text-slate-500">预期收益 </span>
                  <span
                    className={`font-semibold ${
                      c.expected_return_pct >= 0
                        ? "text-emerald-600"
                        : "text-rose-600"
                    }`}
                  >
                    {fmtPct(c.expected_return_pct)}
                  </span>
                </div>
              )}
              {c.risk_level && (
                <div>
                  <span className="text-slate-500">风险 </span>
                  <span className={`badge ${riskBadge(c.risk_level)}`}>
                    {c.risk_level}
                  </span>
                </div>
              )}
            </div>

            {/* Reason */}
            {c.reason && (
              <p className="text-xs text-slate-600 leading-relaxed">
                {c.reason}
              </p>
            )}

            {/* Indicators */}
            {c.indicators && Object.keys(c.indicators).length > 0 && (
              <div className="flex flex-wrap gap-2 border-t border-base-200 pt-2">
                {Object.entries(c.indicators).map(([key, val]) => (
                  <span
                    key={key}
                    className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800"
                  >
                    <span className="text-slate-500">{key}</span>
                    <span className="font-medium">
                      {typeof val === "number" ? val.toFixed(2) : String(val)}
                    </span>
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Empty */}
      {!candidates.length && (
        <div className="py-12 text-center text-slate-500">暂无候选标的</div>
      )}
    </div>
  );
}