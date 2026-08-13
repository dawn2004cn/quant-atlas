import { useEffect, useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { DemoBanner } from "../components/DemoBanner";
import { DEMO_STOCKS } from "../lib/demoCatalog";
import { apiFetchV1 } from "../lib/api";
import { Link } from "react-router-dom";
import type { WatchlistData, WatchlistGroup, WatchlistStock } from "../types/watchlist";

type ExperiencePayload = WatchlistData & {
  active_group?: WatchlistGroup;
  summary?: WatchlistData["summary"] & { text?: string; avg_score?: number };
};

type GroupsPayload = { groups?: WatchlistGroup[]; items?: WatchlistGroup[] };

function fetchGroups(): Promise<GroupsPayload> {
  return apiFetchV1<GroupsPayload>("/stock-groups");
}

function fetchExperience(groupId?: number, sortBy = "priority"): Promise<ExperiencePayload> {
  const q = new URLSearchParams({
    sort_by: sortBy,
    include_news: "false",
    market: "CN",
  });
  if (groupId != null) q.set("group_id", String(groupId));
  return apiFetchV1<ExperiencePayload>(`/watchlist/experience?${q}`);
}

function normalizeStock(row: WatchlistStock & { code?: string }): WatchlistStock {
  return {
    ...row,
    symbol: row.symbol || row.code || "",
  };
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

  const { data: groupsData } = useSWR("stock-groups", () => fetchGroups(), { refreshInterval: 120_000 });
  const groups = groupsData?.groups ?? groupsData?.items ?? [];

  useEffect(() => {
    if (activeGroupId == null && groups.length) {
      setActiveGroupId(groups[0].id);
    }
  }, [groups, activeGroupId]);

  const { data: wlData, error, isLoading } = useSWR(
    activeGroupId != null ? ["watchlist-experience", activeGroupId, sortBy] : null,
    () => fetchExperience(activeGroupId ?? undefined, sortBy),
    { refreshInterval: 60_000, revalidateOnFocus: false },
  );

  const liveStocks = (wlData?.items ?? []).map((s) => normalizeStock(s as WatchlistStock & { code?: string }));
  const summary = wlData?.summary;
  const isDemo = Boolean(error) || (!isLoading && !liveStocks.length);
  const stocks = isDemo ? DEMO_STOCKS : liveStocks;

  const filtered = searchQuery
    ? stocks.filter(
        (s: WatchlistStock) =>
          (s.symbol ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
          (s.name ?? "").toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : stocks;

  if (isLoading && !stocks.length) return <PageSkeleton rows={4} />;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.selfStocks} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">自选股中心</h1>
          <p className="text-sm text-slate-500">分组管理 · 健康评分 · 异动监控 · 风险提示</p>
          <DemoBanner show={isDemo} />
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn btn-primary btn-sm">新增标的</button>
          <button type="button" className="btn btn-ghost btn-sm">批量导入</button>
          <button type="button" className="btn btn-ghost btn-sm">导出 CSV</button>
        </div>
      </div>

      {!stocks.length && !isLoading && !isDemo && (
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
            <h3 className="mt-2 text-sm font-bold">跟流程</h3>
            <p className="mt-1 text-xs text-slate-500">诊股 / 回测 / 观察单闭环，沉淀可复核决策。</p>
          </div>
        </div>
      )}

      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <select
          className="select select-bordered select-sm"
          value={activeGroupId ?? ""}
          onChange={(e) => setActiveGroupId(e.target.value ? Number(e.target.value) : null)}
        >
          {groups.map((g) => (
            <option key={g.id} value={g.id}>{g.name}</option>
          ))}
        </select>
        <select className="select select-bordered select-sm" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="priority">优先级</option>
          <option value="health">健康分</option>
          <option value="change">涨跌幅</option>
          <option value="risk">风险</option>
          <option value="amount">成交额</option>
        </select>
        <input
          className="input input-bordered input-sm"
          placeholder="搜索代码/名称"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <span className="text-xs text-slate-500">
          {filtered.length} 只 · 均分 {summary?.avg_health ?? summary?.avg_score ?? "--"}
        </span>
      </div>

      {error ? <div className="alert alert-error">加载失败：{error.message}</div> : null}

      <section className="glass-card overflow-x-auto p-4">
        <table className="table w-full">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>现价</th>
              <th>涨跌幅</th>
              <th>健康分</th>
              <th>风险</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => (
              <tr key={s.symbol}>
                <td>
                  <Link className="link" to={`/stock/${encodeURIComponent(s.symbol)}`}>
                    <code>{s.symbol}</code>
                  </Link>
                </td>
                <td className="font-medium">{s.name ?? "--"}</td>
                <td>{s.price != null ? `¥${s.price.toFixed(2)}` : "--"}</td>
                <td className={pctClass(s.change_pct)}>{fmtPct(s.change_pct)}</td>
                <td><span className={`badge ${healthBadge(s.health_score)}`}>{s.health_score ?? "--"}</span></td>
                <td className="text-xs text-slate-500">{s.risk_level ?? "--"}</td>
              </tr>
            ))}
            {!filtered.length ? (
              <tr><td colSpan={6} className="py-12 text-center text-slate-500">暂无自选股</td></tr>
            ) : null}
          </tbody>
        </table>
      </section>
    </div>
  );
}
