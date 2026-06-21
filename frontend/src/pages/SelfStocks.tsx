import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import type { WatchlistData, WatchlistGroup, WatchlistStock } from "../types/watchlist";

/* ── API ── */
function fetchWatchlist(groupId?: number): Promise<{ data: WatchlistData }> {
  let url = "/daily-workbench?market=CN&watchlist_limit=50";
  if (groupId) url += `&group_id=${groupId}`;
  return apiFetchV1(url);
}

function fetchGroups(): Promise<{ data: { items: WatchlistGroup[] } }> {
  return apiFetchV1("/user/groups");
}

function fmtPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function pctClass(v?: number | null): string {
  if (v == null) return "";
  return v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-600" : "";
}

function healthBadge(score?: number): string {
  if (score == null) return "badge-ghost";
  if (score >= 70) return "badge-success";
  if (score >= 40) return "badge-warning";
  return "badge-error";
}

export function SelfStocksPage() {
  const [activeGroupId, setActiveGroupId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<string>("priority");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: groupsData } = useSWR("watchlist/groups", () => fetchGroups(), { refreshInterval: 120_000 });
  const { data: wlData, error, isLoading } = useSWR(
    ["watchlist", activeGroupId, sortBy],
    () => fetchWatchlist(activeGroupId ?? undefined),
    { refreshInterval: 60_000 },
  );

  const groups = groupsData?.data?.items ?? [];
  const stocks = wlData?.data?.items ?? [];
  const summary = wlData?.data?.summary;

  const filtered = searchQuery
    ? stocks.filter(
        (s: WatchlistStock) =>
          (s.symbol ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
          (s.name ?? "").toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : stocks;

  const sorted = [...filtered].sort((a: WatchlistStock, b: WatchlistStock) => {
    switch (sortBy) {
      case "health": return (b.health_score ?? 0) - (a.health_score ?? 0);
      case "change": return Math.abs(b.change_pct ?? 0) - Math.abs(a.change_pct ?? 0);
      case "risk": return (b.risk_level ?? "").localeCompare(a.risk_level ?? "");
      case "amount": return (b.amount ?? 0) - (a.amount ?? 0);
      default: return (a.priority ?? 99) - (b.priority ?? 99);
    }
  });

  if (isLoading && !stocks.length) return <PageSkeleton rows={4} />;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">自选股中心</h1>
          <p className="text-sm text-slate-500">分组管理 · 健康评分 · 异动监控 · 风险提示</p>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn btn-primary btn-sm">新增标的</button>
          <button type="button" className="btn btn-ghost btn-sm">批量导入</button>
          <button type="button" className="btn btn-ghost btn-sm">导出 CSV</button>
        </div>
      </div>

      {/* Onboarding (show when no stocks) */}
      {!stocks.length && !isLoading && (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="glass-card rounded-2xl p-4 text-center">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand/10 text-sm font-bold text-brand">1</span>
            <h3 className="mt-2 text-sm font-bold">加自选</h3>
            <p className="mt-1 text-xs text-slate-500">跟踪核心标的，健康度与异动会出现在操盘台。</p>
          </div>
          <div className="glass-card rounded-2xl p-4 text-center">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand/10 text-sm font-bold text-brand">2</span>
            <h3 className="mt-2 text-sm font-bold">看盘面</h3>
            <p className="mt-1 text-xs text-slate-500">对照全景与涨跌结构，避免只看个股不看环境。</p>
          </div>
          <div className="glass-card rounded-2xl p-4 text-center">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand/10 text-sm font-bold text-brand">3</span>
            <h3 className="mt-2 text-sm font-bold">做记录</h3>
            <p className="mt-1 text-xs text-slate-500">用观察单沉淀买卖逻辑，便于复盘。</p>
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <select className="select select-bordered select-sm" value={activeGroupId ?? ""} onChange={(e) => setActiveGroupId(e.target.value ? Number(e.target.value) : null)}>
          <option value="">全部分组</option>
          {groups.map((g: WatchlistGroup) => (
            <option key={g.id} value={g.id}>{g.name} ({g.stock_count})</option>
          ))}
        </select>
        <select className="select select-bordered select-sm" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="priority">优先级</option>
          <option value="health">健康分</option>
          <option value="change">涨跌幅</option>
          <option value="risk">风险优先</option>
          <option value="amount">成交额</option>
        </select>
        <input
          type="search"
          className="input input-bordered input-sm flex-1 min-w-[160px]"
          placeholder="搜索代码 / 名称"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        {/* Summary panel */}
        <aside className="glass-card space-y-3 rounded-2xl p-4 lg:col-span-1">
          <h3 className="text-sm font-bold text-slate-500">组合概览</h3>
          {summary && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-slate-100 p-2 text-center dark:bg-slate-800">
                  <div className="text-xs text-slate-500">可评分</div>
                  <div className="text-lg font-bold">{summary.total ?? "--"}</div>
                </div>
                <div className="rounded-lg bg-slate-100 p-2 text-center dark:bg-slate-800">
                  <div className="text-xs text-slate-500">健康均分</div>
                  <div className="text-lg font-bold">{summary.avg_health ?? "--"}</div>
                </div>
                <div className="rounded-lg bg-emerald-50 p-2 text-center dark:bg-emerald-950/40">
                  <div className="text-xs text-slate-500">强势</div>
                  <div className="text-lg font-bold text-emerald-600">{summary.strong_count ?? 0}</div>
                </div>
                <div className="rounded-lg bg-rose-50 p-2 text-center dark:bg-rose-950/40">
                  <div className="text-xs text-slate-500">风险</div>
                  <div className="text-lg font-bold text-rose-600">{summary.risk_count ?? 0}</div>
                </div>
              </div>
              {summary.summary_text && (
                <p className="rounded-lg bg-slate-50 p-2 text-xs text-slate-600 dark:bg-slate-900">{summary.summary_text}</p>
              )}
            </>
          )}
        </aside>

        {/* Stock list */}
        <section className="overflow-x-auto lg:col-span-3">
          <table className="table w-full">
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>价格</th>
                <th>涨跌幅</th>
                <th>健康分</th>
                <th>行业</th>
                <th>成交额</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((s: WatchlistStock) => (
                <tr key={s.symbol} className="hover">
                  <td><code>{s.symbol}</code></td>
                  <td className="font-medium">{s.name ?? "--"}</td>
                  <td>{s.price != null ? `¥${s.price.toFixed(2)}` : "--"}</td>
                  <td className={pctClass(s.change_pct)}>{fmtPct(s.change_pct)}</td>
                  <td>
                    <span className={`badge ${healthBadge(s.health_score)}`}>{s.health_score ?? "--"}</span>
                  </td>
                  <td className="text-xs text-slate-500">{s.industry ?? "--"}</td>
                  <td className="text-xs text-slate-500">
                    {s.amount != null ? `${(s.amount / 1e8).toFixed(2)}亿` : "--"}
                  </td>
                </tr>
              ))}
              {!sorted.length && (
                <tr><td colSpan={7} className="py-12 text-center text-slate-500">暂无自选股数据</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}