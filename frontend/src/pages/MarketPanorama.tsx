import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { fetchMarketPanorama, fetchMarketQuotesPage, fetchMarketSentiment } from "../lib/api";
import { PageSkeleton } from "../components/PageSkeleton";

/* ── Helpers ── */
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
  if (v == null) return "text-zinc-500";
  return v >= 0 ? "text-emerald-400" : "text-rose-400";
}

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

function RankingTable({ rows, label }: { rows: import("../types/market").PanoramaStockRow[]; label: string }) {
  const navigate = useNavigate();
  if (!rows.length) {
    return <p className="py-8 text-center text-sm text-zinc-600">暂无数据</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg ring-1 ring-zinc-800/40">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800/60 text-left text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
            <th className="px-4 py-2.5">{label}</th>
            <th className="px-4 py-2.5 text-right">现价</th>
            <th className="px-4 py-2.5 text-right">涨跌幅</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/30">
          {rows.slice(0, 20).map((row, i) => (
            <tr
              key={row.code ?? i}
              onClick={() => navigate(`/stock/${encodeURIComponent(row.code ?? "")}`)}
              className="cursor-pointer transition-colors hover:bg-zinc-800/30"
            >
              <td className="px-4 py-2.5">
                <span className="font-medium text-zinc-200">{row.name ?? row.code ?? "--"}</span>
                {row.code ? <span className="ml-2 font-mono text-[10px] text-zinc-600">{row.code}</span> : null}
              </td>
              <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-300">{fmtPrice(row.price)}</td>
              <td className={`px-4 py-2.5 text-right font-mono tabular-nums font-semibold ${pctClass(row.change_pct)}`}>
                {fmtPct(row.change_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const TABS = ["涨幅榜", "跌幅榜", "成交额", "换手率"];

const SCAN_FILTERS: { key: string; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "up", label: "上涨" },
  { key: "down", label: "下跌" },
  { key: "limit_up", label: "涨停" },
  { key: "limit_down", label: "跌停" },
];

export function MarketPanoramaPage() {
  const [tab, setTab] = useState("涨幅榜");
  const [listPage, setListPage] = useState(1);
  const [listFilter, setListFilter] = useState("all");
  const [listScope, setListScope] = useState<"market" | "watchlist">("market");

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
  const { data: quotesPage, isLoading: quotesLoading } = useSWR(
    ["market-quotes-page", listPage, listFilter, listScope],
    () =>
      fetchMarketQuotesPage({
        page: listPage,
        page_size: 40,
        sort: "change_pct",
        order: "desc",
        filter: listFilter,
        scope: listScope,
      }),
    { revalidateOnFocus: false, refreshInterval: 45_000 },
  );

  const rankings = panorama?.data?.rankings;
  const sectors = panorama?.data?.sectors ?? [];
  const marketStats = quotesPage?.stats;
  const listItems = quotesPage?.items ?? [];
  const listTotal = quotesPage?.total ?? 0;
  const listPageSize = quotesPage?.page_size ?? 40;
  const listPageCount = Math.max(1, Math.ceil(listTotal / listPageSize));

  if (isLoading && !panorama) return <PageSkeleton rows={4} />;

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.marketPanorama} />
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">
          Real-time Market Panorama
        </div>
        <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">全市场纵览</h1>
        <p className="mt-1 text-sm text-zinc-500">监控全量标的实时异动，内置高性能排序与多维过滤器</p>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
          加载失败: {error.message}
        </div>
      ) : null}

      {/* Sentiment Summary */}
      {sentiment?.data ? (
        <Panel className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">市场情绪</p>
              <div className="mt-1 text-3xl font-bold tracking-tight text-zinc-100">{sentiment.data.level ?? "--"}</div>
              <p className="mt-1 text-sm text-zinc-500">{sentiment.data.description ?? ""}</p>
              {sentiment.data.score != null && (
                <div className="mt-2 flex items-center gap-2">
                  <div className="h-1.5 w-24 overflow-hidden rounded-full bg-zinc-800">
                    <div className="h-full rounded-full bg-emerald-500/60" style={{ width: `${sentiment.data.score}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-zinc-500">{sentiment.data.score}</span>
                </div>
              )}
            </div>
            <div className="flex gap-3">
              <div className="min-w-[72px] rounded-lg bg-emerald-500/8 px-4 py-2.5 text-center ring-1 ring-emerald-500/10">
                <div className="text-lg font-bold font-mono tabular-nums text-emerald-400">
                  {marketStats?.up ?? panorama?.data?.summary?.gainers ?? "--"}
                </div>
                <div className="text-[10px] uppercase tracking-[0.1em] text-emerald-400/60">上涨</div>
              </div>
              <div className="min-w-[72px] rounded-lg bg-zinc-800/50 px-4 py-2.5 text-center">
                <div className="text-lg font-bold font-mono tabular-nums text-zinc-300">
                  {marketStats?.flat ?? panorama?.data?.summary?.flat ?? "--"}
                </div>
                <div className="text-[10px] uppercase tracking-[0.1em] text-zinc-500">平盘</div>
              </div>
              <div className="min-w-[72px] rounded-lg bg-rose-500/8 px-4 py-2.5 text-center ring-1 ring-rose-500/10">
                <div className="text-lg font-bold font-mono tabular-nums text-rose-400">
                  {marketStats?.down ?? panorama?.data?.summary?.losers ?? "--"}
                </div>
                <div className="text-[10px] uppercase tracking-[0.1em] text-rose-400/60">下跌</div>
              </div>
            </div>
          </div>
        </Panel>
      ) : null}

      {/* Sectors */}
      {sectors.length > 0 ? (
        <Panel className="p-5">
          <p className="mb-4 text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">板块概况</p>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-4">
            {sectors.slice(0, 16).map((s, i) => (
              <div key={s.name ?? i} className="flex items-center justify-between rounded-lg bg-zinc-800/40 px-3 py-2">
                <span className="truncate text-sm font-medium text-zinc-300">{s.name ?? "--"}</span>
                <span className={`ml-2 font-mono text-sm font-semibold tabular-nums ${pctClass(s.change_pct)}`}>
                  {fmtPct(s.change_pct)}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      {/* Paginated market scanner (server-side snapshot) */}
      <Panel className="p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">全市场扫描</p>
          <div className="flex gap-px rounded-lg bg-zinc-800/60 p-0.5">
            <button
              type="button"
              onClick={() => { setListScope("market"); setListPage(1); }}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                listScope === "market" ? "bg-zinc-800 text-zinc-200" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              全市场
            </button>
            <button
              type="button"
              onClick={() => { setListScope("watchlist"); setListPage(1); }}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                listScope === "watchlist" ? "bg-zinc-800 text-zinc-200" : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              自选股
            </button>
          </div>
        </div>
        <div className="mb-4 flex flex-wrap gap-1.5">
          {SCAN_FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              onClick={() => { setListFilter(f.key); setListPage(1); }}
              className={`rounded-md px-3 py-1 text-xs font-medium ring-1 transition-colors ${
                listFilter === f.key
                  ? "bg-zinc-800 text-zinc-200 ring-zinc-700"
                  : "text-zinc-500 ring-zinc-800/60 hover:text-zinc-300"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        {quotesLoading && !quotesPage ? (
          <p className="py-8 text-center text-sm text-zinc-600">加载行情…</p>
        ) : (
          <>
            <RankingTable rows={listItems} label="代码" />
            <div className="mt-4 flex items-center justify-between text-xs text-zinc-500">
              <span>
                第 {listPage} / {listPageCount} 页 · 共 {listTotal} 条
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={listPage <= 1}
                  onClick={() => setListPage((p) => Math.max(1, p - 1))}
                  className="rounded-md px-3 py-1 ring-1 ring-zinc-800 disabled:opacity-40"
                >
                  上一页
                </button>
                <button
                  type="button"
                  disabled={listPage >= listPageCount}
                  onClick={() => setListPage((p) => p + 1)}
                  className="rounded-md px-3 py-1 ring-1 ring-zinc-800 disabled:opacity-40"
                >
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </Panel>

      {/* Rankings */}
      {rankings ? (
        <Panel className="p-5">
          <div className="mb-4 flex gap-px rounded-lg bg-zinc-800/60 p-0.5 w-fit">
            {TABS.map((t) => (
              <button key={t} type="button" onClick={() => setTab(t)}
                className={`rounded-md px-4 py-1.5 text-xs font-medium transition-all ${
                  tab === t ? "bg-zinc-800 text-zinc-200 shadow-sm" : "text-zinc-500 hover:text-zinc-300"
                }`}
              >{t}</button>
            ))}
          </div>

          {tab === "涨幅榜" ? <RankingTable rows={rankings.gainers ?? []} label="代码" /> :
           tab === "跌幅榜" ? <RankingTable rows={rankings.losers ?? []} label="代码" /> :
           tab === "成交额" ? <RankingTable rows={rankings.amounts ?? []} label="代码" /> :
           tab === "换手率" ? <RankingTable rows={rankings.turnovers ?? []} label="代码" /> : null}
        </Panel>
      ) : null}
    </div>
  );
}