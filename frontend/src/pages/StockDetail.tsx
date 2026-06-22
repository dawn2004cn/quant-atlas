import { lazy, Suspense } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import useSWR from "swr";
import { StockQuoteCard } from "../components/stock/StockQuoteCard";
import { AiInsightPanel } from "../components/stock/AiInsightPanel";
import { TradePlanPanel } from "../components/stock/TradePlanPanel";
import { useAnalysisStream } from "../hooks/useAnalysisStream";
import { useAuth } from "../hooks/useAuth";
import { fetchStock, fetchStockHistory } from "../lib/api";
import { extractRealtime, normalizeBars, type StockDetailPayload } from "../types/stock";

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

  const quote = data ? extractRealtime(data as StockDetailPayload) : null;
  const bars = normalizeBars(historyRaw);
  const { steps, loading: aiLoading, error: aiError, start: startAi } = useAnalysisStream(symbol, market);

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

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link className="rounded-lg bg-zinc-800/40 px-3 py-1.5 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-colors hover:bg-zinc-800 hover:text-zinc-200" to="/app">← 操盘台</Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">
            {symbol}
            <span className="ml-2 text-base font-normal text-zinc-500">({market})</span>
          </h1>
        </div>
      </div>

      {isLoading && <Panel className="flex items-center gap-3 p-5"><div className="h-4 w-4 animate-ping rounded-full bg-emerald-500/40" /><p className="text-sm text-zinc-500">加载行情…</p></Panel>}
      {error && <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">加载失败: {error.message}</div>}

      {quote && <StockQuoteCard quote={quote} />}
      {symbol && <TradePlanPanel symbol={symbol} market={market} />}

      <AiInsightPanel symbol={symbol} market={market} steps={steps} loading={aiLoading} error={aiError} onStart={startAi} />

      {/* Chart */}
      <Panel className="p-5">
        <h3 className="mb-4 text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">近 120 日走势</h3>
        {historyLoading && <div className="flex items-center gap-3 text-sm text-zinc-500"><div className="h-3 w-3 animate-spin rounded-full border-2 border-zinc-600 border-t-zinc-400" />加载 K 线…</div>}
        {historyError && <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-sm text-amber-400">K 线加载失败: {historyError.message}</div>}
        {!historyLoading && !historyError && (
          <Suspense fallback={<div className="h-80 animate-pulse rounded-xl bg-zinc-800/40" />}>
            <PriceHistoryChart data={bars} />
          </Suspense>
        )}
      </Panel>

      {data?.indicators && Object.keys(data.indicators).length > 0 && (
        <Panel className="p-5">
          <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">技术指标</h3>
          <pre className="max-h-48 overflow-auto rounded-lg bg-zinc-800/40 p-3 font-mono text-[10px] text-zinc-400">{JSON.stringify(data.indicators, null, 2)}</pre>
        </Panel>
      )}

      <a className="inline-block rounded-lg bg-zinc-800/40 px-4 py-2 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-colors hover:bg-zinc-800 hover:text-zinc-200" href={`/stock/${encodeURIComponent(symbol)}?m=${market}`}>打开经典版详情</a>
    </div>
  );
}