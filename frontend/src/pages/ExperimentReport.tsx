import { useMemo, useState } from "react";
import useSWR from "swr";
import { fetchExperiment, fetchExperiments } from "../lib/api";
import type { ExperimentDetail } from "../types/experiment";

function metric(value: number | undefined, digits = 2) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function buildEquitySvg(curve: ExperimentDetail["equity_curve"]) {
  if (!curve || curve.length < 2) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg bg-slate-100 text-sm text-slate-500 dark:bg-slate-900">
        暂无权益曲线数据
      </div>
    );
  }
  const vals = curve.map((p) => Number(p.value ?? p.equity ?? 0));
  const w = 640;
  const h = 180;
  const pad = 8;
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;
  const pts = vals
    .map((v, i) => {
      const x = pad + (i / (vals.length - 1)) * (w - pad * 2);
      const y = h - pad - ((v - min) / span) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg className="h-48 w-full rounded-lg bg-slate-50 dark:bg-slate-900" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline fill="none" stroke="#7c3aed" strokeWidth="2" points={pts} />
    </svg>
  );
}

export function ExperimentReportPage() {
  const [selectedId, setSelectedId] = useState("");
  const { data: listData, error: listError, isLoading: listLoading } = useSWR(
    "experiments-list",
    fetchExperiments,
  );
  const { data: detail, error: detailError, isLoading: detailLoading } = useSWR(
    selectedId ? `experiment-${selectedId}` : null,
    () => fetchExperiment(selectedId),
  );

  const experiments = listData?.experiments ?? [];
  const metrics = detail?.metrics ?? {};
  const icValue = metrics.ic ?? metrics.ic_mean ?? metrics.IC ?? metrics.rank_ic;

  const findings = useMemo(() => detail?.findings ?? [], [detail?.findings]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">实验报告</h1>
        <p className="text-sm text-slate-500">投研实验列表与权益曲线 · `/api/v1/experiments`</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          className="select select-bordered select-sm max-w-xs"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          <option value="">选择实验…</option>
          {experiments.map((exp) => (
            <option key={exp.id} value={exp.id}>
              {exp.name} · {exp.created_at?.slice(0, 10) ?? exp.status}
            </option>
          ))}
        </select>
        <a className="link text-sm" href="/experiment-reporter">
          经典版报告页
        </a>
      </div>

      {listLoading ? <p className="text-slate-500">加载实验列表…</p> : null}
      {listError ? (
        <p className="text-error">列表加载失败：{listError instanceof Error ? listError.message : "unknown"}</p>
      ) : null}

      {selectedId && detailLoading ? <p className="text-slate-500">加载报告…</p> : null}
      {detailError ? (
        <p className="text-error">报告加载失败：{detailError instanceof Error ? detailError.message : "unknown"}</p>
      ) : null}

      {detail ? (
        <div className="glass-card space-y-6 p-6">
          <div>
            <h2 className="text-xl font-semibold">{detail.name || "投研实验报告"}</h2>
            <p className="text-sm text-slate-500">
              ID {detail.id.slice(0, 8)}
              {detail.preset_name ? ` · 预设 ${detail.preset_name}` : ""}
              {" · "}
              {detail.created_at?.slice(0, 19) ?? "—"} · {detail.status}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-900">
              <div className="text-lg font-bold text-brand">{metric(metrics.total_return, 1)}%</div>
              <div className="text-xs text-slate-500">总收益</div>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-900">
              <div className="text-lg font-bold">{metric(metrics.sharpe_ratio ?? metrics.sharpe)}</div>
              <div className="text-xs text-slate-500">夏普</div>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-900">
              <div className="text-lg font-bold text-violet-600">{metric(icValue as number | undefined, 3)}</div>
              <div className="text-xs text-slate-500">IC</div>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-900">
              <div className="text-lg font-bold text-rose-600">{metric(metrics.max_drawdown, 1)}%</div>
              <div className="text-xs text-slate-500">最大回撤</div>
            </div>
          </div>

          {detail.description ? (
            <section>
              <h3 className="mb-2 font-semibold">策略描述</h3>
              <p className="text-sm text-slate-600 dark:text-slate-300">{detail.description}</p>
            </section>
          ) : null}

          <section>
            <h3 className="mb-2 font-semibold">收益曲线</h3>
            {buildEquitySvg(detail.equity_curve)}
          </section>

          {findings.length > 0 ? (
            <section>
              <h3 className="mb-2 font-semibold">研究发现</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {findings.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
