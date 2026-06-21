import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

type TeamMember = {
  user_id: number;
  username: string;
  role: string;
  avatar?: string;
  last_active: string;
};

type SharedNote = {
  id: string;
  title: string;
  content: string;
  author: string;
  updated_at: string;
};

type ActivityItem = {
  id: string;
  type: string;
  description: string;
  actor: string;
  timestamp: string;
};

type WorkspaceData = {
  team_members: TeamMember[];
  shared_notes: SharedNote[];
  activity_feed: ActivityItem[];
};

export function CollaborationWorkspacePage() {
  const { data, error, isLoading, mutate } = useSWR(
    "collaboration-workspace",
    () => apiFetchV1<WorkspaceData>("/collaboration/workspace"),
    { refreshInterval: 60_000 },
  );

  const [activeTab, setActiveTab] = useState<"members" | "notes" | "activity">("members");

  if (isLoading && !data) return <PageSkeleton rows={4} />;
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无协作工作区数据</div>;

  const members = data.team_members ?? [];
  const notes = data.shared_notes ?? [];
  const activity = data.activity_feed ?? [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">协作工作区</h1>
          <p className="text-sm text-slate-500">团队成员、共享笔记与活动动态</p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      <div className="tabs tabs-box">
        <button type="button" className={`tab ${activeTab === "members" ? "tab-active" : ""}`} onClick={() => setActiveTab("members")}>
          团队成员 ({members.length})
        </button>
        <button type="button" className={`tab ${activeTab === "notes" ? "tab-active" : ""}`} onClick={() => setActiveTab("notes")}>
          共享笔记 ({notes.length})
        </button>
        <button type="button" className={`tab ${activeTab === "activity" ? "tab-active" : ""}`} onClick={() => setActiveTab("activity")}>
          活动动态 ({activity.length})
        </button>
      </div>

      {activeTab === "members" && (
        <div className="glass-card overflow-x-auto p-4">
          {members.length === 0 ? (
            <div className="text-center text-slate-500 py-8">暂无团队成员</div>
          ) : (
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>成员</th>
                  <th>角色</th>
                  <th>最后活跃</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.user_id}>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="avatar">
                          <div className="w-8 h-8 rounded-full bg-brand/20 flex items-center justify-center">
                            <span className="text-xs font-bold text-brand">{m.username[0]?.toUpperCase()}</span>
                          </div>
                        </div>
                        <span className="font-medium">{m.username}</span>
                      </div>
                    </td>
                    <td><span className="badge badge-outline">{m.role}</span></td>
                    <td className="text-xs text-slate-500">{m.last_active}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === "notes" && (
        <div className="glass-card p-4 space-y-3">
          {notes.length === 0 ? (
            <div className="text-center text-slate-500 py-8">暂无共享笔记</div>
          ) : (
            notes.map((note) => (
              <div key={note.id} className="border rounded-lg p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <h4 className="font-semibold">{note.title}</h4>
                    <p className="text-sm text-slate-600 dark:text-slate-300 mt-1 line-clamp-2">{note.content}</p>
                  </div>
                </div>
                <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                  <span>作者：{note.author}</span>
                  <span>{note.updated_at}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "activity" && (
        <div className="glass-card p-4 space-y-3">
          {activity.length === 0 ? (
            <div className="text-center text-slate-500 py-8">暂无活动记录</div>
          ) : (
            activity.map((item) => (
              <div key={item.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
                <div className="w-2 h-2 mt-2 rounded-full bg-brand flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm">{item.description}</p>
                  <p className="text-xs text-slate-500 mt-1">{item.actor} · {item.timestamp}</p>
                </div>
                <span className="badge badge-ghost badge-xs">{item.type}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}