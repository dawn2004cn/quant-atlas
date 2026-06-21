import type { AnalysisChunk } from "../../types/mlflow";

function labelFor(chunk: AnalysisChunk) {
  if (chunk.event === "step") {
    return `${chunk.phase ?? "step"} · ${chunk.status ?? ""}`;
  }
  if (chunk.event === "evidence") {
    return chunk.title || chunk.source || "证据";
  }
  if (chunk.event === "notice") {
    return chunk.message || "提示";
  }
  if (chunk.event === "complete") {
    return "分析完成";
  }
  return chunk.event || "事件";
}

export function AiInsightPanel({
  symbol,
  market,
  steps,
  loading,
  error,
  onStart,
}: {
  symbol: string;
  market: string;
  steps: AnalysisChunk[];
  loading: boolean;
  error: string | null;
  onStart: () => void;
}) {
  const complete = steps.find((s) => s.event === "complete");
  const decision = complete?.data?.decision as Record<string, unknown> | undefined;

  return (
    <section className="glass-card p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold">AI 诊股（流式）</h3>
          <p className="text-sm text-slate-500">
            SSE <code>/api/v1/ai/analyze/stream</code>
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={loading}
          onClick={onStart}
        >
          {loading ? "分析中…" : "开始分析"}
        </button>
      </div>

      {error ? <div className="alert alert-warning mt-3 text-sm">{error}</div> : null}

      {decision ? (
        <div className="mt-4 rounded-xl bg-violet-500/10 p-4 text-sm">
          <div className="font-semibold">
            立场：{String(decision.stance ?? decision.action ?? "—")}
          </div>
          {decision.summary ? (
            <p className="mt-2 text-slate-600 dark:text-slate-300">
              {String(decision.summary)}
            </p>
          ) : null}
        </div>
      ) : null}

      {steps.length > 0 ? (
        <ol className="mt-4 max-h-64 space-y-2 overflow-y-auto text-sm">
          {steps.map((chunk, index) => (
            <li
              key={`${chunk.ts ?? index}-${chunk.event}`}
              className="rounded-lg border border-slate-200/80 px-3 py-2 dark:border-slate-700"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{labelFor(chunk)}</span>
                <span className="text-xs text-slate-400">{chunk.ts?.slice(11, 19)}</span>
              </div>
              {chunk.message ? (
                <p className="mt-1 text-slate-500">{chunk.message}</p>
              ) : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-4 text-sm text-slate-500">
          点击「开始分析」获取 {symbol} ({market}) 的实时推理步骤。
        </p>
      )}

      <a
        className="btn btn-ghost btn-xs mt-4"
        href={`/ai-analysis?symbol=${encodeURIComponent(symbol)}&market=${market}`}
      >
        打开经典版 AI 诊股
      </a>
    </section>
  );
}
