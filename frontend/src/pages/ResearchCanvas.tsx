import { useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_RESEARCH_CANVAS } from "../lib/demoCatalog";

type CanvasItem = {
  id: string;
  type: "note" | "chart" | "link" | "image" | "document";
  title: string;
  content: string;
  preview_url?: string;
  tags: string[];
  position?: { x: number; y: number };
  created_at: string;
  updated_at: string;
};

type CanvasData = {
  items: CanvasItem[];
};

const TYPE_ICON: Record<string, string> = {
  note: "📝",
  chart: "📊",
  link: "🔗",
  image: "🖼",
  document: "📄",
};

export function ResearchCanvasPage() {
  const [filter, setFilter] = useState<string>("all");

  const { data, error, isLoading, mutate } = useSWR(
    "research-canvas",
    () => apiFetchV1<CanvasData>("/research/canvas"),
  );

  if (isLoading && !data) return <PageSkeleton rows={4} />;

  const live = data?.items ?? [];
  const isDemo = Boolean(error) || (!isLoading && !live.length);
  const items = (isDemo ? DEMO_RESEARCH_CANVAS : live).filter(
    (item) => filter === "all" || item.type === filter,
  );

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.researchCanvas} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">研究画板</h1>
          <p className="text-sm text-slate-500">研究笔记、图表与资料集合</p>
          <DemoBanner show={isDemo} />
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void mutate()}>
          刷新
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["all", "note", "chart", "link", "image", "document"] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={`btn btn-sm ${filter === t ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setFilter(t)}
          >
            {t === "all" ? "全部" : `${TYPE_ICON[t] ?? ""} ${t}`}
          </button>
        ))}
      </div>

      {items.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-lg font-semibold text-slate-500">暂无研究画板内容</p>
          <p className="text-sm text-slate-400 mt-2">
            {filter === "all"
              ? "通过研究工具添加笔记、图表和资料后，内容将显示在这里"
              : "当前筛选条件下没有内容"}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <div key={item.id} className="glass-card p-4 space-y-2 transition hover:shadow-md">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{TYPE_ICON[item.type] ?? "📄"}</span>
                  <h4 className="font-semibold text-sm truncate">{item.title}</h4>
                </div>
                <span className="badge badge-ghost badge-xs">{item.type}</span>
              </div>

              <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-3">{item.content}</p>

              {item.preview_url && (
                <div className="bg-slate-100 dark:bg-slate-800 rounded h-20 flex items-center justify-center text-xs text-slate-400">
                  {item.type === "image" ? (
                    <img
                      src={item.preview_url}
                      alt={item.title}
                      className="max-h-full max-w-full object-contain rounded"
                    />
                  ) : (
                    <span className="truncate px-2">{item.preview_url}</span>
                  )}
                </div>
              )}

              {item.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {item.tags.map((tag) => (
                    <span key={tag} className="badge badge-ghost badge-xs">{tag}</span>
                  ))}
                </div>
              )}

              <div className="text-xs text-slate-400">
                {item.updated_at !== item.created_at
                  ? `更新于 ${item.updated_at}`
                  : `创建于 ${item.created_at}`}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}