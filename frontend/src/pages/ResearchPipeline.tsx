import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

type PipelineStage = {
  id: string;
  name: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  progress: number;
  started_at?: string;
  completed_at?: string;
  output?: string;
  error?: string;
};

type PipelineData = {
  pipeline_id: string;
  name: string;
  description: string;
  status: "idle" | "running" | "completed" | "failed";
  stages: PipelineStage[];
  started_at?: string;
  updated_at: string;
};

const STAGE_STATUS_ICON: Record<string, string> = {
  pending: "○",
  running: "◉",
  completed: "●",
  failed: "✕",
  skipped: "—",
};

const STAGE_STATUS_CLASS: Record<string, string> = {
  pending: "text-slate-400",
  running: "text-brand animate-pulse",
  completed: "text-emerald-500",
  failed: "text-rose-500",
  skipped: "text-slate-300",
};

const PIPELINE_STATUS_CLASS: Record<string, string> = {
  idle: "badge-ghost",
  running: "badge-info",
  completed: "badge-success",
  failed: "badge-error",
};

const PIPELINE_STATUS_LABEL: Record<string, string> = {
  idle: "待启动",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

export function ResearchPipelinePage() {
  const { data, error, isLoading, mutate } = useSWR(
    "research-pipeline",
    () => apiFetchV1<PipelineData>("/research/pipeline"),
    { refreshInterval: 15_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={5} />;
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无研究管线数据</div>;

  const stages = data.stages ?? [];
  const completedStages = stages.filter((s) => s.status === "completed").length;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.researchPipeline} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">研究管线</h1>
          <p className="text-sm text-slate-500">
            {data.name} — {data.description}
          </p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      <div className="flex items-center gap-4 flex-wrap">
        <span className={`badge ${PIPELINE_STATUS_CLASS[data.status] ?? "badge-ghost"}`}>
          {PIPELINE_STATUS_LABEL[data.status] ?? data.status}
        </span>
        <span className="text-sm text-slate-500">
          阶段进度：{completedStages}/{stages.length}
        </span>
        {data.started_at && (
          <span className="text-xs text-slate-400">开始于 {data.started_at}</span>
        )}
        <span className="text-xs text-slate-400">更新于 {data.updated_at}</span>
      </div>

      {stages.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-lg font-semibold text-slate-500">暂无管线阶段</p>
          <p className="text-sm text-slate-400 mt-2">启动研究流程后，管线阶段将在此展示</p>
        </div>
      ) : (
        <div className="space-y-3">
          {stages.map((stage, index) => (
            <div
              key={stage.id}
              className={`glass-card p-4 transition ${
                stage.status === "running" ? "ring-2 ring-brand/30" : ""
              }`}
            >
              <div className="flex items-start gap-4">
                <div className="flex flex-col items-center pt-1">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 ${
                      STAGE_STATUS_CLASS[stage.status] ?? "text-slate-400"
                    } ${
                      stage.status === "completed"
                        ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30"
                        : stage.status === "failed"
                          ? "border-rose-500 bg-rose-50 dark:bg-rose-950/30"
                          : "border-slate-300 dark:border-slate-600"
                    }`}
                  >
                    {STAGE_STATUS_ICON[stage.status] ?? "○"}
                  </div>
                  {index < stages.length - 1 && (
                    <div className="w-0.5 h-8 bg-slate-300 dark:bg-slate-600" />
                  )}
                </div>

                <div className="flex-1 min-w-0 pb-4">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="font-semibold">{stage.name}</h4>
                    <span className={`badge badge-sm ${STAGE_STATUS_CLASS[stage.status]?.replace("text-", "badge-") ?? "badge-ghost"}`}>
                      {stage.status === "running"
                        ? `${stage.progress}%`
                        : stage.status === "completed"
                          ? "完成"
                          : stage.status === "failed"
                            ? "失败"
                            : stage.status === "skipped"
                              ? "跳过"
                              : "待处理"}
                    </span>
                  </div>

                  <p className="text-sm text-slate-500 mt-1">{stage.description}</p>

                  {(stage.status === "running" || stage.status === "pending") && (
                    <div className="mt-2">
                      <progress
                        className="progress progress-primary w-full"
                        value={stage.progress}
                        max={100}
                      />
                    </div>
                  )}

                  {stage.output && (
                    <div className="mt-2 bg-slate-100 dark:bg-slate-800 rounded p-2 text-xs font-mono overflow-x-auto">
                      {stage.output}
                    </div>
                  )}

                  {stage.error && (
                    <div className="mt-2 text-xs text-rose-600 bg-rose-50 dark:bg-rose-950/30 rounded p-2">
                      {stage.error}
                    </div>
                  )}

                  <div className="mt-1 flex gap-3 text-xs text-slate-400">
                    {stage.started_at && <span>开始：{stage.started_at}</span>}
                    {stage.completed_at && <span>完成：{stage.completed_at}</span>}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}