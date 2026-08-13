import { useState, useEffect, useCallback } from "react";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_OBSERVABILITY } from "../lib/demoCatalog";

type Snapshot = {
  overall_status?: string;
  health_banner?: {
    message?: string;
    level?: string;
    quotes_full_dump_warn?: boolean;
    quotes_full_dump_count?: number;
    quotes_full_dump_threshold?: number;
  };
  sla?: { uptime_target_pct?: number; api_p95_ms?: number; decision_review_sla_hours?: number };
  critical_services?: { ok?: boolean; critical_missing?: string[]; required_missing?: string[] };
  task_messages?: TaskEvent[];
  timeseries_beat_runs?: BeatRun[];
  quotes_api?: {
    full_dump_count?: number;
    symbol_batch_count?: number;
    last_full_dump_at?: string | null;
    last_full_dump_rows?: number;
    backend?: string;
    recent_dumps?: Array<{ at?: string; market?: string; rows?: number }>;
    trend_rows?: number[];
  };
  alert_ops?: {
    alert_dispatch_beat?: boolean;
    alert_dispatch_beat_minutes?: number;
    quotes_dump_monitor_beat?: boolean;
    quotes_dump_monitor_beat_minutes?: number;
    quotes_dump_auto_dispatch?: boolean;
    quotes_full_dump_warn?: boolean;
    quotes_full_dump_count?: number;
    quotes_full_dump_threshold?: number;
    preferred_endpoint?: string;
  };
};

type TaskEvent = { ts?: string; label?: string; detail?: string; event?: string; task_name?: string };
type TraceEntry = { time?: string; trace_id?: string; query?: string; raw?: string };
type BeatRun = { recorded_at?: string; ok?: boolean; mode?: string; questdb_rows_written?: number };

type AdapterRow = {
  adapter_id?: string;
  market?: string;
  phase?: string;
  ready?: boolean;
  sim_ready?: boolean;
  session_wired?: boolean;
  contracts?: boolean;
  detail?: Record<string, unknown>;
};

type ProbeReport = {
  ok?: boolean;
  passed?: number;
  failed?: number;
  mode?: string;
  checks?: Array<{ id?: string; title?: string; passed?: boolean; required?: boolean; detail?: string }>;
};

function StatCard({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="quant-card text-center">
      <div className={`text-lg font-bold mono ${ok === false ? "text-down" : ok ? "text-up" : ""}`}>{value}</div>
      <div className="text-xs text-[var(--quant-muted)] mt-1">{label}</div>
    </div>
  );
}

function DumpTrendBars({ rows }: { rows: number[] }) {
  if (!rows.length) {
    return <div className="text-xs text-[var(--quant-muted)]">暂无近次全量 dump 采样</div>;
  }
  const max = Math.max(...rows, 1);
  return (
    <div className="flex h-16 items-end gap-1" aria-label="全量 quotes dump 行数趋势">
      {rows.map((n, i) => (
        <div
          key={`${i}-${n}`}
          className="min-w-[6px] flex-1 rounded-t bg-amber-500/70"
          style={{ height: `${Math.max(8, Math.round((n / max) * 100))}%` }}
          title={`${n} 行`}
        />
      ))}
    </div>
  );
}

