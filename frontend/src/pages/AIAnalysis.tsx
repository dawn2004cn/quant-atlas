import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { CoreNextSteps, CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

const MARKETS = ["CN", "HK", "US"] as const;

type AnalysisResult = {
  symbol: string;
  market: string;
  summary: string;
  technical?: string;
  fundamental?: string;
  sentiment?: string;
  risk?: string;
  recommendation?: string;
  generated_at: string;
};

export function AIAnalysisPage() {
  const [symbol, setSymbol] = useState("");
  const [market, setMarket] = useState<string>("CN");
  const [submitted, setSubmitted] = useState(false);

  const { data, error, isLoading } = useSWR(
    submitted && symbol.trim()
      ? ["ai-analysis", symbol, market]
      : null,
    () =>
      apiFetchV1<AnalysisResult>("/ai/analysis", {
        method: "POST",
        body: JSON.stringify({
          symbol: symbol.trim().toUpperCase(),
          market,
        }),
      }),
  );

  const handleSubmit = () => {
    if (!symbol.trim()) return;
    setSubmitted(true);
  };

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <CoreWorkflowStrip />
      <PageQuickNav items={QUICK_NAV_PRESETS.aiAnalysis} />
      <div>
        <h1 className="text-2xl font-bold">AI 诊股</h1>
        <p className="text-sm text-zinc-500">多智能体证据链 — 技术、基本面、情绪与风险综合研判</p>
      </div>

      <Panel className="flex flex-wrap items-end gap-3 p-4">
        <div>
          <label className="text-xs font-semibold text-zinc-500">标的</label>
          <input
            type="text"
            className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20 mt-1 w-40"
            placeholder="600519"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-zinc-500">市场</label>
          <div className="mt-1 flex gap-1">
            {MARKETS.map((m) => (
              <button
                key={m}
                type="button"
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${market === m ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30 hover:bg-emerald-500/20" : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"}`}
                onClick={() => setMarket(m)}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
        <button
          type="button"
          className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30 transition-colors hover:bg-emerald-500/20"
          onClick={handleSubmit}
          disabled={!symbol.trim() || isLoading}
        >
          {isLoading ? (
            <span className="loading loading-spinner loading-sm" />
          ) : (
            "开始分析"
          )}
        </button>
      </Panel>

      {error && <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">{error.message}</div>}
      {isLoading && <PageSkeleton rows={4} />}

      {!submitted && !isLoading && (
        <Panel className="flex flex-col items-center gap-3 p-8 text-center">
          <div className="text-4xl">📊</div>
          <p className="text-sm text-zinc-400">
            输入标的代码并选择市场，开始 AI 分析
          </p>
        </Panel>
      )}

      {data && !isLoading && (
        <Panel className="space-y-4 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold">
                {data.symbol}
                <span className="ml-2 text-xs font-normal text-zinc-500">{data.market}</span>
              </h2>
              <p className="text-xs text-zinc-400">
                分析时间：{new Date(data.generated_at).toLocaleString("zh-CN")}
              </p>
            </div>
            {data.recommendation && (
              <span className="rounded px-3 py-1.5 font-mono text-xs font-semibold bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30">{data.recommendation}</span>
            )}
          </div>

          {data.summary && (
            <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
              <h3 className="mb-1 text-xs font-bold text-zinc-500">摘要</h3>
              <p className="text-sm">{data.summary}</p>
            </div>
          )}

          <CoreNextSteps symbol={data.symbol} />

          <div className="grid gap-3 md:grid-cols-2">
            {data.technical && (
              <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
                <h3 className="mb-1 text-xs font-bold text-zinc-500">技术分析</h3>
                <p className="text-sm whitespace-pre-wrap">{data.technical}</p>
              </div>
            )}
            {data.fundamental && (
              <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
                <h3 className="mb-1 text-xs font-bold text-zinc-500">基本面</h3>
                <p className="text-sm whitespace-pre-wrap">{data.fundamental}</p>
              </div>
            )}
            {data.sentiment && (
              <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
                <h3 className="mb-1 text-xs font-bold text-zinc-500">市场情绪</h3>
                <p className="text-sm whitespace-pre-wrap">{data.sentiment}</p>
              </div>
            )}
            {data.risk && (
              <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
                <h3 className="mb-1 text-xs font-bold text-zinc-500">风险提示</h3>
                <p className="text-sm whitespace-pre-wrap">{data.risk}</p>
              </div>
            )}
          </div>
        </Panel>
      )}
    </div>
  );
}
