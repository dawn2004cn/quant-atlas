import { useState, useEffect, useCallback } from "react";
import { apiFetchV1 } from "../lib/api";

type LakeHealth = {
  engine?: string;
  status?: string;
  migration?: { status?: string };
  metrics?: { p95_latency_ms?: number };
  store?: { type?: string; status?: string };
};

type TimeseriesHealth = {
  questdb?: { enabled?: boolean; connected?: boolean };
  ohlcv_tables?: { questdb_rows?: number };
  last_sync?: {
    recorded_at?: string;
    ok?: boolean;
    source?: string;
    mode?: string;
    questdb_rows_written?: number;
  };
  sync_progress?: {
    status?: string;
    percent?: number;
    symbols_done?: number;
    symbols_total?: number;
  };
  celery_beat?: {
    enabled?: boolean;
    schedule_label?: string;
    sync_in_progress?: boolean;
    last_beat_run_at?: string;
    last_beat_run_ok?: boolean;
    recent_beat_runs?: Array<{ source?: string; ok?: boolean; recorded_at?: string }>;
  };
  execution?: { qmt?: { execution_mode?: string } };
  warnings?: string[];
  backfill?: {
    target_rows?: number;
    coverage_pct?: number;
    meets_target?: boolean;
    questdb_rows?: number;
  };
};

type RealtimeStatus = {
  socketio_enabled?: boolean;
  origins_configured?: boolean;
  quote_broadcast?: boolean;
  tick_stream?: boolean;
  rooms?: { market?: number; alerts?: number };
  tick?: { status?: string };
};

