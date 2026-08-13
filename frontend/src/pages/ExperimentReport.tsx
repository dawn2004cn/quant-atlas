import { useMemo, useState } from "react";
import useSWR from "swr";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { fetchExperiment, fetchExperiments } from "../lib/api";
import { DEMO_EXPERIMENT_DETAIL, DEMO_EXPERIMENTS } from "../lib/demoCatalog";
import type { ExperimentDetail } from "../types/experiment";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

function metric(value: number | undefined, digits = 2) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function buildEquitySvg(curve: ExperimentDetail["equity_curve"]) {
  if (!curve || curve.length < 2) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg bg-zinc-100 text-sm text-zinc-500 dark:bg-zinc-900">
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
    <svg className="h-48 w-full rounded-lg bg-zinc-50 dark:bg-zinc-900" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
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

  const liveExperiments = listData?.experiments ?? [];
  const listDemo = Boolean(listError) || !liveExperiments.length;
  const experiments = listDemo ? DEMO_EXPERIMENTS : liveExperiments;

  const effectiveId = selectedId || (listDemo ? DEMO_EXPERIMENT_DETAIL.id : "");
  const detailDemo = Boolean(detailError) || (Boolean(effectiveId) && !detail && !detailLoading);
  const viewDetail: ExperimentDetail | null = effectiveId
    ? detailDemo
      ? (DEMO_EXPERIMENT_DETAIL as ExperimentDetail)
      : (detail as ExperimentDetail)
    : null;

  const metrics = viewDetail?.metrics ?? {};
  const icValue = metrics.ic ?? metrics.ic_mean ?? metrics.IC ?? metrics.rank_ic;
  const findings = useMemo(() => viewDetail?.findings ?? [], [viewDetail?.findings]);
  const isDemo = listDemo || (Boolean(effectiveId) && detailDemo);

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <CoreWorkflowStrip />
      <PageQuickNav items={QUICK_NAV_PRESETS.experimentReport} />
      <div>
        <h1 className="text-2xl font-bold">实验报告</h1>
        <p className="text-sm text-zinc-500">投研实验列表与权益曲线 · `/api/v1/experiments`</p>
        <DemoBanner show={isDemo} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200 max-w-xs"
          value={selectedId || (listDemo ? DEMO_EXPERIMENT_DETAIL.id : "")}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {!listDemo ? <option value="">选择实验…</option> : null}
          {experiments.map((exp) => (
            <option key={exp.id} value={exp.id}>
              {exp.name} · {exp.created_at?.slice(0, 10) ?? exp.status}
            </option>
          ))}
        </select>
      </div>

      {listLoading && !listDemo ? <p className="text-zinc-500">加载实验列表…</p> : null}
      {selectedId && detailLoading && !detailDemo ? <p className="text-zinc-500">加载报告…</p> : null}

      {viewDetail ? (
        <Panel className="space-y-6 p-6">
          <div>
            <h2 className="text-xl font-semibold">{viewDetail.name || "投研实验报告"}</h2>
            <p className="text-sm text-zinc-500">
              ID {viewDetail.id.slice(0, 8)}
              {viewDetail.preset_name ? ` · 预设 ${viewDetail.preset_name}` : ""}
              {" · "}
              {viewDetail.created_at?.slice(0, 19) ?? "—"} · {viewDetail.status}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-zinc-50 p-3 text-center dark:bg-zinc-900">
              <div className="text-lg font-bold text-brand">{metric(metrics.total_return, 1)}%</div>
              <div className="text-xs text-zinc-500">总收益</div>
            </div>
            <div className="rounded-lg bg-zinc-50 p-3 text-center dark:bg-zinc-900">
              <div className="text-lg font-bold">{metric(metrics.sharpe_ratio ?? metrics.sharpe)}</div>
              <div className="text-xs text-zinc-500">夏普</div>
            </div>
            <div className="rounded-lg bg-zinc-50 p-3 text-center dark:bg-zinc-900">
              <div className="text-lg font-bold text-violet-600">{metric(icValue as number | undefined, 3)}</div>
              <div className="text-xs text-zinc-500">IC</div>
            </div>
            <div className="rounded-lg bg-zinc-50 p-3 text-center dark:bg-zinc-900">
              <div className="text-lg font-bold text-rose-400">{metric(metrics.max_drawdown, 1)}%</div>
              <div className="text-xs text-zinc-500">最大回撤</div>
            </div>
          </div>

          {viewDetail.description ? (
            <section>
              <h3 className="mb-2 font-semibold">策略描述</h3>
              <p className="text-sm text-zinc-600 dark:text-zinc-300">{viewDetail.description}</p>
            </section>
          ) : null}

          <section>
            <h3 className="mb-2 font-semibold">收益曲线</h3>
            {buildEquitySvg(viewDetail.equity_curve)}
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
        </Panel>
      ) : null}
    </div>
  );
}
