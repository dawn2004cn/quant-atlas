import { Link, useNavigate, useParams } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { AsyncProgressBar, PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1, fetchCeleryTaskStatus } from "../lib/api";

type TaskDetailData = {
  id: string;
  name: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  created_at: string;
  updated_at: string;
  type: string;
  result?: Record<string, unknown>;
  error?: string;
  logs?: string[];
  source?: "registry" | "celery";
};

const STATUS_LABEL: Record<string, string> = {
  pending: "待处理",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

const STATUS_CLASS: Record<string, string> = {
  pending: "badge-ghost",
  running: "badge-info",
  completed: "badge-success",
  failed: "badge-error",
  cancelled: "badge-ghost",
};

function mapCeleryToTask(taskId: string, celery: Awaited<ReturnType<typeof fetchCeleryTaskStatus>>): TaskDetailData {
  const state = String(celery.state || (celery.ready ? "READY" : "PENDING")).toUpperCase();
  let status: TaskDetailData["status"] = "pending";
  if (celery.successful || state === "SUCCESS") status = "completed";
  else if (celery.failed || state === "FAILURE" || state === "REVOKED") status = "failed";
  else if (state === "STARTED" || state === "RETRY" || state === "RECEIVED" || state === "PROGRESS") {
    status = "running";
  } else if (celery.ready) {
    status = celery.successful ? "completed" : "failed";
  }

  let progress = 15;
  if (status === "running") progress = 55;
  if (status === "completed" || status === "failed" || status === "cancelled") progress = 100;

  const result =
    celery.result && typeof celery.result === "object"
      ? (celery.result as Record<string, unknown>)
      : undefined;
  const error =
    typeof celery.error === "string"
      ? celery.error
      : typeof celery.result === "string" && status === "failed"
        ? celery.result
        : undefined;

  return {
    id: taskId,
    name: "Celery 异步任务",
    description: `来自 Celery · state=${state}`,
    status,
    progress,
    created_at: "—",
    updated_at: new Date().toLocaleString("zh-CN"),
    type: "celery",
    result,
    error,
    source: "celery",
  };
}

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const {
    data: registryData,
    error: registryError,
    isLoading: registryLoading,
  } = useSWR(
    taskId ? `task-detail-${taskId}` : null,
    () => apiFetchV1<TaskDetailData>(`/task/${encodeURIComponent(taskId ?? "")}`),
    {
      refreshInterval: (latest) =>
        latest && (latest.status === "running" || latest.status === "pending") ? 10_000 : 0,
      shouldRetryOnError: false,
    },
  );

  const needCelery = Boolean(taskId) && !registryLoading && !registryData;

  const {
    data: celeryRaw,
    error: celeryError,
    isLoading: celeryLoading,
  } = useSWR(
    needCelery && taskId ? `celery-task-detail-${taskId}` : null,
    () => fetchCeleryTaskStatus(taskId ?? ""),
    {
      refreshInterval: (latest) => (latest && !latest.ready ? 5_000 : 0),
      shouldRetryOnError: false,
    },
  );

  const celeryTask =
    needCelery && celeryRaw && taskId ? mapCeleryToTask(taskId, celeryRaw) : null;
  const data = registryData ?? celeryTask ?? null;

  if ((registryLoading && !registryData) || (needCelery && celeryLoading && !celeryTask)) {
    return <PageSkeleton rows={5} showProgress />;
  }

  if (!data) {
    const msg =
      (celeryError instanceof Error && celeryError.message) ||
      (registryError instanceof Error && registryError.message) ||
      "任务未找到";
    return (
      <div className="space-y-4">
        <button type="button" className="link link-primary text-sm" onClick={() => navigate(-1)}>
          &larr; 返回
        </button>
        <div className="alert alert-warning">{msg}</div>
        {taskId ? (
          <p className="text-xs text-slate-500 font-mono">task_id: {taskId}</p>
        ) : null}
      </div>
    );
  }

  const task = data;
  const indeterminate = task.status === "running" || task.status === "pending";

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.taskDetail} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <button
            type="button"
            className="link link-primary text-sm mb-1 inline-flex items-center gap-1"
            onClick={() => navigate(-1)}
          >
            &larr; 返回任务中心
          </button>
          <h1 className="text-2xl font-bold">{task.name}</h1>
          <p className="text-sm text-slate-500">{task.description || "无描述"}</p>
          {task.source === "celery" ? (
            <p className="mt-1 text-xs text-sky-500/80">
              注册表无此任务，已回退 Celery 状态 ·{" "}
              <Link className="link" to={`/task-center?task_id=${encodeURIComponent(task.id)}`}>
                任务中心定位
              </Link>
            </p>
          ) : null}
        </div>
        <span className={`badge badge-lg ${STATUS_CLASS[task.status] ?? "badge-ghost"}`}>
          {STATUS_LABEL[task.status] ?? task.status}
        </span>
      </div>

      <div className="glass-card p-6 space-y-4">
        <AsyncProgressBar
          label={task.status === "running" ? "执行中…" : STATUS_LABEL[task.status] ?? task.status}
          value={task.progress}
          indeterminate={indeterminate && task.progress < 100}
        />

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-500">任务类型</span>
            <p className="font-medium">{task.type}</p>
          </div>
          <div>
            <span className="text-slate-500">创建时间</span>
            <p className="font-medium">{task.created_at}</p>
          </div>
          <div>
            <span className="text-slate-500">最后更新</span>
            <p className="font-medium">{task.updated_at}</p>
          </div>
          <div>
            <span className="text-slate-500">任务 ID</span>
            <p className="font-mono text-xs">{task.id}</p>
          </div>
        </div>
      </div>

      {task.result && Object.keys(task.result).length > 0 && (
        <div className="glass-card p-6 space-y-3">
          <h3 className="font-semibold">执行结果</h3>
          <div className="overflow-x-auto">
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>指标</th>
                  <th>值</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(task.result).map(([key, value]) => (
                  <tr key={key}>
                    <td className="font-medium">{key}</td>
                    <td className="font-mono text-xs">
                      {typeof value === "object" ? JSON.stringify(value) : String(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {task.error && (
        <div className="alert alert-error">
          <span className="font-bold">错误信息：</span> {task.error}
        </div>
      )}

      {task.logs && task.logs.length > 0 && (
        <div className="glass-card p-6 space-y-2">
          <h3 className="font-semibold">执行日志</h3>
          <div className="bg-slate-900 text-green-400 rounded-lg p-4 text-xs font-mono max-h-60 overflow-y-auto space-y-1">
            {task.logs.map((line, idx) => (
              <div key={idx}>{line}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
