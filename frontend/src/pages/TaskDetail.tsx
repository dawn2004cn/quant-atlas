import { useParams, useNavigate } from "react-router-dom";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

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

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const { data, error, isLoading } = useSWR(
    taskId ? `task-detail-${taskId}` : null,
    () => apiFetchV1<TaskDetailData>(`/task/${encodeURIComponent(taskId ?? "")}`),
    { refreshInterval: taskId ? 10_000 : undefined },
  );

  if (isLoading && !data) return <PageSkeleton rows={5} />;
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">任务未找到</div>;

  const task = data;

  return (
    <div className="space-y-5">
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
        </div>
        <span className={`badge badge-lg ${STATUS_CLASS[task.status] ?? "badge-ghost"}`}>
          {STATUS_LABEL[task.status] ?? task.status}
        </span>
      </div>

      <div className="glass-card p-6 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-500 mb-2">任务进度</h3>
          <div className="flex items-center justify-between text-sm mb-1">
            <span>{task.progress}%</span>
            <span className="text-slate-500">{task.status === "running" ? "执行中..." : STATUS_LABEL[task.status]}</span>
          </div>
          <progress
            className="progress progress-primary w-full h-3"
            value={task.progress}
            max={100}
          />
        </div>

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