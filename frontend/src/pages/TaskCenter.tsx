import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { AsyncProgressBar, PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1, fetchCeleryTaskStatus } from "../lib/api";
import { DEMO_TASKS } from "../lib/demoCatalog";

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

function normalizeId(id: string): string {
  return id.trim().toLowerCase();
}

export function TaskCenterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const focusTaskId = (searchParams.get("task_id") || "").trim();
  const [filter, setFilter] = useState<string>("all");
  const focusRef = useRef<HTMLButtonElement | null>(null);

  const { data, error, isLoading, mutate } = useSWR(
    "task-list",
    () => apiFetchV1<TaskListData>("/task/list"),
    { refreshInterval: 15_000 },
  );

  const { data: celeryFocus } = useSWR(
    focusTaskId ? ["celery-task-focus", focusTaskId] : null,
    () => fetchCeleryTaskStatus(focusTaskId),
    { refreshInterval: 2000, revalidateOnFocus: false },
  );

  const liveTasks = data?.tasks ?? [];
  const isDemo = Boolean(error) || (!isLoading && !liveTasks.length);
  const sourceTasks = isDemo ? DEMO_TASKS : liveTasks;

  const tasks = useMemo(() => {
    return sourceTasks.filter((t) => filter === "all" || t.status === filter);
  }, [sourceTasks, filter]);

  const focusedInList = useMemo(
    () => tasks.find((t) => normalizeId(t.id) === normalizeId(focusTaskId)),
    [tasks, focusTaskId],
  );

  useEffect(() => {
    if (focusRef.current) {
      focusRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusedInList?.id, focusTaskId]);

  if (isLoading && !data) return <PageSkeleton rows={4} showProgress />;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.taskCenter} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">任务中心</h1>
          <p className="text-sm text-slate-500">异步任务管理与状态追踪</p>
          <DemoBanner show={isDemo} />
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      {focusTaskId ? (
        <div className="glass-card border border-sky-500/30 bg-sky-500/5 p-4 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs font-mono uppercase tracking-wide text-sky-500">定位任务</div>
              <div className="font-mono text-sm break-all">{focusTaskId}</div>
            </div>
            {focusedInList ? (
              <button
                type="button"
                className="btn btn-sm btn-primary"
                onClick={() => navigate(`/task/${focusedInList.id}`)}
              >
                打开详情
              </button>
            ) : null}
          </div>
          {celeryFocus ? (
            <div className="text-sm text-slate-600 dark:text-slate-300">
              Celery 状态：
              <span className="font-semibold ml-1">{celeryFocus.state || (celeryFocus.ready ? "READY" : "PENDING")}</span>
              {celeryFocus.successful === true ? " · 成功" : null}
              {celeryFocus.failed === true ? " · 失败" : null}
              {typeof celeryFocus.error === "string" && celeryFocus.error ? (
                <span className="block text-rose-500 mt-1">{celeryFocus.error}</span>
              ) : null}
            </div>
          ) : focusedInList ? (
            <p className="text-sm text-slate-500">已在下方列表高亮该任务。</p>
          ) : (
            <p className="text-sm text-slate-500">列表中暂无匹配项，正在查询 Celery 任务状态…</p>
          )}
        </div>
      ) : null}

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
          {focusTaskId ? (
            <p className="text-xs text-slate-400 mt-3">
              也可从回测页携带{" "}
              <Link className="link" to={`/task-center?task_id=${encodeURIComponent(focusTaskId)}`}>
                task_id
              </Link>{" "}
              定位 Celery 异步任务
            </p>
          ) : null}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {tasks.map((task) => {
            const isFocus = focusTaskId && normalizeId(task.id) === normalizeId(focusTaskId);
            return (
              <button
                key={task.id}
                ref={isFocus ? focusRef : undefined}
                type="button"
                className={`glass-card text-left p-4 transition hover:shadow-md ${
                  isFocus ? "ring-2 ring-sky-500/60 bg-sky-500/5" : ""
                }`}
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
                    <AsyncProgressBar label="进度" value={task.progress} />
                  </div>
                ) : null}

                <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                  <span className="badge badge-ghost badge-xs">{task.type}</span>
                  <span>更新于 {task.updated_at}</span>
                  {isFocus ? <span className="badge badge-info badge-xs">定位</span> : null}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
