import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_COMMITTEE_DASHBOARD } from "../lib/demoCatalog";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

type CommitteeMember = {
  name: string;
  role: string;
  score: number;
  accuracy: number;
  total_votes: number;
  avatar_url?: string;
};

type CommitteeDashboard = {
  consensus_meter: number;
  total_members: number;
  active_proposals: number;
  members: CommitteeMember[];
  updated_at: string;
};

export function AICommitteeDashboardPage() {
  const { data, error, isLoading } = useSWR(
    "ai-committee-dashboard",
    () => apiFetchV1<CommitteeDashboard>("/ai-committee/dashboard"),
    { refreshInterval: 60_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={4} />;

  const isDemo = Boolean(error) || !data || !(data.members ?? []).length;
  const view = isDemo ? DEMO_COMMITTEE_DASHBOARD : data;

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.aiCommitteeDashboard} />
      <div>
        <h1 className="text-2xl font-bold">AI 委员会仪表盘</h1>
        <p className="text-sm text-zinc-500">AI 投资委员会成员表现与共识概览</p>
        <DemoBanner show={isDemo} />
        {view.updated_at && (
          <p className="mt-1 text-xs text-zinc-400">
            更新于：{view.updated_at === "演示" ? "演示" : new Date(view.updated_at).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <Panel className="p-4 text-center">
          <div className="text-2xl font-bold">{view.total_members}</div>
          <div className="text-xs text-zinc-500">成员总数</div>
        </Panel>
        <Panel className="p-4 text-center">
          <div className="text-2xl font-bold">{view.active_proposals}</div>
          <div className="text-xs text-zinc-500">活跃提案</div>
        </Panel>
        <Panel className="p-4 text-center">
          <div className="text-2xl font-bold">{(view.consensus_meter * 100).toFixed(0)}%</div>
          <div className="text-xs text-zinc-500">共识度</div>
        </Panel>
      </div>

      {/* Consensus meter */}
      <Panel className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-bold text-zinc-500">共识度</span>
          <span className="text-sm font-bold">{(view.consensus_meter * 100).toFixed(0)}%</span>
        </div>
        <progress
          className="progress progress-primary w-full"
          value={view.consensus_meter}
          max={1}
        />
      </Panel>

      {/* Members */}
      <Panel className="p-4">
        <h2 className="mb-3 text-sm font-bold text-zinc-500">委员会成员</h2>
        {view.members.length === 0 ? (
          <p className="text-sm text-zinc-400">暂无成员数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th>成员</th>
                  <th>角色</th>
                  <th className="text-right">评分</th>
                  <th className="text-right">准确率</th>
                  <th className="text-right">投票数</th>
                </tr>
              </thead>
              <tbody>
                {view.members.map((member) => (
                  <tr key={member.name}>
                    <td className="font-medium">{member.name}</td>
                    <td className="text-zinc-500">{member.role}</td>
                    <td className="text-right">{member.score.toFixed(1)}</td>
                    <td className="text-right">{(member.accuracy * 100).toFixed(1)}%</td>
                    <td className="text-right">{member.total_votes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
