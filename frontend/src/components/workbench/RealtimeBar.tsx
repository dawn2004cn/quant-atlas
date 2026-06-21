import type { AiAnalysisChunk, QuoteUpdate } from "../../hooks/useRealtime";

export function RealtimeBar({
  connected,
  error,
  lastQuote,
  lastAiChunk,
}: {
  connected: boolean;
  error: string | null;
  lastQuote: QuoteUpdate | null;
  lastAiChunk?: AiAnalysisChunk | null;
}) {
  const aiStep =
    lastAiChunk?.chunk && typeof lastAiChunk.chunk === "object"
      ? String(
          (lastAiChunk.chunk as { step?: string }).step ??
            (lastAiChunk.chunk as { type?: string }).type ??
            "",
        )
      : "";

  return (
    <div className="glass-card flex flex-wrap items-center justify-between gap-3 px-4 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            connected ? "bg-emerald-500" : "bg-slate-400"
          }`}
          aria-hidden
        />
        <span className="font-medium">
          实时行情 {connected ? "已连接" : "未连接"}
        </span>
      </div>
      {error ? (
        <span className="text-rose-600">{error}</span>
      ) : lastQuote ? (
        <span className="text-slate-600 dark:text-slate-300">
          {lastQuote.symbol ? `${lastQuote.symbol} ` : ""}
          {lastQuote.price != null ? `¥${lastQuote.price}` : ""}
          {lastQuote.change_pct != null ? (
            <span
              className={
                lastQuote.change_pct >= 0 ? "text-emerald-600" : "text-rose-600"
              }
            >
              {" "}
              {lastQuote.change_pct >= 0 ? "+" : ""}
              {lastQuote.change_pct}%
            </span>
          ) : null}
        </span>
      ) : (
        <span className="text-slate-500">等待推送…</span>
      )}
      {lastAiChunk?.symbol ? (
        <span className="text-xs text-violet-600 dark:text-violet-300">
          AI 流 {lastAiChunk.symbol}
          {aiStep ? ` · ${aiStep}` : ""}
        </span>
      ) : null}
    </div>
  );
}
