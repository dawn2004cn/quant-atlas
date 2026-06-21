import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

type AgentNode = {
  id: string;
  name: string;
  type: string;
  model: string;
  role: string;
  status: "active" | "inactive" | "draft";
  connections: string[];
  config: Record<string, unknown>;
};

type DesignerData = {
  agents: AgentNode[];
  workspace: {
    id: string;
    name: string;
    description: string;
  };
};

export function SwarmDesignerPage() {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  const { data, error, isLoading, mutate } = useSWR(
    "swarm-designer",
    () => apiFetchV1<DesignerData>("/agent-swarm/designer"),
  );

  if (isLoading && !data) return <PageSkeleton rows={4} />;
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无 Designer 数据</div>;

  const agents = data.agents ?? [];
  const workspace = data.workspace;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Swarm Designer</h1>
          <p className="text-sm text-slate-500">
            {workspace ? `${workspace.name} — ${workspace.description}` : "智能体集群流程设计器"}
          </p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">流程画布</h3>
          <div className="flex gap-2">
            <span className="text-xs text-slate-500">共 {agents.length} 个 Agent</span>
          </div>
        </div>

        {agents.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-lg font-semibold text-slate-500">暂无 Agent 节点</div>
            <p className="text-sm text-slate-400 mt-2">通过 API 创建 Agent 后，节点将在此显示</p>
          </div>
        ) : (
          <div className="flex flex-wrap gap-4 justify-center">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className={`border-2 rounded-xl p-4 transition cursor-pointer w-56 ${
                  selectedAgent === agent.id
                    ? "border-brand bg-brand/5"
                    : "border-slate-200 dark:border-slate-700 hover:border-slate-300"
                }`}
                onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h5 className="font-semibold text-sm">{agent.name}</h5>
                  <div
                    className={`w-2.5 h-2.5 rounded-full ${
                      agent.status === "active"
                        ? "bg-emerald-500"
                        : agent.status === "draft"
                          ? "bg-amber-400"
                          : "bg-slate-400"
                    }`}
                  />
                </div>
                <p className="text-xs text-slate-500 mb-2">{agent.role}</p>
                <div className="flex flex-wrap gap-1">
                  <span className="badge badge-ghost badge-xs">{agent.type}</span>
                  <span className="badge badge-ghost badge-xs">{agent.model}</span>
                </div>
                {agent.connections.length > 0 && (
                  <div className="mt-2 pt-2 border-t text-xs text-slate-400">
                    连接：{agent.connections.join(", ")}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedAgent && (
        <div className="glass-card p-6 space-y-3">
          {(() => {
            const agent = agents.find((a) => a.id === selectedAgent);
            if (!agent) return null;
            return (
              <>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold">{agent.name}</h3>
                    <p className="text-xs text-slate-500">{agent.id}</p>
                  </div>
                  <span className={`badge ${agent.status === "active" ? "badge-success" : agent.status === "draft" ? "badge-warning" : "badge-ghost"}`}>
                    {agent.status}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><span className="text-slate-500">类型</span><p className="font-medium">{agent.type}</p></div>
                  <div><span className="text-slate-500">模型</span><p className="font-medium">{agent.model}</p></div>
                  <div><span className="text-slate-500">角色</span><p className="font-medium">{agent.role}</p></div>
                  <div><span className="text-slate-500">连接数</span><p className="font-medium">{agent.connections.length}</p></div>
                </div>
                {agent.connections.length > 0 && (
                  <div>
                    <span className="text-xs text-slate-500">输出连接</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {agent.connections.map((conn) => (
                        <span key={conn} className="badge badge-outline badge-sm">{conn}</span>
                      ))}
                    </div>
                  </div>
                )}
                {Object.keys(agent.config).length > 0 && (
                  <details className="text-sm">
                    <summary className="cursor-pointer text-slate-500">配置详情</summary>
                    <pre className="mt-2 bg-slate-100 dark:bg-slate-800 rounded p-3 text-xs overflow-x-auto">
                      {JSON.stringify(agent.config, null, 2)}
                    </pre>
                  </details>
                )}
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}