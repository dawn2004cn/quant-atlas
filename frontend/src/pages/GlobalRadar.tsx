import { useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_GLOBAL_RADAR } from "../lib/demoCatalog";

type GlobalRadarData = {
  total_assets: number;
  gainers: number;
  losers: number;
  last_update: string;
  markets: Array<{
    name: string;
    code: string;
    indices: Array<{ label: string; code?: string; price: number; change_pct: number }>;
  }>;
  linkages?: Array<{
    us_sector: string;
    cn_sector: string;
    correlation: number;
    signal: "positive" | "negative" | "neutral";
    summary: string;
  }>;
};

function fmtPct(v?: number | null): string {
  if (v == null) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function pctClass(v?: number | null): string {
  if (v == null) return "";
  return v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-600" : "";
}

function corrLabel(c?: number): string {
  if (c == null) return "未知";
  const a = Math.abs(c);
  if (a >= 0.7) return "强相关";
  if (a >= 0.4) return "中相关";
  return "弱相关";
}

const MARKET_TABS = [
  { key: "CN", label: "A股" },
  { key: "HK", label: "港股" },
  { key: "US", label: "美股" },
  { key: "CRYPTO", label: "加密货币" },
];

export function GlobalRadarPage() {
  const [activeTab, setActiveTab] = useState("CN");

  const { data, error, isLoading } = useSWR(
    "global-radar",
    () => apiFetchV1<{ data: GlobalRadarData }>("/markets/global/radar"),
    { refreshInterval: 60_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={4} />;

  const live = data?.data;
  const isDemo = Boolean(error) || !live?.markets?.length;
  const radar = isDemo ? DEMO_GLOBAL_RADAR : live;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.globalRadar} />
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">全球资产透视塔</h1>
          <p className="text-sm text-slate-500">一站式监控 A股 / 港股 / 美股 / 加密货币</p>
          <DemoBanner show={isDemo} />
        </div>
      </div>

      {/* Quick Stats */}
      {radar && (
        <div className="grid grid-cols-4 gap-4">
          <div className="glass-card rounded-2xl p-4 text-center"><div className="text-2xl font-black">{radar.total_assets ?? "--"}</div><div className="text-xs text-slate-500">资产总数</div></div>
          <div className="glass-card rounded-2xl border-emerald-200 p-4 text-center"><div className="text-2xl font-black text-emerald-600">{radar.gainers ?? "--"}</div><div className="text-xs text-slate-500">上涨</div></div>
          <div className="glass-card rounded-2xl border-rose-200 p-4 text-center"><div className="text-2xl font-black text-rose-600">{radar.losers ?? "--"}</div><div className="text-xs text-slate-500">下跌</div></div>
          <div className="glass-card rounded-2xl p-4 text-center"><div className="text-lg font-bold">{radar.last_update ?? "--"}</div><div className="text-xs text-slate-500">最后更新</div></div>
        </div>
      )}

      {error && <div className="alert alert-error">{error.message}</div>}

      {/* Market Tabs */}
      <div className="tabs tabs-box">
        {MARKET_TABS.map((t) => (
          <button key={t.key} type="button" className={`tab ${activeTab === t.key ? "tab-active" : ""}`} onClick={() => setActiveTab(t.key)}>{t.label}</button>
        ))}
      </div>

      {/* Market Indices */}
      <section className="glass-card overflow-x-auto p-4">
        <table className="table w-full">
          <thead><tr><th>名称</th><th>代码</th><th>价格</th><th>涨跌幅</th></tr></thead>
          <tbody>
            {(radar?.markets ?? []).filter((m) => m.code === activeTab).flatMap((m) => m.indices).map((idx) => (
              <tr key={idx.label}>
                <td className="font-medium">{idx.label}</td>
                <td><code>{idx.code ?? "--"}</code></td>
                <td>{(idx.price ?? 0).toFixed(2)}</td>
                <td className={pctClass(idx.change_pct)}>{fmtPct(idx.change_pct)}</td>
              </tr>
            ))}
            {!radar?.markets?.length && (
              <tr><td colSpan={4} className="py-8 text-center text-slate-500">暂无市场数据</td></tr>
            )}
          </tbody>
        </table>
      </section>

      {/* Global Linkages */}
      <section className="glass-card p-4">
        <h2 className="mb-3 text-sm font-bold">全球联动分析</h2>
        {radar?.linkages?.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {radar.linkages.map((lk) => (
              <div key={lk.us_sector} className={`rounded-xl border p-4 ${lk.signal === "positive" ? "border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30" : lk.signal === "negative" ? "border-rose-200 bg-rose-50 dark:bg-rose-950/30" : "border-slate-200 bg-slate-50 dark:bg-slate-800/60"}`}>
                <div className="flex items-center justify-between">
                  <div className="text-sm font-bold">{lk.us_sector} → {lk.cn_sector}</div>
                  <span className="badge badge-sm">{corrLabel(lk.correlation)}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{lk.summary}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">暂无联动分析数据</p>
        )}
      </section>
    </div>
  );
}