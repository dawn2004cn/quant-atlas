import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_SWARM_DASHBOARD } from "../lib/demoCatalog";

type AgentMetric = {
  agent_name: string;
  status: "idle" | "running" | "error" | "stopped";
  tasks_completed: number;
  tasks_failed: number;
  avg_response_time_ms: number;
  last_active: string;
  memory_usage_mb: number;
  model: string;
};

type SwarmDashboardData = {
  overall_status: string;
  active_agents: number;
  total_agents: number;
  tasks_processed: number;
  uptime_hours: number;
  agents: AgentMetric[];
};

const STATUS_CLASS: Record<string, string> = {
  idle: "badge-ghost",
  running: "badge-success",
  error: "badge-error",
  stopped: "badge-warning",
};

const STATUS_LABEL: Record<string, string> = {
  idle: "空闲",
  running: "运行中",
  error: "异常",
  stopped: "已停止",
};

export function SwarmDashboardPage() {
  const { data, error, isLoading, mutate } = useSWR(
    "swarm-dashboard",
    () => apiFetchV1<SwarmDashboardData>("/agent-swarm/dashboard"),
    { refreshInterval: 30_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={5} />;

  const isDemo = Boolean(error) || !data || !(data.agents ?? []).length;
  const view = isDemo ? DEMO_SWARM_DASHBOARD : data;
  const agents = view.agents ?? [];

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.swarmDashboard} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Swarm 仪表盘</h1>
          <p className="text-sm text-slate-500">多智能体集群状态监控</p>
          <DemoBanner show={isDemo} />
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="glass-card p-4">
          <div className="text-2xl font-bold text-brand">{view.active_agents}/{view.total_agents}</div>
          <div className="text-xs text-slate-500">活跃 Agent</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{view.tasks_processed}</div>
          <div className="text-xs text-slate-500">处理任务数</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{view.uptime_hours.toFixed(1)}h</div>
          <div className="text-xs text-slate-500">运行时长</div>
        </div>
        <div className="glass-card p-4">
          <div className={`text-2xl font-bold ${view.overall_status === "healthy" ? "text-emerald-600" : "text-amber-600"}`}>
            {view.overall_status === "healthy" ? "健康" : view.overall_status}
          </div>
          <div className="text-xs text-slate-500">整体状态</div>
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-lg font-semibold text-slate-500">暂无 Agent 数据</p>
          <p className="text-sm text-slate-400 mt-2">启动 Agent Swarm 服务后，Agent 信息将显示在这里</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {agents.map((agent) => (
            <div key={agent.agent_name} className="glass-card p-4 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h4 className="font-semibold">{agent.agent_name}</h4>
                  <p className="text-xs text-slate-500">{agent.model}</p>
                </div>
                <span className={`badge badge-sm ${STATUS_CLASS[agent.status] ?? "badge-ghost"}`}>
                  {STATUS_LABEL[agent.status] ?? agent.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-xs text-slate-500">完成任务</span>
                  <p className="font-medium text-emerald-600">{agent.tasks_completed}</p>
                </div>
                <div>
                  <span className="text-xs text-slate-500">失败任务</span>
                  <p className="font-medium text-rose-600">{agent.tasks_failed}</p>
                </div>
                <div>
                  <span className="text-xs text-slate-500">平均响应</span>
                  <p className="font-medium">{(agent.avg_response_time_ms / 1000).toFixed(1)}s</p>
                </div>
                <div>
                  <span className="text-xs text-slate-500">内存</span>
                  <p className="font-medium">{agent.memory_usage_mb}MB</p>
                </div>
              </div>

              <p className="text-xs text-slate-400">最后活跃：{agent.last_active}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}