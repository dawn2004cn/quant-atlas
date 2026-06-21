import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

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
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无委员会数据</div>;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">AI 委员会仪表盘</h1>
        <p className="text-sm text-slate-500">AI 投资委员会成员表现与共识概览</p>
        {data.updated_at && (
          <p className="mt-1 text-xs text-slate-400">
            更新于：{new Date(data.updated_at).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="glass-card p-4 text-center">
          <div className="text-2xl font-bold">{data.total_members}</div>
          <div className="text-xs text-slate-500">成员总数</div>
        </div>
        <div className="glass-card p-4 text-center">
          <div className="text-2xl font-bold">{data.active_proposals}</div>
          <div className="text-xs text-slate-500">活跃提案</div>
        </div>
        <div className="glass-card p-4 text-center">
          <div className="text-2xl font-bold">{(data.consensus_meter * 100).toFixed(0)}%</div>
          <div className="text-xs text-slate-500">共识度</div>
        </div>
      </div>

      {/* Consensus meter */}
      <div className="glass-card p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-bold text-slate-500">共识度</span>
          <span className="text-sm font-bold">{(data.consensus_meter * 100).toFixed(0)}%</span>
        </div>
        <progress
          className="progress progress-primary w-full"
          value={data.consensus_meter}
          max={1}
        />
      </div>

      {/* Members */}
      <div className="glass-card p-4">
        <h2 className="mb-3 text-sm font-bold text-slate-500">委员会成员</h2>
        {data.members.length === 0 ? (
          <p className="text-sm text-slate-400">暂无成员数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="table table-sm">
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
                {data.members.map((member) => (
                  <tr key={member.name}>
                    <td className="font-medium">{member.name}</td>
                    <td className="text-slate-500">{member.role}</td>
                    <td className="text-right">{member.score.toFixed(1)}</td>
                    <td className="text-right">{(member.accuracy * 100).toFixed(1)}%</td>
                    <td className="text-right">{member.total_votes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
