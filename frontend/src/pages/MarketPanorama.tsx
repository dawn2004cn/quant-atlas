import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useSWR from "swr";
import { fetchMarketPanorama, fetchMarketSentiment } from "../lib/api";
import { PageSkeleton } from "../components/PageSkeleton";

function fmtPct(v: number | undefined | null): string {
  if (v == null || Number.isNaN(Number(v))) return "--";
  const n = Number(v);
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

function fmtPrice(v: number | undefined | null): string {
  if (v == null || Number.isNaN(Number(v))) return "--";
  return Number(v).toFixed(2);
}

function pctClass(v: number | undefined | null): string {
  if (v == null) return "text-slate-500";
  return v >= 0 ? "text-emerald-600" : "text-rose-600";
}

function TabPills({ tabs, active, onChange }: {
  tabs: string[];
  active: string;
  onChange: (t: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {tabs.map((t) => (
        <button
          key={t}
          type="button"
          className={`px-4 py-2 rounded-full text-sm font-bold transition-all cursor-pointer
            ${active === t
              ? "bg-gradient-to-r from-emerald-500 to-blue-500 text-white shadow-lg"
              : "bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
            }`}
          onClick={() => onChange(t)}
        >
          {t}
        </button>
      ))}
    </div>
  );
}

function RankingTable({ rows, label }: { rows: import("../types/market").PanoramaStockRow[]; label: string }) {
  const navigate = useNavigate();
  if (!rows.length) {
    return <p className="text-sm text-slate-500 py-4 text-center">暂无数据</p>;
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-800/60">
            <th className="px-3 py-2 text-left text-xs font-bold text-slate-500 uppercase">{label}</th>
            <th className="px-3 py-2 text-right text-xs font-bold text-slate-500 uppercase">现价</th>
            <th className="px-3 py-2 text-right text-xs font-bold text-slate-500 uppercase">涨跌幅</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((row, i) => (
            <tr
              key={row.code ?? i}
              className="border-t border-slate-100 dark:border-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
              onClick={() => navigate(`/stock/${encodeURIComponent(row.code ?? "")}`)}
            >
              <td className="px-3 py-2">
                <span className="font-bold">{row.name ?? row.code ?? "--"}</span>
                {row.code ? <span className="ml-2 text-xs text-slate-400">{row.code}</span> : null}
              </td>
              <td className="px-3 py-2 text-right font-mono">{fmtPrice(row.price)}</td>
              <td className={`px-3 py-2 text-right font-mono font-bold ${pctClass(row.change_pct)}`}>
                {fmtPct(row.change_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MarketPanoramaPage() {
  const [tab, setTab] = useState("涨幅榜");

  const { data: panorama, error, isLoading } = useSWR(
    "market-panorama",
    () => fetchMarketPanorama(),
    { revalidateOnFocus: false, refreshInterval: 60_000 },
  );

  const { data: sentiment } = useSWR(
    "market-sentiment",
    () => fetchMarketSentiment(),
    { revalidateOnFocus: false, refreshInterval: 120_000 },
  );

  const rankings = panorama?.data?.rankings;
  const sectors = panorama?.data?.sectors ?? [];

  if (isLoading && !panorama) {
    return <PageSkeleton rows={5} />;
  }

  return (
    <div className="space-y-5">
      {/* Hero */}
      <section className="glass-card p-6">
        <div className="hero-caption">Real-time Market Panorama</div>
        <h1 className="text-2xl font-bold">全市场纵览</h1>
        <p className="text-sm text-slate-500 mt-1">
          监控全量标的实时异动，内置高性能排序与多维过滤器
        </p>
      </section>

      {/* Error */}
      {error ? (
        <div className="alert alert-error text-sm">加载失败: {error.message}</div>
      ) : null}

      {/* Sentiment Summary */}
      {sentiment?.data ? (
        <section className="glass-card p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="hero-caption mb-1">市场情绪</div>
              <div className="text-3xl font-bold">{sentiment.data.level ?? "--"}</div>
              <p className="text-sm text-slate-500 mt-1">{sentiment.data.description ?? ""}</p>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-xl bg-emerald-50 px-4 py-3 dark:bg-emerald-950/40">
                <div className="text-2xl font-bold text-emerald-600">
                  {panorama?.data?.summary?.gainers ?? "--"}
                </div>
                <div className="text-xs text-slate-500">上涨</div>
              </div>
              <div className="rounded-xl bg-slate-100 px-4 py-3 dark:bg-slate-800/60">
                <div className="text-2xl font-bold">
                  {panorama?.data?.summary?.flat ?? "--"}
                </div>
                <div className="text-xs text-slate-500">平盘</div>
              </div>
              <div className="rounded-xl bg-rose-50 px-4 py-3 dark:bg-rose-950/40">
                <div className="text-2xl font-bold text-rose-600">
                  {panorama?.data?.summary?.losers ?? "--"}
                </div>
                <div className="text-xs text-slate-500">下跌</div>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {/* Sector Overview */}
      {sectors.length > 0 ? (
        <section className="glass-card p-6">
          <div className="hero-caption mb-2">板块概况</div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
            {sectors.slice(0, 16).map((s, i) => (
              <div
                key={s.name ?? i}
                className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800/40"
              >
                <span className="text-sm font-medium truncate">{s.name ?? "--"}</span>
                <span className={`text-sm font-bold ml-2 ${pctClass(s.change_pct)}`}>
                  {fmtPct(s.change_pct)}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {/* Rankings */}
      {rankings ? (
        <section className="glass-card p-6 space-y-4">
          <TabPills
            tabs={["涨幅榜", "跌幅榜", "成交额", "换手率"]}
            active={tab}
            onChange={setTab}
          />

          {tab === "涨幅榜" ? (
            <RankingTable rows={rankings.gainers ?? []} label="代码" />
          ) : tab === "跌幅榜" ? (
            <RankingTable rows={rankings.losers ?? []} label="代码" />
          ) : tab === "成交额" ? (
            <RankingTable rows={rankings.amounts ?? []} label="代码" />
          ) : tab === "换手率" ? (
            <RankingTable rows={rankings.turnovers ?? []} label="代码" />
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
