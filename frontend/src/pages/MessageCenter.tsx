import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

type Message = {
  id: string;
  sender_id: number;
  sender_name: string;
  subject: string;
  preview: string;
  content: string;
  is_read: boolean;
  created_at: string;
  conversation_id: string;
};

type MessagesData = {
  conversations: Message[];
};

export function MessageCenterPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, error, isLoading, mutate } = useSWR(
    "messages",
    () => apiFetchV1<MessagesData>("/messages"),
    { refreshInterval: 30_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={4} />;
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无消息数据</div>;

  const conversations = data.conversations ?? [];
  const selected = conversations.find((m) => m.id === selectedId) ?? null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">消息中心</h1>
          <p className="text-sm text-slate-500">系统消息与协作通知</p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      {conversations.length === 0 && !selectedId ? (
        <div className="glass-card p-12 text-center">
          <div className="text-4xl mb-4 text-slate-300">📭</div>
          <p className="text-lg font-semibold text-slate-500">暂无消息</p>
          <p className="text-sm text-slate-400 mt-2">当有系统通知、协作邀请或策略预警时，消息将显示在这里</p>
        </div>
      ) : (
        <div className="flex gap-4 flex-col md:flex-row">
          <div className="glass-card overflow-y-auto p-2 w-full md:w-80 md:min-w-[18rem] max-h-[70vh]">
            {conversations.map((msg) => (
              <button
                key={msg.id}
                type="button"
                className={`w-full text-left p-3 rounded-lg transition ${
                  selectedId === msg.id
                    ? "bg-brand/10 ring-1 ring-brand"
                    : "hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
                onClick={() => setSelectedId(msg.id)}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-sm truncate">{msg.subject}</span>
                  {!msg.is_read && <span className="badge badge-primary badge-xs">新</span>}
                </div>
                <p className="text-xs text-slate-500 mt-1 truncate">{msg.preview}</p>
                <p className="text-xs text-slate-400 mt-1">{msg.sender_name} · {msg.created_at}</p>
              </button>
            ))}
          </div>

          <div className="flex-1 min-w-0">
            {selected ? (
              <div className="glass-card p-6 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-bold">{selected.subject}</h3>
                    <p className="text-sm text-slate-500">
                      {selected.sender_name} · {selected.created_at}
                    </p>
                  </div>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSelectedId(null)}>
                    关闭
                  </button>
                </div>
                <div className="border-t pt-4 whitespace-pre-wrap text-sm leading-relaxed">
                  {selected.content}
                </div>
              </div>
            ) : (
              <div className="glass-card p-12 text-center">
                <p className="text-slate-400">选择一条消息查看详情</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}