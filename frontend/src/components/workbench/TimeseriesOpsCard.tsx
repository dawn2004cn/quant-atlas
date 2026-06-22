import useSWR from "swr";
import {
  fetchTimeseriesHealth,
  fetchTimeseriesSyncHistory,
} from "../../lib/api";
import type { TimeseriesSyncRun } from "../../types/timeseries";

function runLabel(run: TimeseriesSyncRun): string {
  const time = run.recorded_at ? run.recorded_at.slice(0, 19) : "—";
  const mark = run.ok ? "✓" : "✗";
  const rows =
    run.questdb_rows_written != null ? ` +${run.questdb_rows_written}` : "";
  const mode = run.mode ? ` · ${run.mode}` : "";
  return `${time} ${mark}${rows}${mode}`;
}

function Tag({ children, color }: { children: React.ReactNode; color: "emerald" | "sky" | "rose" | "zinc" }) {
  const colorMap = {
    emerald: "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20",
    sky: "bg-sky-500/10 text-sky-400 ring-1 ring-sky-500/20",
    rose: "bg-rose-500/10 text-rose-400 ring-1 ring-rose-500/20",
    zinc: "bg-zinc-800/60 text-zinc-400 ring-1 ring-zinc-700/40",
  };
  return (
    <span className={`rounded-full px-2.5 py-1 font-mono text-[10px] font-semibold ${colorMap[color]}`}>
      {children}
    </span>
  );
}

export function TimeseriesOpsCard() {
  const { data: health, error: healthError, isLoading: healthLoading } = useSWR(
    "timeseries-health",
    fetchTimeseriesHealth,
    { refreshInterval: 60_000 },
  );
  const { data: history } = useSWR(
    "timeseries-sync-history",
    () => fetchTimeseriesSyncHistory(5, "celery_beat"),
    { refreshInterval: 60_000 },
  );

  if (healthLoading && !health) {
    return (
      <div className="rounded-xl bg-zinc-900/30 p-4 ring-1 ring-zinc-800/40">
        <div className="flex items-center gap-3">
          <div className="h-4 w-4 animate-pulse rounded bg-zinc-800/60" />
          <div className="h-4 w-36 animate-pulse rounded bg-zinc-800/40" />
        </div>
      </div>
    );
  }

  if (healthError) {
    return (
      <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
        时序健康探针不可用：{healthError.message}
      </div>
    );
  }

  const beat = health?.celery_beat ?? {};
  const qdb = health?.questdb ?? {};
  const rows = health?.ohlcv_tables?.questdb_rows;
  const qmt = health?.execution?.qmt?.execution_mode ?? "—";
  const runs =
    history?.runs?.length ? history.runs : beat.recent_beat_runs ?? [];

  let beatHeadline = beat.enabled ? beat.schedule_label ?? "16:35" : "Beat 关闭";
  if (beat.sync_in_progress) {
    const pct = beat.sync_progress?.percent ?? 0;
    beatHeadline += ` · 同步中 ${pct}%`;
  } else if (beat.last_beat_run_at) {
    beatHeadline = `${beat.last_beat_run_at.slice(0, 16)} ${beat.last_beat_run_ok ? "✓" : "✗"}`;
  }

  return (
    <div className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-zinc-500">
            时序基础设施
          </p>
          <h3 className="mt-0.5 text-base font-bold text-zinc-200">Beat · QuestDB</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag color={beat.enabled ? "emerald" : "zinc"}>{beatHeadline}</Tag>
          {qdb.enabled && (
            <Tag color={qdb.connected ? "sky" : "rose"}>
              QuestDB {qdb.connected ? "在线" : "离线"}
              {rows != null ? ` · ${rows.toLocaleString()} 行` : ""}
            </Tag>
          )}
          <Tag color="zinc">QMT {qmt}</Tag>
        </div>
      </div>

      {runs.length ? (
        <div className="mt-4 space-y-1 border-t border-zinc-800/40 pt-3">
          <p className="text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-600">
            最近的 Beat 同步记录
          </p>
          {runs.map((run, idx) => (
            <div key={`${run.recorded_at ?? idx}`} className="font-mono text-xs text-zinc-500">
              {runLabel(run)}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-zinc-600">尚无 celery_beat 同步记录</p>
      )}

      {(health?.warnings?.length ?? 0) > 0 ? (
        <p className="mt-3 text-xs text-amber-400/70">
          提示：{health?.warnings?.join(" · ")}
        </p>
      ) : null}
    </div>
  );
}