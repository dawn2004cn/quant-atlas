import { useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types ── */
type ReplayStep = {
  step_id: string;
  sequence: number;
  description: string;
  timestamp?: string;
  duration_ms?: number;
  status: "success" | "failure" | "skipped" | "running";
  details?: string;
  input_summary?: string;
  output_summary?: string;
};

type DecisionReplay = {
  replay_id: string;
  title: string;
  description?: string;
  session_id?: string;
  started_at: string;
  completed_at?: string;
  total_steps: number;
  steps: ReplayStep[];
  summary?: string;
};

type ReplayResponse = {
  items: DecisionReplay[];
  total: number;
};

/* ── Helpers ── */
function fmtDate(iso?: string): string {
  if (!iso) return "--";
  try {
    return new Date(iso).toLocaleString("zh-CN");
  } catch {
    return iso;
  }
}

function stepStatusIcon(status: string): string {
  switch (status) {
    case "success":
      return "✅";
    case "failure":
      return "❌";
    case "skipped":
      return "⏭";
    case "running":
      return "🔄";
    default:
      return "⬜";
  }
}

function stepStatusBadge(status: string): string {
  switch (status) {
    case "success":
      return "badge-success";
    case "failure":
      return "badge-error";
    case "skipped":
      return "badge-ghost";
    case "running":
      return "badge-info";
    default:
      return "badge-ghost";
  }
}

function fmtDuration(ms?: number): string {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`;
}

/* ── Component ── */
export function DecisionReplaySpacePage() {
  const [expandedReplay, setExpandedReplay] = useState<string | null>(null);

  const { data, error, isLoading } = useSWR(
    "decision-replay",
    () => apiFetchV1<ReplayResponse>("/decision-replay"),
    { refreshInterval: 30_000 },
  );

  const replays = data?.items ?? [];

  if (isLoading && !replays.length) return <PageSkeleton rows={4} />;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.decisionReplay} />
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">决策回放空间</h1>
        <p className="text-sm text-slate-500">
          逐步骤回放研究与投决过程，溯源每个决策节点
        </p>
      </div>

      {/* Error */}
      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      {/* Replay list */}
      <div className="space-y-4">
        {replays.map((r: DecisionReplay) => {
          const isExpanded = expandedReplay === r.replay_id;
          const sortedSteps = [...(r.steps ?? [])].sort(
            (a, b) => a.sequence - b.sequence,
          );

          return (
            <div
              key={r.replay_id}
              className="glass-card rounded-2xl overflow-hidden"
            >
              {/* Summary header */}
              <button
                type="button"
                className="w-full p-5 text-left hover:bg-base-200/50 transition-colors"
                onClick={() =>
                  setExpandedReplay(
                    isExpanded ? null : r.replay_id,
                  )
                }
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold">{r.title}</h3>
                      <span className="badge badge-ghost text-xs">
                        {r.total_steps} 步
                      </span>
                    </div>
                    {r.description && (
                      <p className="mt-1 text-sm text-slate-500">
                        {r.description}
                      </p>
                    )}
                  </div>
                  <div className="text-right text-xs text-slate-500 space-y-1">
                    <div>{fmtDate(r.started_at)}</div>
                    {r.completed_at && <div>完成于 {fmtDate(r.completed_at)}</div>}
                    {r.session_id && (
                      <div className="badge badge-ghost badge-xs">
                        {r.session_id}
                      </div>
                    )}
                  </div>
                </div>

                {/* Mini steps bar */}
                {!isExpanded && sortedSteps.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {sortedSteps.map((s) => (
                      <span
                        key={s.step_id}
                        className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800"
                      >
                        <span>{stepStatusIcon(s.status)}</span>
                        <span className="truncate max-w-[100px]">
                          {s.description}
                        </span>
                      </span>
                    ))}
                  </div>
                )}
                {r.summary && !isExpanded && (
                  <p className="mt-2 text-xs text-slate-600 line-clamp-2">
                    {r.summary}
                  </p>
                )}
              </button>

              {/* Expanded timeline */}
              {isExpanded && (
                <div className="border-t border-base-200 px-5 pb-5">
                  {/* Summary */}
                  {r.summary && (
                    <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-900">
                      {r.summary}
                    </div>
                  )}

                  {/* Timeline */}
                  <div className="mt-4 space-y-0">
                    {sortedSteps.map((s, idx) => (
                      <div
                        key={s.step_id}
                        className="relative flex gap-4 pb-6"
                      >
                        {/* Timeline line */}
                        {idx < sortedSteps.length - 1 && (
                          <div className="absolute left-[11px] top-6 bottom-0 w-0.5 bg-base-300" />
                        )}

                        {/* Dot */}
                        <div className="relative z-10 mt-1 flex-shrink-0">
                          <div
                            className={`w-6 h-6 rounded-full flex items-center justify-center text-xs border-2 ${
                              s.status === "success"
                                ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950"
                                : s.status === "failure"
                                  ? "border-rose-500 bg-rose-50 dark:bg-rose-950"
                                  : s.status === "running"
                                    ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
                                    : "border-slate-300 bg-slate-50 dark:bg-slate-800"
                            }`}
                          >
                            {s.sequence}
                          </div>
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-sm">
                              {s.description}
                            </span>
                            {s.duration_ms != null && (
                              <span className="text-xs text-slate-400">
                                {fmtDuration(s.duration_ms)}
                              </span>
                            )}
                            <span
                              className={`badge badge-sm ${stepStatusBadge(s.status)}`}
                            >
                              {s.status}
                            </span>
                          </div>

                          {s.timestamp && (
                            <div className="mt-1 text-xs text-slate-400">
                              {fmtDate(s.timestamp)}
                            </div>
                          )}

                          {s.details && (
                            <p className="mt-1 text-xs text-slate-600">
                              {s.details}
                            </p>
                          )}

                          {/* Input/Output collapsible */}
                          {(s.input_summary || s.output_summary) && (
                            <div className="mt-2 flex gap-2 text-xs">
                              {s.input_summary && (
                                <div className="flex-1 rounded-md bg-slate-50 p-2 dark:bg-slate-900">
                                  <span className="font-medium text-slate-500">
                                    输入
                                  </span>
                                  <p className="mt-0.5 text-slate-600 truncate">
                                    {s.input_summary}
                                  </p>
                                </div>
                              )}
                              {s.output_summary && (
                                <div className="flex-1 rounded-md bg-slate-50 p-2 dark:bg-slate-900">
                                  <span className="font-medium text-slate-500">
                                    输出
                                  </span>
                                  <p className="mt-0.5 text-slate-600 truncate">
                                    {s.output_summary}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empty */}
      {!replays.length && (
        <div className="py-12 text-center text-slate-500">
          暂无决策回放记录
        </div>
      )}
    </div>
  );
}