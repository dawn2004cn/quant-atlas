import { Link } from "react-router-dom";
import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import {
  DecisionPanel,
  HealthBanner,
  MacroRow,
  SentimentHero,
} from "../components/workbench/Panels";
import { TimeseriesOpsCard } from "../components/workbench/TimeseriesOpsCard";
import {
  RecommendPanel,
  ReviewPanel,
  WatchlistPanel,
} from "../components/workbench/Lists";
import { useAuth } from "../hooks/useAuth";
import { useRealtime } from "../hooks/useRealtime";
import { fetchDailyWorkbench } from "../lib/api";
import { DEMO_WORKBENCH } from "../lib/demoWorkbench";
import { RealtimeBar } from "../components/workbench/RealtimeBar";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";

const MARKETS = ["CN", "HK", "US"] as const;
const MARKET_LABELS: Record<string, string> = { CN: "A股", HK: "港股", US: "美股" };

export function DashboardPage() {
  const { mode, username } = useAuth();
  const [market, setMarket] = useState<(typeof MARKETS)[number]>("CN");
  const [realtimeEnabled, setRealtimeEnabled] = useState(false);
  const { connected, lastQuote, lastAiChunk, error: realtimeError } = useRealtime(realtimeEnabled);

  const { data, error, isLoading, mutate } = useSWR(
    ["workbench", market],
    () => fetchDailyWorkbench(market, 12),
    { refreshInterval: 60_000, revalidateOnFocus: false, dedupingInterval: 10_000 },
  );

  const snapshot = data ?? (error ? DEMO_WORKBENCH : undefined);
  const isDemo = snapshot?.data_mode === "demo" || snapshot?.data_mode === "mixed" || Boolean(error && snapshot);

  if (isLoading && !snapshot) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-8 w-48 animate-pulse rounded bg-zinc-800/60" />
          <div className="flex gap-2">
            {MARKETS.map((m) => (
              <div key={m} className="h-8 w-14 animate-pulse rounded-lg bg-zinc-800/40" />
            ))}
          </div>
        </div>
        <div className="h-12 animate-pulse rounded-xl bg-zinc-800/40" />
        <PageSkeleton rows={4} showProgress />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-4">
      <CoreWorkflowStrip />
      <PageQuickNav items={QUICK_NAV_PRESETS.dashboard} />
      {/* ── Header Row ── */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">
            Daily Trading Desk
          </div>
          <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">
            今日操盘台
          </h1>
          <p className="mt-0.5 text-sm text-zinc-500">
            {username ? `欢迎回来，${username}` : `已登录（${mode}）`}
          </p>
          {isDemo ? (
            <p className="mt-1 text-[11px] font-mono text-amber-400/90">
              演示数据 · 行情源未就绪或仅部分可用
            </p>
          ) : null}
          {data?.health_banner?.quotes_full_dump_warn ? (
            <p className="mt-1 text-[11px] font-mono text-amber-500/90">
              quotes dump={data.health_banner.quotes_full_dump_count ?? 0}/
              thr={data.health_banner.quotes_full_dump_threshold ?? 1}{" "}
              <Link className="link link-hover text-amber-400" to="/observability">
                观测台
              </Link>
              {" · "}
              <Link className="link link-hover text-amber-400" to="/alert-center">
                预警中心
              </Link>
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {MARKETS.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMarket(m)}
              className={`relative rounded-lg px-3 py-1.5 text-xs font-semibold transition-all duration-200 ${
                market === m
                  ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30"
                  : "text-zinc-500 hover:bg-zinc-800/60 hover:text-zinc-300"
              }`}
            >
              {MARKET_LABELS[m]}
              <span className="ml-1 font-mono text-[10px] opacity-60">{m}</span>
            </button>
          ))}
          <div className="mx-1 h-5 w-px bg-zinc-700/60" />
          <button
            type="button"
            onClick={() => setRealtimeEnabled((v) => !v)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              realtimeEnabled
                ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30"
                : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
            }`}
          >
            {realtimeEnabled ? "实时已开" : "连接实时"}
          </button>
          <button
            type="button"
            onClick={() => mutate()}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:bg-zinc-800/60 hover:text-zinc-200"
          >
            刷新
          </button>
        </div>
      </div>

      {/* ── Connection Bar ── */}
      <RealtimeBar
        connected={connected}
        error={realtimeError}
        lastQuote={lastQuote}
        lastAiChunk={lastAiChunk}
      />

      {/* ── Timeseries ── */}
      <TimeseriesOpsCard />

      {/* ── Error State ── */}
      {error ? (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-5 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-rose-500/20 text-xs font-bold text-rose-400">!</span>
                <span className="text-sm font-semibold text-rose-400">数据加载失败</span>
              </div>
              <p className="mt-1 text-sm text-zinc-400">{error.message}</p>
            </div>
            <button
              type="button"
              onClick={() => mutate()}
              className="rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs font-medium text-rose-400 transition-colors hover:bg-rose-500/10"
            >
              重试
            </button>
          </div>
        </div>
      ) : null}

      {/* ── Main Content ── */}
      {snapshot ? (
        <>
          {snapshot.health_banner ? <HealthBanner data={snapshot} /> : null}

          {/* Market Sentiment Hero */}
          <SentimentHero data={snapshot} />

          {/* Macro Indices */}
          <MacroRow data={snapshot} />

          {/* Three-column decision + watchlist layout */}
          <div className="grid gap-4 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <DecisionPanel data={snapshot} />
            </div>
            <div className="space-y-4 lg:col-span-3">
              <WatchlistPanel
                items={snapshot.watchlist_health?.items ?? []}
                market={market}
              />
              <div className="grid gap-4 md:grid-cols-2">
                <RecommendPanel data={snapshot} market={market} />
                <ReviewPanel data={snapshot} />
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}