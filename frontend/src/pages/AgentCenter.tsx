import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types ── */
type AgentStatus = "idle" | "running" | "error" | "completed";

type Agent = {
  agent_id: string;
  name: string;
  description?: string;
  status: AgentStatus;
  type: string;
  last_run_at?: string;
  last_run_summary?: string;
  run_count: number;
  success_rate_pct?: number;
  tags?: string[];
};

type AgentsResponse = {
  items: Agent[];
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

function statusBadge(status: AgentStatus): string {
  switch (status) {
    case "running":
      return "badge-info";
    case "completed":
      return "badge-success";
    case "error":
      return "badge-error";
    case "idle":
    default:
      return "badge-ghost";
  }
}

function statusLabel(status: AgentStatus): string {
  switch (status) {
    case "running":
      return "运行中";
    case "completed":
      return "已完成";
    case "error":
      return "异常";
    case "idle":
    default:
      return "空闲";
  }
}

/* ── Component ── */
export function AgentCenterPage() {
  const [filterType, setFilterType] = useState("all");
  const [filterStatus, setFilterStatus] = useState<AgentStatus | "all">("all");

  const { data, error, isLoading } = useSWR(
    "agent-center/agents",
    () => apiFetchV1<AgentsResponse>("/agent-center/agents"),
    { refreshInterval: 30_000 },
  );

  const agents = data?.items ?? [];

  const types = [...new Set(agents.map((a: Agent) => a.type))];

  const filtered = agents.filter((a: Agent) => {
    if (filterType !== "all" && a.type !== filterType) return false;
    if (filterStatus !== "all" && a.status !== filterStatus) return false;
    return true;
  });

  if (isLoading && !agents.length) return <PageSkeleton rows={4} />;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Agent 中心</h1>
        <p className="text-sm text-slate-500">
          多智能体策略研究与执行管理
        </p>
      </div>

      {/* Filter Bar */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <select
          className="select select-bordered select-sm"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="all">全部类型</option>
          {types.map((t: string) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          className="select select-bordered select-sm"
          value={filterStatus}
          onChange={(e) =>
            setFilterStatus(e.target.value as AgentStatus | "all")
          }
        >
          <option value="all">全部状态</option>
          <option value="idle">空闲</option>
          <option value="running">运行中</option>
          <option value="completed">已完成</option>
          <option value="error">异常</option>
        </select>
      </div>

      {/* Error */}
      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      {/* Agent Card Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((a: Agent) => (
          <div
            key={a.agent_id}
            className="glass-card rounded-2xl p-5 space-y-4 hover:shadow-md transition-shadow"
          >
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-brand/10 flex items-center justify-center">
                    <svg
                      className="w-4 h-4 text-brand"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <div>
                    <div className="font-bold">{a.name}</div>
                    <div className="text-xs text-slate-500">{a.type}</div>
                  </div>
                </div>
              </div>
              <span className={`badge ${statusBadge(a.status)}`}>
                {statusLabel(a.status)}
                {a.status === "running" && (
                  <span className="loading loading-spinner loading-xs ml-1" />
                )}
              </span>
            </div>

            {/* Description */}
            {a.description && (
              <p className="text-xs text-slate-600 line-clamp-2">
                {a.description}
              </p>
            )}

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                <div className="text-xs text-slate-500">运行次数</div>
                <div className="text-sm font-bold">{a.run_count}</div>
              </div>
              <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                <div className="text-xs text-slate-500">成功率</div>
                <div className="text-sm font-bold">
                  {a.success_rate_pct != null
                    ? `${a.success_rate_pct.toFixed(0)}%`
                    : "--"}
                </div>
              </div>
            </div>

            {/* Last run */}
            {a.last_run_at && (
              <div className="text-xs text-slate-500">
                <span>上次运行：{fmtDate(a.last_run_at)}</span>
                {a.last_run_summary && (
                  <p className="mt-1 truncate">{a.last_run_summary}</p>
                )}
              </div>
            )}

            {/* Tags */}
            {a.tags && a.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {a.tags.map((tag) => (
                  <span key={tag} className="badge badge-ghost badge-sm">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Empty */}
      {!filtered.length && (
        <div className="py-12 text-center text-slate-500">
          {agents.length
            ? "没有匹配过滤条件的 Agent"
            : "暂无 Agent 数据"}
        </div>
      )}
    </div>
  );
}