import { useState, useEffect } from "react";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type Capability = {
  name: string;
  enabled: boolean;
  description: string;
  category: string;
};

type CapabilitiesResponse = {
  qlib?: boolean;
  celery?: boolean;
  rd_agent?: boolean;
  websocket?: boolean;
  capabilities?: Capability[];
};

export default function CapabilitiesPage() {
  const [data, setData] = useState<CapabilitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await apiFetchV1<CapabilitiesResponse>("/capabilities");
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
        <div className="skeleton skeleton-card"></div>
        <div className="skeleton skeleton-card"></div>
      </div>
    );
  }

  const stats = [
    { label: "Qlib", value: data?.qlib ? "已连接" : "未连接", status: data?.qlib },
    { label: "Celery", value: data?.celery ? "运行中" : "停止", status: data?.celery },
    { label: "RD Agent", value: data?.rd_agent ? "就绪" : "不可用", status: data?.rd_agent },
    { label: "WebSocket", value: data?.websocket ? "连接中" : "断开", status: data?.websocket },
  ];

  const caps = data?.capabilities ?? [];

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.capabilities} />
      <div>
        <h1 className="page-title">系统能力</h1>
        <p className="text-sm text-slate-500 mt-1">查看系统核心组件与能力注册表状态</p>
      </div>

      {error && (
        <div className="alert alert-error text-sm">加载失败: {error}</div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s, i) => (
          <div key={i} className="quant-card">
            <div className="hero-caption">{s.label}</div>
            <div className="text-2xl font-bold mono mt-1">{s.value}</div>
            <div className={`mt-2 badge-soft ${s.status ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400" : "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400"}`}>
              {s.status ? "正常" : "异常"}
            </div>
          </div>
        ))}
      </div>

      <section className="quant-card">
        <h2 className="text-lg font-bold mb-4">能力注册表</h2>
        {caps.length === 0 ? (
          <p className="text-sm text-slate-500">暂无能力数据</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {caps.map((c, i) => (
              <div key={i} className="glass-panel p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold">{c.name}</div>
                    <p className="text-sm text-slate-500 mt-1">{c.description}</p>
                  </div>
                  <span className={`badge ${c.enabled ? "badge-success" : "badge-ghost"}`}>
                    {c.enabled ? "启用" : "禁用"}
                  </span>
                </div>
                <div className="text-xs text-slate-400 mt-2">{c.category}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}