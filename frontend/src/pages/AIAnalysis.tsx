import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

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
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">AI 分析</h1>
        <p className="text-sm text-slate-500">输入标的代码，获取 AI 多维度分析报告</p>
      </div>

      <div className="glass-card flex flex-wrap items-end gap-3 p-4">
        <div>
          <label className="text-xs font-semibold text-slate-500">标的</label>
          <input
            type="text"
            className="input input-bordered input-sm mt-1 w-40"
            placeholder="600519"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500">市场</label>
          <div className="mt-1 flex gap-1">
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
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={handleSubmit}
          disabled={!symbol.trim() || isLoading}
        >
          {isLoading ? (
            <span className="loading loading-spinner loading-sm" />
          ) : (
            "开始分析"
          )}
        </button>
      </div>

      {error && <div className="alert alert-error">{error.message}</div>}
      {isLoading && <PageSkeleton rows={4} />}

      {!submitted && !isLoading && (
        <div className="glass-card flex flex-col items-center gap-3 p-8 text-center">
          <div className="text-4xl">📊</div>
          <p className="text-sm text-slate-400">
            输入标的代码并选择市场，开始 AI 分析
          </p>
        </div>
      )}

      {data && !isLoading && (
        <div className="glass-card space-y-4 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold">
                {data.symbol}
                <span className="ml-2 text-xs font-normal text-slate-500">{data.market}</span>
              </h2>
              <p className="text-xs text-slate-400">
                分析时间：{new Date(data.generated_at).toLocaleString("zh-CN")}
              </p>
            </div>
            {data.recommendation && (
              <span className="badge badge-lg badge-primary">{data.recommendation}</span>
            )}
          </div>

          {data.summary && (
            <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
              <h3 className="mb-1 text-xs font-bold text-slate-500">摘要</h3>
              <p className="text-sm">{data.summary}</p>
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            {data.technical && (
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                <h3 className="mb-1 text-xs font-bold text-slate-500">技术分析</h3>
                <p className="text-sm whitespace-pre-wrap">{data.technical}</p>
              </div>
            )}
            {data.fundamental && (
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                <h3 className="mb-1 text-xs font-bold text-slate-500">基本面</h3>
                <p className="text-sm whitespace-pre-wrap">{data.fundamental}</p>
              </div>
            )}
            {data.sentiment && (
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                <h3 className="mb-1 text-xs font-bold text-slate-500">市场情绪</h3>
                <p className="text-sm whitespace-pre-wrap">{data.sentiment}</p>
              </div>
            )}
            {data.risk && (
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                <h3 className="mb-1 text-xs font-bold text-slate-500">风险提示</h3>
                <p className="text-sm whitespace-pre-wrap">{data.risk}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
