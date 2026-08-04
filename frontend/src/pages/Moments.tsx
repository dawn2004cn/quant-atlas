import { useState, useEffect } from "react";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type Moment = { id: string; content: string; created_at: string; type: string };

export default function MomentsPage() {
  const [items, setItems] = useState<Moment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await apiFetchV1<{ items?: Moment[] }>("/user/moments?limit=20");
        setItems(res?.items ?? []);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const typeLabel: Record<string, string> = { ai: "AI 分析", post: "用户动态", system: "系统通知" };

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.moments} />
      <div>
        <h1 className="page-title">投资动态</h1>
        <p className="text-sm text-slate-500 mt-1">AI 投资笔记与社区动态</p>
      </div>

      {error && <div className="alert alert-error text-sm">加载失败: {error}</div>}

      {loading && !items.length ? (
        <div className="space-y-3">
          {[1,2,3,4].map((i) => <div key={i} className="skeleton skeleton-row"></div>)}
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((m) => (
            <div key={m.id} className="quant-card">
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="badge-soft text-xs">{typeLabel[m.type] || m.type}</span>
                <span className="text-xs text-slate-500">{m.created_at ? new Date(m.created_at).toLocaleString("zh-CN") : ""}</span>
              </div>
              <p className="text-sm whitespace-pre-wrap">{m.content}</p>
            </div>
          ))}
          {items.length === 0 && <div className="quant-card text-center py-8 text-slate-500">暂无动态</div>}
        </div>
      )}
    </div>
  );
}