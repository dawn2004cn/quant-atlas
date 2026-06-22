import { useState, useEffect } from "react";
import { apiFetchV1 } from "../lib/api";

type AssistantData = {
  health_score?: number;
  tips?: Array<{ title: string; description: string }>;
  resources?: Array<{ title: string; url: string }>;
  portfolio_health?: { diversification?: number; risk_level?: string; recommendation?: string };
};

export default function RetailAssistantPage() {
  const [data, setData] = useState<AssistantData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await apiFetchV1<AssistantData>("/user/retail-assistant");
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
    return <div className="space-y-4"><div className="skeleton skeleton-card"></div><div className="skeleton skeleton-card"></div></div>;
  }

  const tips = data?.tips ?? [];
  const resources = data?.resources ?? [];
  const ph = data?.portfolio_health;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="page-title">散户助手</h1>
        <p className="text-sm text-slate-500 mt-1">投资学习与组合健康检查</p>
      </div>

      {error && <div className="alert alert-error text-sm">加载失败: {error}</div>}

      {data?.health_score != null && (
        <div className="quant-card">
          <div className="hero-caption">组合健康分</div>
          <div className="text-4xl font-bold">{data.health_score}</div>
        </div>
      )}

      {ph && (
        <section className="quant-card space-y-3">
          <h2 className="text-lg font-bold">组合健康检查</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <div><div className="hero-caption">分散度</div><div className="text-xl font-bold">{ph.diversification != null ? `${(ph.diversification * 100).toFixed(0)}%` : "--"}</div></div>
            <div><div className="hero-caption">风险等级</div><div className="text-xl font-bold">{ph.risk_level ?? "--"}</div></div>
            <div><div className="hero-caption">建议</div><div className="text-sm text-slate-500">{ph.recommendation ?? "--"}</div></div>
          </div>
        </section>
      )}

      {tips.length > 0 && (
        <section className="quant-card space-y-3">
          <h2 className="text-lg font-bold">投资技巧</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {tips.map((t, i) => (
              <div key={i} className="glass-panel p-4">
                <div className="font-semibold">{t.title}</div>
                <p className="text-sm text-slate-500 mt-1">{t.description}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {resources.length > 0 && (
        <section className="quant-card space-y-3">
          <h2 className="text-lg font-bold">学习资源</h2>
          <div className="space-y-2">
            {resources.map((r, i) => (
              <a key={i} href={r.url} target="_blank" rel="noopener noreferrer" className="block glass-panel p-3 hover:opacity-80 transition-opacity">
                <div className="font-semibold">{r.title}</div>
              </a>
            ))}
          </div>
        </section>
      )}

      {!error && !data?.health_score && tips.length === 0 && resources.length === 0 && (
        <div className="quant-card text-center py-8 text-slate-500">暂无助手数据</div>
      )}
    </div>
  );
}