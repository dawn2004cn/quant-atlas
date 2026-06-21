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
      <section className="glass-card p-4 text-sm text-slate-500">
        正在加载时序基础设施…
      </section>
    );
  }

  if (healthError) {
    return (
      <section className="glass-card border border-amber-200 bg-amber-50 p-4 text-sm dark:border-amber-900 dark:bg-amber-950/30">
        时序健康探针不可用：{healthError.message}
      </section>
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
    <section className="glass-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
            时序基础设施
          </p>
          <h3 className="text-lg font-bold">Beat · QuestDB</h3>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span
            className={`rounded-full px-2.5 py-1 font-semibold ${
              beat.enabled ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-600"
            }`}
          >
            {beatHeadline}
          </span>
          {qdb.enabled ? (
            <span
              className={`rounded-full px-2.5 py-1 font-semibold ${
                qdb.connected
                  ? "bg-sky-100 text-sky-800"
                  : "bg-rose-100 text-rose-800"
              }`}
            >
              QuestDB {qdb.connected ? "在线" : "离线"}
              {rows != null ? ` · ${rows.toLocaleString()} 行` : ""}
            </span>
          ) : null}
          <span className="rounded-full bg-slate-100 px-2.5 py-1 font-semibold text-slate-700">
            QMT {qmt}
          </span>
        </div>
      </div>
      {runs.length ? (
        <ul className="mt-4 space-y-1 border-t border-slate-200/80 pt-3 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          {runs.map((run, idx) => (
            <li key={`${run.recorded_at ?? idx}`} className="font-mono text-xs">
              {runLabel(run)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-500">尚无 celery_beat 同步记录</p>
      )}
      {(health?.warnings?.length ?? 0) > 0 ? (
        <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">
          提示：{health?.warnings?.join(" · ")}
        </p>
      ) : null}
    </section>
  );
}
