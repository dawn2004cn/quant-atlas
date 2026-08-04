import { useState, useEffect } from "react";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type Sector = { name: string; weight: number; return: number };
type AttributionData = {
  total_return?: number;
  allocation_effect?: number;
  selection_effect?: number;
  interaction_effect?: number;
  sectors?: Sector[];
};

export default function AttributionDashboardPage() {
  const [data, setData] = useState<AttributionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await apiFetchV1<AttributionData>("/analytics/attribution");
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

  const statCards = [
    { label: "总收益", value: data?.total_return, fmt: "pct" },
    { label: "配置效应", value: data?.allocation_effect, fmt: "pct" },
    { label: "选股效应", value: data?.selection_effect, fmt: "pct" },
    { label: "交互效应", value: data?.interaction_effect, fmt: "pct" },
  ];

  const fmtPct = (v?: number) => v != null ? `${(v >= 0 ? "+" : "")}${v.toFixed(2)}%` : "--";
  const pctClass = (v?: number) => v != null ? (v >= 0 ? "text-emerald-600" : "text-rose-600") : "";

  const sectors = data?.sectors ?? [];

  return (
    <div className="space-y-5">
      <CoreWorkflowStrip />
      <PageQuickNav items={QUICK_NAV_PRESETS.attributionDashboard} />
      <div>
        <h1 className="page-title">归因分析</h1>
        <p className="text-sm text-slate-500 mt-1">Brinson 绩效归因分解</p>
      </div>

      {error && <div className="alert alert-error text-sm">加载失败: {error}</div>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((s, i) => (
          <div key={i} className="quant-card">
            <div className="hero-caption">{s.label}</div>
            <div className={`text-2xl font-bold mono ${pctClass(s.value)}`}>
              {fmtPct(s.value)}
            </div>
          </div>
        ))}
      </div>

      {sectors.length > 0 && (
        <section className="quant-card">
          <h2 className="text-lg font-bold mb-4">行业分解</h2>
          <div className="overflow-x-auto">
            <table className="table w-full text-sm">
              <thead>
                <tr><th className="text-left">行业</th><th className="text-right">权重</th><th className="text-right">收益</th></tr>
              </thead>
              <tbody>
                {sectors.map((s, i) => (
                  <tr key={i}>
                    <td className="font-semibold">{s.name}</td>
                    <td className="text-right mono">{s.weight != null ? `${(s.weight * 100).toFixed(1)}%` : "--"}</td>
                    <td className={`text-right mono font-bold ${pctClass(s.return)}`}>{fmtPct(s.return)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}