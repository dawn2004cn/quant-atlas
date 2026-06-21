import { Link } from "react-router-dom";

const LABELS: Record<string, string> = {
  feature_alpha_marketplace: "Alpha 因子市场 / ZK 治理",
  feature_war_room: "War Room / Hyper 模拟器",
  feature_decision_theater: "决策剧场 (3D / 回溯)",
  feature_swarm_topology: "Swarm 拓扑设计器",
  feature_federated_mesh: "联邦 Mesh / 集群",
};

const ENV_HINTS: Record<string, string> = {
  feature_alpha_marketplace: "FEATURE_ALPHA_MARKETPLACE=1",
  feature_war_room: "FEATURE_WAR_ROOM=1",
  feature_decision_theater: "FEATURE_DECISION_THEATER=1",
  feature_swarm_topology: "FEATURE_SWARM_TOPOLOGY=1",
  feature_federated_mesh: "FEATURE_FEDERATED_MESH=1",
};

type Props = {
  feature: keyof typeof LABELS;
};

export function FeatureRetired({ feature }: Props) {
  const label = LABELS[feature] ?? feature;
  const envHint = ENV_HINTS[feature] ?? "FEATURE_*=1";

  return (
    <div className="glass-card mx-auto max-w-lg p-8 text-center">
      <h1 className="text-2xl font-bold">能力已下线</h1>
      <p className="mt-3 text-sm text-slate-500">
        「{label}」已在 P3 战略削减中默认关闭。开发环境可设置{" "}
        <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">
          {envHint}
        </code>{" "}
        后重启服务以恢复。
      </p>
      <div className="mt-6">
        <Link to="/" className="btn btn-primary btn-sm">
          返回操盘台
        </Link>
      </div>
    </div>
  );
}
