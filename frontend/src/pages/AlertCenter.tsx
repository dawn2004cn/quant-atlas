import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types ── */
type AlertSeverity = "info" | "warning" | "critical";

type Alert = {
  id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  source: string;
  symbol?: string;
  is_read: boolean;
  created_at: string;
  action_url?: string;
};

type AlertsResponse = {
  items: Alert[];
  total: number;
  unread_count: number;
};

/* ── API ── */
function fetchAlerts(): Promise<{ data: AlertsResponse }> {
  return apiFetchV1("/alert-center/alerts");
}

function fmtDate(iso?: string): string {
  if (!iso) return "--";
  try {
    return new Date(iso).toLocaleString("zh-CN");
  } catch {
    return iso;
  }
}

function severityBadge(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "badge-error";
    case "warning":
      return "badge-warning";
    case "info":
    default:
      return "badge-info";
  }
}

function severityLabel(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "严重";
    case "warning":
      return "预警";
    case "info":
    default:
      return "提示";
  }
}

/* ── Component ── */
export function AlertCenterPage() {
  const [filterSeverity, setFilterSeverity] = useState<AlertSeverity | "all">("all");
  const [filterRead, setFilterRead] = useState<"all" | "unread" | "read">("all");

  const { data, error, isLoading } = useSWR(
    "alert-center/alerts",
    () => fetchAlerts(),
    { refreshInterval: 60_000 },
  );

  const alerts = data?.data?.items ?? [];
  const unreadCount = data?.data?.unread_count ?? 0;

  const filtered = alerts.filter((a: Alert) => {
    if (filterSeverity !== "all" && a.severity !== filterSeverity) return false;
    if (filterRead === "unread" && a.is_read) return false;
    if (filterRead === "read" && !a.is_read) return false;
    return true;
  });

  if (isLoading && !alerts.length) return <PageSkeleton rows={5} />;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">预警中心</h1>
          <p className="text-sm text-slate-500">
            实时监控异动、风控触发与重要资讯
          </p>
        </div>
        <div className="flex gap-2">
          <span className="btn btn-ghost btn-sm">
            未读 <span className="badge badge-error ml-1">{unreadCount}</span>
          </span>
          <button type="button" className="btn btn-primary btn-sm">
            全部标记已读
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <select
          className="select select-bordered select-sm"
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value as AlertSeverity | "all")}
        >
          <option value="all">全部级别</option>
          <option value="critical">严重</option>
          <option value="warning">预警</option>
          <option value="info">提示</option>
        </select>
        <select
          className="select select-bordered select-sm"
          value={filterRead}
          onChange={(e) => setFilterRead(e.target.value as "all" | "unread" | "read")}
        >
          <option value="all">全部状态</option>
          <option value="unread">未读</option>
          <option value="read">已读</option>
        </select>
      </div>

      {/* Error */}
      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      {/* Alert List */}
      <section className="glass-card overflow-x-auto">
        <table className="table w-full">
          <thead>
            <tr>
              <th className="w-8"></th>
              <th>级别</th>
              <th>标题</th>
              <th>来源</th>
              <th>标的</th>
              <th>时间</th>
              <th className="w-24">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a: Alert) => (
              <tr
                key={a.id}
                className={a.is_read ? "" : "bg-base-200/50 font-medium"}
              >
                <td>
                  {!a.is_read && (
                    <span className="block w-2 h-2 rounded-full bg-brand" />
                  )}
                </td>
                <td>
                  <span className={`badge ${severityBadge(a.severity)}`}>
                    {severityLabel(a.severity)}
                  </span>
                </td>
                <td className="max-w-xs truncate">
                  <div className="font-medium">{a.title}</div>
                  <div className="text-xs text-slate-500 truncate">{a.message}</div>
                </td>
                <td className="text-xs text-slate-500">{a.source}</td>
                <td>
                  {a.symbol ? <code>{a.symbol}</code> : <span className="text-slate-400">--</span>}
                </td>
                <td className="text-xs text-slate-500 whitespace-nowrap">
                  {fmtDate(a.created_at)}
                </td>
                <td>
                  <div className="flex gap-1">
                    {a.action_url && (
                      <a
                        href={a.action_url}
                        className="btn btn-ghost btn-xs"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        详情
                      </a>
                    )}
                    <button
                      type="button"
                      className={`btn btn-ghost btn-xs ${
                        a.is_read ? "text-slate-400" : ""
                      }`}
                    >
                      {a.is_read ? "已读" : "标记已读"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!filtered.length && (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-500">
                  暂无预警
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}