function StatusDot({ ok }: { ok?: boolean }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${ok ? "bg-[var(--quant-accent)]" : "bg-[var(--quant-danger)]"}`} />
  );
}

function Cell({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="text-center">
      <div className="text-xs text-[var(--quant-muted)] mb-1">{label}</div>
      <div className="flex items-center justify-center gap-1.5">
        {ok != null && <StatusDot ok={ok} />}
        <span className="mono text-sm font-bold">{value}</span>
      </div>
    </div>
  );
}

function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="w-full h-2 rounded-full bg-[var(--quant-surface)] overflow-hidden mt-2">
      <div
        className="h-full rounded-full bg-[var(--quant-accent)] transition-all duration-500"
        style={{ width: `${Math.min(100, percent)}%` }}
      />
    </div>
  );
}

export default function DataLakeHealth() {
  const [lake, setLake] = useState<LakeHealth | null>(null);
  const [ts, setTs] = useState<TimeseriesHealth | null>(null);
  const [rt, setRt] = useState<RealtimeStatus | null>(null);
  const [migrating, setMigrating] = useState(false);
  const [migrateLog, setMigrateLog] = useState<string[]>([]);

  const load = useCallback(async () => {
    try {
      const [l, t, r] = await Promise.all([
        apiFetchV1<LakeHealth>("/data-lake/health"),
        apiFetchV1<TimeseriesHealth>("/data/timeseries-health"),
        apiFetchV1<RealtimeStatus>("/realtime/status"),
      ]);
      setLake(l);
      setTs(t);
      setRt(r);
    } catch {
      // keep previous state
    }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, [load]);

  async function handleMigrate() {
    setMigrating(true);
    setMigrateLog(["开始迁移..."]);
    try {
      const result = await apiFetchV1<{ files_scanned?: number; rows_migrated?: number; details?: unknown[] }>(
        "/data-lake/migrate",
        { method: "POST" }
      );
      setMigrateLog((prev) => [
        ...prev,
        `扫描文件: ${result.files_scanned ?? 0}`,
        `迁移行数: ${result.rows_migrated ?? 0}`,
        "迁移完成",
      ]);
      load();
    } catch (e) {
      setMigrateLog((prev) => [...prev, `迁移失败: ${e instanceof Error ? e.message : String(e)}`]);
    } finally {
      setMigrating(false);
    }
  }

  const questRows = ts?.ohlcv_tables?.questdb_rows;
  const backfill = ts?.backfill;
  const syncProg = ts?.sync_progress;
  const beat = ts?.celery_beat;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">数据湖健康</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">统一数据湖、QuestDB、WebSocket、迁移状态监控</p>
      </div>

      {/* Warnings */}
      {ts?.warnings && ts.warnings.length > 0 && (
        <div className="quant-card border-[var(--quant-warn)]/30 bg-[var(--quant-warn)]/5">
          <div className="flex items-center gap-2 text-[var(--quant-warn)] text-sm font-bold mb-1">⚠ 警告</div>
          {ts.warnings.map((w, i) => (
            <div key={i} className="text-xs text-[var(--quant-muted)]">{w}</div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* SQLite Data Lake */}
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">SQLite 数据湖</div>
          <div className="grid grid-cols-2 gap-4">
            <Cell label="存储引擎" value={lake?.engine ?? lake?.store?.type ?? "—"} />
            <Cell label="健康状态" value={lake?.status ?? lake?.store?.status ?? "—"} ok={lake?.status === "healthy" || lake?.store?.status === "healthy"} />
            <Cell label="迁移状态" value={lake?.migration?.status ?? "—"} />
            <Cell label="P95 延迟" value={lake?.metrics?.p95_latency_ms != null ? `${(lake.metrics.p95_latency_ms / 1000).toFixed(2)}s` : "—"} />
          </div>
        </div>

        {/* QuestDB / Timeseries */}
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">QuestDB 时序同步</div>
          <div className="grid grid-cols-2 gap-4">
            <Cell label="QuestDB" value={ts?.questdb?.enabled ? (ts.questdb.connected ? "在线" : "离线") : "禁用"} ok={ts?.questdb?.connected} />
            <Cell label="OHLCV 行数" value={questRows != null ? questRows.toLocaleString() : "—"} />
            <Cell
              label="最近同步"
              value={ts?.last_sync?.recorded_at ? new Date(ts.last_sync.recorded_at).toLocaleString() : "—"}
              ok={ts?.last_sync?.ok}
            />
            <Cell label="QMT 模式" value={ts?.execution?.qmt?.execution_mode ?? "—"} />
          </div>
          {syncProg?.status === "running" && (
            <div className="mt-3">
              <div className="flex justify-between text-xs text-[var(--quant-muted)]">
                <span>同步进度</span>
                <span>{syncProg.symbols_done}/{syncProg.symbols_total}</span>
              </div>
              <ProgressBar percent={syncProg.percent ?? 0} />
            </div>
          )}
          {backfill && backfill.target_rows != null && (
            <div className="mt-3">
              <div className="flex justify-between text-xs text-[var(--quant-muted)]">
                <span>回填进度</span>
                <span>{backfill.coverage_pct?.toFixed(1) ?? 0}%</span>
              </div>
              <ProgressBar percent={backfill.coverage_pct ?? 0} />
              <div className="text-[10px] text-[var(--quant-muted)] mt-1">
                目标: {backfill.target_rows.toLocaleString()} 行 | 当前: {(backfill.questdb_rows ?? 0).toLocaleString()}
              </div>
            </div>
          )}
          {beat?.enabled && (
            <div className="mt-3 text-xs text-[var(--quant-muted)] space-y-0.5">
              <div>Celery Beat: {beat.schedule_label ?? "—"}</div>
              <div>上次执行: {beat.last_beat_run_at ? new Date(beat.last_beat_run_at).toLocaleString() : "—"}</div>
            </div>
          )}
        </div>

        {/* Realtime / WebSocket */}
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">实时推送 (WebSocket)</div>
          <div className="grid grid-cols-2 gap-4">
            <Cell label="SocketIO" value={rt?.socketio_enabled ? "启用" : "禁用"} ok={rt?.socketio_enabled} />
            <Cell label="行情广播" value={rt?.quote_broadcast ? "启用" : "禁用"} ok={rt?.quote_broadcast} />
            <Cell label="行情房间" value={rt?.rooms?.market != null ? `${rt.rooms.market} 客户端` : "—"} />
            <Cell label="告警房间" value={rt?.rooms?.alerts != null ? `${rt.rooms.alerts} 客户端` : "—"} />
            <Cell label="Tick 流" value={rt?.tick_stream ? "启用" : "禁用"} ok={rt?.tick_stream} />
          </div>
        </div>
      </div>

      {/* Migration Panel */}
      <div className="quant-card">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-bold">历史数据迁移</div>
          <button
            type="button"
            className="btn-brand !text-xs !px-3 !py-1.5"
            onClick={handleMigrate}
            disabled={migrating}
          >
            {migrating ? "迁移中..." : "开始全量迁移"}
          </button>
        </div>
        {migrateLog.length > 0 && (
          <div className="bg-[var(--quant-surface)] rounded-lg p-3 font-mono text-xs text-[var(--quant-muted)] max-h-40 overflow-y-auto space-y-0.5">
            {migrateLog.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