export default function Observability() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [traceId, setTraceId] = useState("");
  const [traceResults, setTraceResults] = useState<TraceEntry[]>([]);
  const [adapters, setAdapters] = useState<AdapterRow[]>([]);
  const [probeBusy, setProbeBusy] = useState<"qmt" | "ibkr" | "rl" | null>(null);
  const [probeReport, setProbeReport] = useState<ProbeReport | null>(null);
  const [rlStatus, setRlStatus] = useState<{
    live_enabled?: boolean;
    has_policy?: boolean;
    message?: string;
    policy?: { metrics?: Record<string, number>; ts?: string };
  } | null>(null);

  const [snapFailed, setSnapFailed] = useState(false);

  const load = useCallback(async () => {
    try {
      const s = await apiFetchV1<Snapshot>("/system/observability/snapshot");
      setSnap(s);
      setSnapFailed(false);
    } catch {
      setSnapFailed(true);
    }
  }, []);

  const loadAdapters = useCallback(async () => {
    try {
      const r = await apiFetchV1<{ adapters?: AdapterRow[] }>("/system/execution-adapters");
      setAdapters(Array.isArray(r?.adapters) ? r.adapters : []);
    } catch {
      setAdapters([]);
    }
  }, []);

  const loadRl = useCallback(async () => {
    try {
      const r = await apiFetchV1<typeof rlStatus>("/strategy/rl-research/status");
      setRlStatus(r ?? null);
    } catch {
      setRlStatus(null);
    }
  }, []);

  useEffect(() => {
    void load();
    void loadAdapters();
    void loadRl();
    const iv = setInterval(() => {
      void load();
      void loadAdapters();
      void loadRl();
    }, 20000);
    return () => clearInterval(iv);
  }, [load, loadAdapters, loadRl]);

  async function queryTrace() {
    if (!traceId.trim()) return;
    try {
      const r = await apiFetchV1<TraceEntry[]>(`/system/trace/${traceId}`);
      setTraceResults(Array.isArray(r) ? r : []);
    } catch {
      setTraceResults([]);
    }
  }

  async function runProbe(kind: "qmt" | "ibkr") {
    setProbeBusy(kind);
    try {
      const path =
        kind === "qmt" ? "/system/qmt-integration-probe" : "/system/ibkr-ctp-integration-probe";
      const r = await apiFetchV1<ProbeReport>(path, { method: "POST" });
      setProbeReport(r ?? null);
    } catch {
      setProbeReport({ ok: false, failed: 1, checks: [{ title: "探针请求失败", passed: false }] });
    } finally {
      setProbeBusy(null);
      void loadAdapters();
    }
  }

  const isDemo = snapFailed || !snap;
  const viewSnap = isDemo ? (DEMO_OBSERVABILITY as Snapshot) : snap;
  const sla = viewSnap?.sla;
  const cs = viewSnap?.critical_services;
  const tasks = viewSnap?.task_messages ?? [];
  const beatRuns = viewSnap?.timeseries_beat_runs ?? [];
  const quotesApi = viewSnap?.quotes_api;
  const fullDumpCount = quotesApi?.full_dump_count ?? 0;
  const alertOps = viewSnap?.alert_ops;

  return (
    <div className="space-y-6">
      <PageQuickNav items={QUICK_NAV_PRESETS.observability} />
      <div>
        <h1 className="page-title">观测台</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">系统可观测性、追踪、任务事件与执行适配器</p>
        <DemoBanner show={isDemo} />
      </div>

      <div className="grid grid-cols-3 lg:grid-cols-7 gap-3">
        <StatCard
          label="系统状态"
          value={viewSnap?.overall_status ?? "—"}
          ok={viewSnap?.overall_status === "healthy" || viewSnap?.overall_status === "ok"}
        />
        <StatCard label="SLA 目标" value={sla?.uptime_target_pct != null ? `${sla.uptime_target_pct}%` : "—"} />
        <StatCard label="API P95" value={sla?.api_p95_ms != null ? `${sla.api_p95_ms}ms` : "—"} />
        <StatCard label="关键服务" value={cs?.ok ? "正常" : "异常"} ok={cs?.ok} />
        <StatCard label="事件数" value={String(tasks.length)} />
        <StatCard
          label="Beat 同步"
          value={beatRuns.length > 0 ? (beatRuns[0].ok ? "正常" : "异常") : "—"}
          ok={beatRuns[0]?.ok}
        />
        <StatCard label="全量 quotes" value={String(fullDumpCount)} ok={fullDumpCount === 0} />
      </div>

      {fullDumpCount > 0 && (
        <div className="quant-card qa-tone-banner--warn text-sm">
          累计 {fullDumpCount} 次无 symbol 的全量{" "}
          <code className="font-mono text-xs">/markets/*/quotes</code> dump
          {quotesApi?.last_full_dump_at ? ` · 最近 ${quotesApi.last_full_dump_at}` : ""}
          {quotesApi?.last_full_dump_rows != null ? ` · ${quotesApi.last_full_dump_rows} 行` : ""}
          {quotesApi?.backend ? ` · backend=${quotesApi.backend}` : ""}。请改用{" "}
          <code className="font-mono text-xs">quotes/page</code>。
        </div>
      )}

      {alertOps && (
        <div className="quant-card text-sm space-y-1">
          <div className="font-bold">告警运维 Beat</div>
          <div className="text-xs text-[var(--quant-muted)] font-mono">
            alert_dispatch={alertOps.alert_dispatch_beat ? `on/${alertOps.alert_dispatch_beat_minutes ?? "?"}m` : "off"}
            {" · "}
            dump_monitor=
            {alertOps.quotes_dump_monitor_beat
              ? `on/${alertOps.quotes_dump_monitor_beat_minutes ?? "?"}m`
              : "off"}
            {" · "}
            auto_dispatch={alertOps.quotes_dump_auto_dispatch ? "on" : "off"}
            {alertOps.quotes_full_dump_warn
              ? ` · warn dump=${alertOps.quotes_full_dump_count ?? 0}/thr=${alertOps.quotes_full_dump_threshold ?? 1}`
              : ""}
            {" · preferred="}
            {alertOps.preferred_endpoint ?? "quotes/page"}
          </div>
        </div>
      )}

      {(quotesApi?.trend_rows?.length ?? 0) > 0 && (
        <div className="quant-card space-y-2">
          <div className="text-sm font-bold">全量 quotes dump 近次行数</div>
          <DumpTrendBars rows={quotesApi?.trend_rows ?? []} />
          <div className="text-[10px] text-[var(--quant-muted)]">
            最近 {quotesApi?.recent_dumps?.length ?? 0} 次采样（最多 24）
          </div>
        </div>
      )}

      {viewSnap?.health_banner?.message && (
        <div className="quant-card qa-tone-banner--warn text-sm">
          {viewSnap.health_banner.message}
          {viewSnap.health_banner.quotes_full_dump_warn ? (
            <span className="ml-2 text-[10px] font-mono text-[var(--quant-muted)]">
              dump={viewSnap.health_banner.quotes_full_dump_count ?? 0}/thr=
              {viewSnap.health_banner.quotes_full_dump_threshold ?? 1}
            </span>
          ) : null}
        </div>
      )}
      {cs && (cs.critical_missing?.length ?? 0) > 0 && (
        <div className="quant-card qa-tone-banner--danger text-sm">
          <span className="font-bold" style={{ color: "var(--tone-danger)" }}>
            关键服务缺失:{" "}
          </span>
          {cs.critical_missing!.join(", ")}
        </div>
      )}

      <div className="quant-card space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-bold">执行适配器</div>
            <div className="text-xs text-[var(--quant-muted)]">
              QMT / CCXT / IBKR / CTP · sim_ready 与 live dry-run 状态
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn btn-sm btn-soft"
              disabled={probeBusy !== null}
              onClick={() => void runProbe("qmt")}
            >
              {probeBusy === "qmt" ? "探针中…" : "QMT 联调探针"}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              disabled={probeBusy !== null}
              onClick={() => void runProbe("ibkr")}
            >
              {probeBusy === "ibkr" ? "探针中…" : "IBKR/CTP 联调探针"}
            </button>
            <button type="button" className="btn btn-sm btn-soft" onClick={() => void loadAdapters()}>
              刷新
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[var(--quant-muted)] border-b border-[var(--quant-border)]">
                <th className="text-left py-2">适配器</th>
                <th className="text-left py-2">市场</th>
                <th className="text-left py-2">阶段</th>
                <th className="text-right py-2">ready</th>
                <th className="text-right py-2">sim_ready</th>
                <th className="text-right py-2">session</th>
              </tr>
            </thead>
            <tbody>
              {adapters.map((a) => (
                <tr key={a.adapter_id} className="border-b border-[var(--quant-border)]/40">
                  <td className="py-2 font-mono text-xs">{a.adapter_id ?? "—"}</td>
                  <td className="py-2">{a.market ?? "—"}</td>
                  <td className="py-2">{a.phase ?? "—"}</td>
                  <td className={`py-2 text-right ${a.ready ? "text-up" : "text-down"}`}>
                    {a.ready ? "yes" : "no"}
                  </td>
                  <td className={`py-2 text-right ${a.sim_ready ? "text-up" : ""}`}>
                    {a.sim_ready == null ? "—" : a.sim_ready ? "yes" : "no"}
                  </td>
                  <td className="py-2 text-right font-mono text-xs">
                    {a.session_wired == null ? "—" : a.session_wired ? "wired" : "—"}
                  </td>
                </tr>
              ))}
              {!adapters.length ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-[var(--quant-muted)]">
                    暂无适配器数据
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--quant-border)]/40 pt-3">
          <div>
            <div className="text-sm font-bold">RL 研究旁路</div>
            <div className="text-xs text-[var(--quant-muted)]">
              tabular Q · live_enabled={String(rlStatus?.live_enabled ?? false)} · policy=
              {rlStatus?.has_policy ? "yes" : "no"}
            </div>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-soft"
            disabled={probeBusy !== null}
            onClick={() => {
              void (async () => {
                setProbeBusy("rl");
                try {
                  await apiFetchV1("/strategy/rl-research/train", {
                    method: "POST",
                    body: JSON.stringify({ prefer_live_bars: true, episodes: 4 }),
                  });
                  await loadRl();
                } finally {
                  setProbeBusy(null);
                }
              })();
            }}
          >
            {probeBusy === "rl" ? "训练中…" : "RL 离线训练"}
          </button>
        </div>

        {probeReport && (
          <div className="text-xs space-y-1 border-t border-[var(--quant-border)]/40 pt-3">
            <div className={probeReport.ok ? "text-up" : "text-down"}>
              探针 {probeReport.ok ? "通过" : "未通过"} · passed={probeReport.passed ?? 0} · failed=
              {probeReport.failed ?? 0} · mode={probeReport.mode ?? "—"}
            </div>
            <ul className="max-h-40 overflow-y-auto space-y-0.5 font-mono text-[var(--quant-muted)]">
              {(probeReport.checks ?? []).slice(0, 12).map((c, i) => (
                <li key={i}>
                  {c.passed ? "✓" : "✗"} {c.title}
                  {c.detail ? ` — ${c.detail}` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">Trace 查询</div>
          <div className="flex gap-2 mb-3">
            <input
              className="input input-bordered input-sm flex-1"
              placeholder="trace id"
              value={traceId}
              onChange={(e) => setTraceId(e.target.value)}
            />
            <button type="button" className="btn btn-sm btn-primary" onClick={() => void queryTrace()}>
              查询
            </button>
          </div>
          <div className="space-y-1 max-h-64 overflow-y-auto text-xs font-mono text-[var(--quant-muted)]">
            {traceResults.map((t, i) => (
              <div key={i}>
                {t.time} · {t.query || t.raw || t.trace_id}
              </div>
            ))}
            {!traceResults.length ? <div>输入 Trace ID 查询</div> : null}
          </div>
        </div>

        <div className="quant-card">
          <div className="text-sm font-bold mb-3">任务事件</div>
          <div className="space-y-1 max-h-64 overflow-y-auto text-xs">
            {tasks.slice(0, 30).map((t, i) => (
              <div key={i} className="border-b border-[var(--quant-border)]/40 py-1">
                <span className="font-mono text-[var(--quant-muted)]">{t.ts ?? ""}</span>{" "}
                {t.label || t.event || t.task_name || t.detail || "—"}
              </div>
            ))}
            {!tasks.length ? <div className="text-[var(--quant-muted)]">暂无任务事件</div> : null}
          </div>
        </div>
      </div>

      <div className="quant-card">
        <div className="text-sm font-bold mb-3">Celery Beat 时序同步</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[var(--quant-muted)] border-b border-[var(--quant-border)]">
                <th className="text-left py-2">时间</th>
                <th className="text-left py-2">模式</th>
                <th className="text-right py-2">写入行数</th>
                <th className="text-right py-2">状态</th>
              </tr>
            </thead>
            <tbody>
              {beatRuns.map((r, i) => (
                <tr key={i} className="border-b border-[var(--quant-border)]/40">
                  <td className="py-2 font-mono text-xs">{r.recorded_at ?? "—"}</td>
                  <td className="py-2">{r.mode ?? "—"}</td>
                  <td className="py-2 text-right mono">{r.questdb_rows_written ?? "—"}</td>
                  <td className={`py-2 text-right ${r.ok ? "text-up" : "text-down"}`}>
                    {r.ok ? "OK" : "FAIL"}
                  </td>
                </tr>
              ))}
              {!beatRuns.length ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-[var(--quant-muted)]">
                    暂无 Beat 记录
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
