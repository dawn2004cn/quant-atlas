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
import { RealtimeBar } from "../components/workbench/RealtimeBar";

const MARKETS = ["CN", "HK", "US"] as const;

export function DashboardPage() {
  const { mode, username } = useAuth();
  const [market, setMarket] = useState<(typeof MARKETS)[number]>("CN");
  const { connected, lastQuote, lastAiChunk, error: realtimeError } = useRealtime(true);

  const { data, error, isLoading, mutate } = useSWR(
    ["workbench", market],
    () => fetchDailyWorkbench(market, 12),
    { refreshInterval: 60_000 },
  );

  if (isLoading && !data) {
    return <PageSkeleton rows={5} />;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">今日操盘台</h1>
          <p className="text-sm text-slate-500">
            {username ? `欢迎，${username}` : `已登录（${mode}）`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {MARKETS.map((m) => (
            <button
              key={m}
              type="button"
              className={`btn btn-sm ${market === m ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setMarket(m)}
            >
              {m}
            </button>
          ))}
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => mutate()}>
            刷新
          </button>
        </div>
      </div>

      <RealtimeBar
        connected={connected}
        error={realtimeError}
        lastQuote={lastQuote}
        lastAiChunk={lastAiChunk}
      />

      <TimeseriesOpsCard />

      {error ? (
        <div className="alert alert-error">
          加载失败：{error.message}
          <button type="button" className="btn btn-sm" onClick={() => mutate()}>
            重试
          </button>
        </div>
      ) : null}

      {data ? (
        <>
          {data.health_banner ? <HealthBanner data={data} /> : null}
          <SentimentHero data={data} />
          <MacroRow data={data} />
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-1">
              <DecisionPanel data={data} />
            </div>
            <div className="space-y-4 lg:col-span-2">
              <WatchlistPanel
                items={data.watchlist_health?.items ?? []}
                market={market}
              />
              <div className="grid gap-4 md:grid-cols-2">
                <RecommendPanel data={data} market={market} />
                <ReviewPanel data={data} />
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
