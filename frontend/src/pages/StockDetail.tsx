import { lazy, Suspense, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { StockQuoteCard } from "../components/stock/StockQuoteCard";
import { AiInsightPanel } from "../components/stock/AiInsightPanel";
import { TradePlanPanel } from "../components/stock/TradePlanPanel";
import { useAnalysisStream } from "../hooks/useAnalysisStream";
import { useAuth } from "../hooks/useAuth";
import { DemoBanner } from "../components/DemoBanner";
import { fetchStock, fetchStockHistory } from "../lib/api";
import { DEMO_STOCK_DETAIL } from "../lib/demoCatalog";
import { extractRealtime, normalizeBars, type StockDetailPayload } from "../types/stock";
import type { ChartOverlay } from "../components/charts/PriceHistoryChart";

const PriceHistoryChart = lazy(() =>
  import("../components/charts/PriceHistoryChart").then((mod) => ({
    default: mod.PriceHistoryChart,
  })),
);

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

export function StockDetailPage() {
  const { symbol = "" } = useParams();
  const [search] = useSearchParams();
  const market = search.get("m") || "CN";
  const { isAuthenticated, loading: authLoading } = useAuth();

  const { data, error, isLoading } = useSWR(
    isAuthenticated && symbol ? ["stock", symbol, market] : null,
    () => fetchStock(symbol, market),
  );
  const { data: historyRaw, error: historyError, isLoading: historyLoading } = useSWR(
    isAuthenticated && symbol ? ["stock-history", symbol, market] : null,
    () => fetchStockHistory(symbol, market, 120),
  );

  const liveQuote = data ? extractRealtime(data as StockDetailPayload) : null;
  const liveBars = normalizeBars(historyRaw);
  const isDemo = Boolean(error) || Boolean(historyError) || (!isLoading && !liveQuote?.price) || (!historyLoading && !liveBars.length);
  const quote = (!error && liveQuote?.price != null) ? liveQuote : DEMO_STOCK_DETAIL.quote;
  const bars = (!historyError && liveBars.length) ? liveBars : DEMO_STOCK_DETAIL.bars;
  const { steps, loading: aiLoading, error: aiError, start: startAi } = useAnalysisStream(symbol, market);
  const [overlays, setOverlays] = useState<ChartOverlay[]>(["ma5", "ma20", "volume"]);

  const toggleOverlay = (key: ChartOverlay) => {
    setOverlays((prev) => (prev.includes(key) ? prev.filter((x) => x !== key) : [...prev, key]));
  };

  if (authLoading) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <div className="animate-pulse rounded-xl bg-zinc-900/30 p-6 ring-1 ring-zinc-800/40">
          <div className="h-5 w-32 rounded bg-zinc-800/60" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <Panel className="flex flex-col items-center p-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-zinc-800/60 text-lg">🔒</div>
          <p className="mt-4 text-sm text-zinc-400">请先登录后查看个股详情</p>
          <Link className="mt-3 rounded-lg bg-emerald-500/15 px-4 py-2 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30 transition-colors hover:bg-emerald-500/20" to="/login">登录</Link>
        </Panel>
      </div>
    );
  }

  const displaySymbol = symbol || quote.code || "";

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.stockDetail} />

      {/* Hero: identity + quote + chart first (OpenStock-style stock focus) */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Link className="rounded-lg bg-zinc-800/40 px-3 py-1.5 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-colors hover:bg-zinc-800 hover:text-zinc-200" to="/">← 操盘台</Link>
            <Link className="rounded-lg bg-zinc-800/40 px-3 py-1.5 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-colors hover:bg-zinc-800 hover:text-zinc-200" to="/self-stocks">自选</Link>
            <Link className="rounded-lg bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-400 ring-1 ring-emerald-500/30" to={`/ai-analysis?symbol=${encodeURIComponent(displaySymbol)}&m=${market}`}>AI 诊股</Link>
          </div>
          <h1 className="mt-3 text-2xl font-bold tracking-tight text-zinc-100">
            {quote.name || displaySymbol}
            <span className="ml-2 font-mono text-base font-normal text-zinc-500">{displaySymbol}</span>
            <span className="ml-2 text-sm font-normal text-zinc-600">· {market}</span>
          </h1>
          <DemoBanner show={isDemo} />
        </div>
      </div>

      {isLoading && !quote && (
        <Panel className="flex items-center gap-3 p-5">
          <div className="h-4 w-4 animate-ping rounded-full bg-emerald-500/40" />
          <p className="text-sm text-zinc-500">加载行情…</p>
        </Panel>
      )}

      {quote && <StockQuoteCard quote={quote} />}

      <Panel className="p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--quant-muted)]">近 120 日走势</h3>
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["ma5", "MA5"],
                ["ma20", "MA20"],
                ["volume", "成交量"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => toggleOverlay(key)}
                className={
                  overlays.includes(key)
                    ? "rounded-md bg-[var(--quant-accent)]/20 px-2 py-1 text-[11px] text-[var(--quant-accent)] ring-1 ring-[var(--quant-accent)]/40"
                    : "rounded-md bg-[var(--quant-surface)] px-2 py-1 text-[11px] text-[var(--quant-muted)] ring-1 ring-[var(--quant-surface-border)]"
                }
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {historyLoading && !bars.length && (
          <div className="flex items-center gap-3 text-sm text-[var(--quant-muted)]">
            <div className="h-3 w-3 animate-spin rounded-full border-2 border-[var(--quant-surface-border)] border-t-[var(--quant-muted)]" />
            加载 K 线…
          </div>
        )}
        {bars.length > 0 && (
          <Suspense fallback={<div className="h-80 animate-pulse rounded-xl bg-[var(--quant-surface)]" />}>
            <PriceHistoryChart data={bars} overlays={overlays} />
          </Suspense>
        )}
      </Panel>

      {/* Secondary: plan / AI / indicators */}
      {symbol && <TradePlanPanel symbol={symbol} market={market} />}
      <AiInsightPanel symbol={symbol} market={market} steps={steps} loading={aiLoading} error={aiError} onStart={startAi} />

      {data?.indicators && Object.keys(data.indicators).length > 0 && (
        <Panel className="p-5">
          <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">技术指标</h3>
          <pre className="max-h-48 overflow-auto rounded-lg bg-zinc-800/40 p-3 font-mono text-[10px] text-zinc-400">{JSON.stringify(data.indicators, null, 2)}</pre>
        </Panel>
      )}

      <div className="flex flex-wrap gap-2 text-xs">
        <Link className="rounded-lg bg-zinc-800/40 px-4 py-2 font-medium text-zinc-400 ring-1 ring-zinc-700/40 hover:text-zinc-200" to="/market-coverage">
          数据说明
        </Link>
        <a className="rounded-lg bg-zinc-800/40 px-4 py-2 font-medium text-zinc-400 ring-1 ring-zinc-700/40 hover:text-zinc-200" href={`/stock/${encodeURIComponent(symbol)}?m=${market}`}>
          打开经典版详情
        </a>
      </div>
    </div>
  );
}
