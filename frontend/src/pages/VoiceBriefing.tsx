import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

type BriefingItem = {
  id: string;
  title: string;
  summary: string;
  audio_url?: string;
  duration_seconds: number;
  category: string;
  created_at: string;
  is_played: boolean;
};

type BriefingData = {
  items: BriefingItem[];
  last_generated: string;
  schedule: string;
};

export function VoiceBriefingPage() {
  const { data, error, isLoading, mutate } = useSWR(
    "voice-briefing",
    () => apiFetchV1<BriefingData>("/voice-briefing/status"),
    { refreshInterval: 60_000 },
  );

  const [playingId, setPlayingId] = useState<string | null>(null);

  if (isLoading && !data) return <PageSkeleton rows={4} />;
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无语音简报数据</div>;

  const items = data.items ?? [];

  const handlePlay = (item: BriefingItem) => {
    if (playingId === item.id) {
      setPlayingId(null);
      return;
    }
    setPlayingId(item.id);
    if (item.audio_url) {
      const audio = new Audio(item.audio_url);
      audio.onended = () => setPlayingId(null);
      audio.play().catch(() => setPlayingId(null));
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">语音简报</h1>
          <p className="text-sm text-slate-500">
            {data.schedule
              ? `生成计划：${data.schedule}`
              : "AI 语音市场简报与策略分析"}
          </p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      {data.last_generated && (
        <div className="text-xs text-slate-500">最近生成：{data.last_generated}</div>
      )}

      {items.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-lg font-semibold text-slate-500">暂无语音简报</p>
          <p className="text-sm text-slate-400 mt-2">
            配置语音简报生成计划后，AI 将自动生成市场播报
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className={`glass-card p-4 flex items-start gap-4 transition ${
                playingId === item.id ? "ring-2 ring-brand" : ""
              }`}
            >
              <button
                type="button"
                className={`btn btn-circle btn-sm ${playingId === item.id ? "btn-primary" : "btn-ghost"} flex-shrink-0`}
                onClick={() => handlePlay(item)}
                disabled={!item.audio_url}
              >
                {playingId === item.id ? "⏹" : "▶"}
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="font-semibold">{item.title}</h4>
                  <span className="badge badge-ghost badge-sm flex-shrink-0">{item.category}</span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1 line-clamp-2">{item.summary}</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                  <span>{item.duration_seconds}s</span>
                  <span>{item.created_at}</span>
                  {item.is_played && <span className="text-slate-400">已播放</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}