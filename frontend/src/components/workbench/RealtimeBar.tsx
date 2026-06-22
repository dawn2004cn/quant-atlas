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
    <div className="flex items-center justify-between rounded-xl bg-zinc-900/30 px-5 py-2.5 ring-1 ring-zinc-800/40">
      <div className="flex items-center gap-3">
        <span className="relative flex h-2 w-2">
          <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${connected ? "bg-emerald-400" : ""}`} />
          <span className={`relative inline-flex h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-zinc-600"}`} />
        </span>
        <span className="text-xs font-medium text-zinc-400">
          实时行情 <span className="text-zinc-500">{connected ? "已连接" : "未连接"}</span>
        </span>
      </div>

      {error ? (
        <span className="text-xs text-rose-400">{error}</span>
      ) : lastQuote ? (
        <div className="flex items-center gap-3 text-xs">
          <span className="font-mono text-zinc-400">{lastQuote.symbol ?? ""}</span>
          <span className="font-mono tabular-nums text-zinc-200">
            {lastQuote.price != null ? `¥${lastQuote.price}` : ""}
          </span>
          {lastQuote.change_pct != null && (
            <span className={`font-mono tabular-nums font-semibold ${lastQuote.change_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {lastQuote.change_pct >= 0 ? "+" : ""}{lastQuote.change_pct}%
            </span>
          )}
        </div>
      ) : (
        <span className="text-xs text-zinc-600">等待推送…</span>
      )}

      {lastAiChunk?.symbol ? (
        <span className="text-xs text-sky-400">
          AI 流 {lastAiChunk.symbol}
          {aiStep ? ` · ${aiStep}` : ""}
        </span>
      ) : null}
    </div>
  );
}