import { useState, useEffect, useCallback } from "react";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_INTEGRATION_HUB } from "../lib/demoCatalog";

type StackLayer = {
  ok?: boolean;
  reason?: string;
  detail?: Record<string, unknown>;
  enabled?: boolean;
};

type StackStatus = {
  layers?: Record<string, StackLayer>;
  mysql_integration_row_counts?: Record<string, number>;
};

type RealtimeStatus = {
  socketio_enabled?: boolean;
  quote_broadcast?: boolean;
  tick_stream?: boolean;
  rooms?: Record<string, number>;
};

type TaskEvent = { ts?: string; label?: string; detail?: string };
type ActiveJob = { task_name?: string; status?: string; args?: unknown };

const LAYER_LABELS: Record<string, string> = {
  mysql_enabled: "MySQL",
  timeseries_ohlcv: "QuestDB",
  quantml_factors: "QuantML",
  openbb_global: "OpenBB",
  celery_tasks: "Celery",
  execution_gateway: "QMT",
  realtime_ws: "WebSocket",
  kronos: "Kronos",
  fingpt: "FinGPT",
  quantml_agent: "AI Agent",
};

const QUALITY_LABELS = [
  { key: "data_freshness", label: "数据新鲜度" },
  { key: "async_throughput", label: "异步吞吐量" },
  { key: "external_deps", label: "外部依赖" },
  { key: "warmup_coverage", label: "预热覆盖" },
];

function StatusBadge({ ok, label }: { ok?: boolean; label: string }) {
  return (
    <div className={`quant-card flex items-center gap-2 ${ok ? "" : "border-[var(--quant-danger)]/30"}`}>
      <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${ok ? "bg-[var(--quant-accent)]" : "bg-[var(--quant-danger)]"}`} />
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
}

export default function IntegrationHub() {
  const [stack, setStack] = useState<StackStatus | null>(null);
  const [rt, setRt] = useState<RealtimeStatus | null>(null);
  const [tasks, setTasks] = useState<TaskEvent[]>([]);
  const [jobs, setJobs] = useState<ActiveJob[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [isDemo, setIsDemo] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, r, t, j] = await Promise.all([
        apiFetchV1<StackStatus>("/integration/stack-status"),
        apiFetchV1<RealtimeStatus>("/realtime/status"),
        apiFetchV1<{ items?: TaskEvent[] }>("/system/task-messages?limit=50"),
        apiFetchV1<{ items?: ActiveJob[] }>("/system/active-jobs"),
      ]);
      const empty = !s?.layers || !Object.keys(s.layers).length;
      if (empty) {
        setStack(DEMO_INTEGRATION_HUB.stack);
        setRt(DEMO_INTEGRATION_HUB.realtime);
        setTasks(DEMO_INTEGRATION_HUB.tasks);
        setJobs(DEMO_INTEGRATION_HUB.jobs);
        setIsDemo(true);
      } else {
        setStack(s);
        setRt(r);
        setTasks(t.items ?? []);
        setJobs(j.items ?? []);
        setIsDemo(false);
      }
    } catch {
      setStack(DEMO_INTEGRATION_HUB.stack);
      setRt(DEMO_INTEGRATION_HUB.realtime);
      setTasks(DEMO_INTEGRATION_HUB.tasks);
      setJobs(DEMO_INTEGRATION_HUB.jobs);
      setIsDemo(true);
    }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 8000);
    return () => clearInterval(iv);
  }, [load]);

  async function triggerSync() {
    setSyncing(true);
    try {
      await apiFetchV1("/system/timeseries-ohlcv-sync", { method: "POST" });
      setTimeout(load, 2000);
    } finally { setSyncing(false); }
  }

  const layers = stack?.layers ?? {};
  const counts = stack?.mysql_integration_row_counts ?? {};

  return (
    <div className="space-y-6">
      <PageQuickNav items={QUICK_NAV_PRESETS.integrationHub} />
      <div>
        <h1 className="page-title">集成中枢</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">系统组件状态、数据层、任务监控</p>
        <DemoBanner show={isDemo} />
      </div>

      {/* Status Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {Object.entries(LAYER_LABELS).map(([key, label]) => (
          <StatusBadge key={key} ok={layers[key]?.ok ?? layers[key]?.enabled} label={label} />
        ))}
      </div>

      {/* Quality Bars */}
      <div className="quant-card">
        <div className="text-sm font-bold mb-3">质量指标</div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {QUALITY_LABELS.map((q) => {
            const layer = Object.values(layers).find((l) => l.detail?.[q.key] != null);
            const val = (layer?.detail?.[q.key] as number) ?? 80;
            return (
              <div key={q.key}>
                <div className="flex justify-between text-xs text-[var(--quant-muted)] mb-1">
                  <span>{q.label}</span>
                  <span className="mono">{val}%</span>
                </div>
                <div className="h-2 rounded-full bg-[var(--quant-surface)] overflow-hidden">
                  <div className="h-full rounded-full bg-[var(--quant-accent)]" style={{ width: `${val}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Data Layer */}
        <div className="quant-card lg:col-span-2">
          <div className="text-sm font-bold mb-3">数据层</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
            {Object.entries(counts).map(([table, rows]) => (
              <div key={table} className="flex items-center justify-between bg-[var(--quant-surface)] rounded-lg px-3 py-2">
                <span className="truncate">{table}</span>
                <span className="mono text-xs shrink-0 ml-2">{rows.toLocaleString()}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-4">
            <button type="button" className="btn-brand !text-xs !px-3 !py-1.5" onClick={triggerSync} disabled={syncing}>
              {syncing ? "同步中..." : "QuestDB 增量同步"}
            </button>
            <button type="button" className="btn btn-ghost btn-xs" onClick={load}>刷新</button>
          </div>
        </div>

        {/* Active Jobs */}
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">活跃任务 ({jobs.length})</div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {jobs.length === 0 ? (
              <div className="text-sm text-[var(--quant-muted)]">无活跃任务</div>
            ) : jobs.map((j, i) => (
              <div key={i} className="text-xs py-1 border-b border-[var(--quant-line-soft)] last:border-0">
                <div className="font-bold">{j.task_name}</div>
                <div className="text-[var(--quant-muted)]">{j.status}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* WebSocket Status */}
      <div className="quant-card">
        <div className="text-sm font-bold mb-3">实时推送</div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <StatusBadge ok={rt?.socketio_enabled} label="SocketIO" />
          <StatusBadge ok={rt?.quote_broadcast} label="行情广播" />
          <StatusBadge ok={rt?.tick_stream} label="Tick 流" />
          {Object.entries(rt?.rooms ?? {}).slice(0, 2).map(([room, count]) => (
            <div key={room} className="quant-card text-center">
              <div className="mono font-bold">{count}</div>
              <div className="text-xs text-[var(--quant-muted)]">{room} 房间</div>
            </div>
          ))}
        </div>
      </div>

      {/* Task Log */}
      <div className="quant-card">
        <div className="text-sm font-bold mb-3">任务日志</div>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {tasks.slice(0, 20).map((t, i) => (
            <div key={i} className="flex items-start gap-2 text-xs py-1 border-b border-[var(--quant-line-soft)] last:border-0">
              <span className="text-[var(--quant-muted)] shrink-0 w-24">{t.ts ? new Date(t.ts).toLocaleTimeString() : "—"}</span>
              <span className="font-bold shrink-0">{t.label}</span>
              <span className="text-[var(--quant-muted)] truncate">{t.detail}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
