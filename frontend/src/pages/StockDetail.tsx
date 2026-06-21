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
  const { steps, loading: aiLoading, error: aiError, start: startAi } = useAnalysisStream(
    symbol,
    market,
  );

  if (authLoading) {
    return <div className="glass-card p-6">检查登录…</div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="glass-card p-6">
        <p>请先登录后查看个股详情。</p>
        <Link className="btn btn-primary mt-3" to="/login">
          登录
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link className="btn btn-ghost btn-sm" to="/">
          ← 操盘台
        </Link>
        <h1 className="text-2xl font-bold">
          {symbol}{" "}
          <span className="text-base font-normal text-slate-500">({market})</span>
        </h1>
      </div>

      {isLoading ? <div className="glass-card p-6">加载行情…</div> : null}
      {error ? (
        <div className="alert alert-error">加载失败：{error.message}</div>
      ) : null}
      {quote ? <StockQuoteCard quote={quote} /> : null}

      {symbol && <TradePlanPanel symbol={symbol} market={market} />}

      <AiInsightPanel
        symbol={symbol}
        market={market}
        steps={steps}
        loading={aiLoading}
        error={aiError}
        onStart={startAi}
      />

      <section className="glass-card p-6">
        <h3 className="mb-3 font-semibold">近 120 日走势</h3>
        {historyLoading ? <div className="text-sm text-slate-500">加载 K 线…</div> : null}
        {historyError ? (
          <div className="alert alert-warning text-sm">
            K 线加载失败：{historyError.message}
          </div>
        ) : null}
        {!historyLoading && !historyError ? (
          <Suspense fallback={<div className="h-80 animate-pulse rounded-xl bg-slate-200/50" />}>
            <PriceHistoryChart data={bars} />
          </Suspense>
        ) : null}
      </section>

      {data?.indicators && Object.keys(data.indicators).length > 0 ? (
        <section className="glass-card p-6">
          <h3 className="mb-2 font-semibold">技术指标</h3>
          <pre className="max-h-48 overflow-auto text-xs">
            {JSON.stringify(data.indicators, null, 2)}
          </pre>
        </section>
      ) : null}

      <a
        className="btn btn-outline btn-sm"
        href={`/stock/${encodeURIComponent(symbol)}?m=${market}`}
      >
        打开经典版详情
      </a>
    </div>
  );
}
