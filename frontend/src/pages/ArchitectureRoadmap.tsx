import { useState, useEffect } from "react";
import { apiFetchV1 } from "../lib/api";

type RoadmapItem = { name: string; status: string; description: string };
type Phase = { phase: string; items: RoadmapItem[] };
type RoadmapData = { phases?: Phase[] };

export default function ArchitectureRoadmapPage() {
  const [data, setData] = useState<RoadmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await apiFetchV1<RoadmapData>("/system/architecture-roadmap");
        setData(res);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <div className="skeleton skeleton-card"></div>
        <div className="skeleton skeleton-card"></div>
      </div>
    );
  }

  const phases = data?.phases ?? [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="page-title">架构路线图</h1>
        <p className="text-sm text-slate-500 mt-1">系统架构阶段与里程碑进展</p>
      </div>

      {error && <div className="alert alert-error text-sm">加载失败: {error}</div>}

      {phases.length === 0 && !error && (
        <div className="quant-card text-center py-8">
          <p className="text-slate-500">暂无路线图数据</p>
        </div>
      )}

      <div className="space-y-4">
        {phases.map((phase, pi) => (
          <div key={pi} className="quant-card">
            <div className="hero-caption">{phase.phase}</div>
            <div className="relative pl-6 ml-2 border-l-2 border-slate-200 dark:border-slate-700 space-y-4 mt-4">
              {phase.items.map((item, ii) => {
                const statusColors: Record<string, string> = {
                  completed: "bg-emerald-500",
                  in_progress: "bg-blue-500",
                  planned: "bg-slate-400",
                  blocked: "bg-rose-500",
                };
                const dotColor = statusColors[item.status] || "bg-slate-400";
                return (
                  <div key={ii} className="relative">
                    <div className={`absolute -left-[25px] top-1 w-3 h-3 rounded-full ${dotColor} ring-2 ring-slate-900`}></div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-semibold">{item.name}</div>
                        <p className="text-sm text-slate-500">{item.description}</p>
                      </div>
                      <span className={`badge-soft whitespace-nowrap ${
                        item.status === "completed" ? "text-emerald-500" :
                        item.status === "in_progress" ? "text-blue-500" :
                        item.status === "blocked" ? "text-rose-500" : ""
                      }`}>
                        {item.status === "completed" ? "已完成" :
                         item.status === "in_progress" ? "进行中" :
                         item.status === "blocked" ? "阻塞" : "待开始"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}