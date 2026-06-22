import { useState, useEffect, useCallback } from "react";
import { apiFetchV1 } from "../lib/api";

type Snapshot = {
  overall_status?: string;
  health_banner?: { message?: string };
  sla?: { uptime_target_pct?: number; api_p95_ms?: number; decision_review_sla_hours?: number };
  critical_services?: { ok?: boolean; critical_missing?: string[]; required_missing?: string[] };
};

type TaskEvent = { ts?: string; label?: string; detail?: string };
type TraceEntry = { time?: string; trace_id?: string; query?: string; raw?: string };
type BeatRun = { recorded_at?: string; ok?: boolean; mode?: string; questdb_rows_written?: number };

function StatCard({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="quant-card text-center">
      <div className={`text-lg font-bold mono ${ok === false ? "text-down" : ok ? "text-up" : ""}`}>{value}</div>
      <div className="text-xs text-[var(--quant-muted)] mt-1">{label}</div>
    </div>
  );
}

export default function Observability() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [tasks, setTasks] = useState<TaskEvent[]>([]);
  const [traceId, setTraceId] = useState("");
  const [traceResults, setTraceResults] = useState<TraceEntry[]>([]);
  const [beatRuns, setBeatRuns] = useState<BeatRun[]>([]);

  const load = useCallback(async () => {
    try {
      const [s, t, b] = await Promise.all([
        apiFetchV1<Snapshot>("/system/observability/snapshot"),
        apiFetchV1<{ items?: TaskEvent[] }>("/system/task-messages?limit=40"),
        apiFetchV1<{ runs?: BeatRun[] }>("/data/timeseries-sync-history?limit=12&source=celery_beat"),
      ]);
      setSnap(s);
      setTasks(t.items ?? []);
      setBeatRuns(b.runs ?? []);
    } catch { /* keep state */ }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 15000);
    return () => clearInterval(iv);
  }, [load]);

  async function queryTrace() {
    if (!traceId.trim()) return;
    try {
      const r = await apiFetchV1<TraceEntry[]>(`/system/trace/${traceId}`);
      setTraceResults(Array.isArray(r) ? r : []);
    } catch { setTraceResults([]); }
  }

  const sla = snap?.sla;
  const cs = snap?.critical_services;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">观测台</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">系统可观测性、追踪、任务事件流</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="系统状态" value={snap?.overall_status ?? "—"} ok={snap?.overall_status === "healthy"} />
        <StatCard label="SLA 目标" value={sla?.uptime_target_pct != null ? `${sla.uptime_target_pct}%` : "—"} />
        <StatCard label="API P95" value={sla?.api_p95_ms != null ? `${sla.api_p95_ms}ms` : "—"} />
        <StatCard label="关键服务" value={cs?.ok ? "正常" : "异常"} ok={cs?.ok} />
        <StatCard label="事件数" value={String(tasks.length)} />
        <StatCard label="Beat 同步" value={beatRuns.length > 0 ? (beatRuns[0].ok ? "正常" : "异常") : "—"} ok={beatRuns[0]?.ok} />
      </div>

      {/* Warnings */}
      {snap?.health_banner?.message && (
        <div className="quant-card border-[var(--quant-warn)]/30 bg-[var(--quant-warn)]/5 text-sm">
          {snap.health_banner.message}
        </div>
      )}
      {cs && (cs.critical_missing?.length ?? 0) > 0 && (
        <div className="quant-card border-[var(--quant-danger)]/30 bg-[var(--quant-danger)]/5 text-sm">
          <span className="font-bold text-[var(--quant-danger)]">关键服务缺失: </span>
          {cs.critical_missing!.join(", ")}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Trace Query */}
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">Trace 查询</div>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={traceId}
              onChange={(e) => setTraceId(e.target.value)}
              placeholder="输入 Trace ID"
              className="input input-bordered input-sm flex-1 bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
              onKeyDown={(e) => e.key === "Enter" && queryTrace()}
            />
            <button type="button" className="btn btn-primary btn-sm" onClick={queryTrace}>查询</button>
          </div>
          {traceResults.length > 0 && (
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {traceResults.map((r, i) => (
                <div key={i} className="text-xs font-mono bg-[var(--quant-surface)] rounded p-2 break-all">
                  <span className="text-[var(--quant-muted)]">{r.time}</span>{" "}
                  {r.query ?? r.raw}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Task Events */}
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">任务事件流</div>
          <div className="space-y-1 max-h-72 overflow-y-auto">
            {tasks.length === 0 ? (
              <div className="text-sm text-[var(--quant-muted)]">暂无事件</div>
            ) : tasks.map((t, i) => (
              <div key={i} className="flex items-start gap-2 text-xs py-1 border-b border-[var(--quant-line-soft)] last:border-0">
                <span className="text-[var(--quant-muted)] shrink-0 w-28">{t.ts ? new Date(t.ts).toLocaleTimeString() : "—"}</span>
                <span className="font-bold shrink-0">{t.label}</span>
                <span className="text-[var(--quant-muted)] truncate">{t.detail}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Beat Sync History */}
      <div className="quant-card">
        <div className="text-sm font-bold mb-3">Beat 同步历史</div>
        {beatRuns.length === 0 ? (
          <div className="text-sm text-[var(--quant-muted)]">暂无记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table table-zebra table-sm">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>状态</th>
                  <th>模式</th>
                  <th>写入行数</th>
                </tr>
              </thead>
              <tbody>
                {beatRuns.map((r, i) => (
                  <tr key={i}>
                    <td className="text-xs">{r.recorded_at ? new Date(r.recorded_at).toLocaleString() : "—"}</td>
                    <td><span className={`badge-soft ${r.ok ? "!bg-[var(--quant-accent)]/10 !text-[var(--quant-accent)]" : "!bg-[var(--quant-danger)]/10 !text-[var(--quant-danger)]"}`}>{r.ok ? "成功" : "失败"}</span></td>
                    <td className="text-xs">{r.mode ?? "—"}</td>
                    <td className="mono text-xs">{r.questdb_rows_written?.toLocaleString() ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
