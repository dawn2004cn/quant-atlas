import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

type TaskItem = {
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
};

type TaskListData = {
  tasks: TaskItem[];
  total: number;
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

export function TaskCenterPage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<string>("all");

  const { data, error, isLoading, mutate } = useSWR(
    "task-list",
    () => apiFetchV1<TaskListData>("/task/list"),
    { refreshInterval: 15_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={4} />;
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无任务数据</div>;

  const tasks = (data.tasks ?? []).filter(
    (t) => filter === "all" || t.status === filter,
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">任务中心</h1>
          <p className="text-sm text-slate-500">异步任务管理与状态追踪</p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["all", "pending", "running", "completed", "failed", "cancelled"] as const).map((s) => (
          <button
            key={s}
            type="button"
            className={`btn btn-sm ${filter === s ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setFilter(s)}
          >
            {s === "all" ? "全部" : STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      {tasks.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-lg font-semibold text-slate-500">暂无进行中的任务</p>
          <p className="text-sm text-slate-400 mt-2">
            {filter === "all"
              ? "提交回测、数据同步等操作后，任务将显示在这里"
              : "当前筛选条件下没有任务"}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {tasks.map((task) => (
            <button
              key={task.id}
              type="button"
              className="glass-card text-left p-4 transition hover:shadow-md"
              onClick={() => navigate(`/task/${task.id}`)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold truncate">{task.name}</h4>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">{task.description}</p>
                </div>
                <span className={`badge badge-sm ${STATUS_CLASS[task.status] ?? "badge-ghost"}`}>
                  {STATUS_LABEL[task.status] ?? task.status}
                </span>
              </div>

              {task.status === "running" || task.status === "pending" ? (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                    <span>进度</span>
                    <span>{task.progress}%</span>
                  </div>
                  <progress
                    className="progress progress-primary w-full"
                    value={task.progress}
                    max={100}
                  />
                </div>
              ) : null}

              <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                <span className="badge badge-ghost badge-xs">{task.type}</span>
                <span>更新于 {task.updated_at}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}