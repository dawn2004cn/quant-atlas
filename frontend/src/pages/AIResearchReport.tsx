import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

const MARKETS = ["CN", "HK", "US"] as const;
const DEPTH_OPTIONS = [
  { value: "basic", label: "基础" },
  { value: "standard", label: "标准" },
  { value: "deep", label: "深度" },
] as const;

type ResearchReport = {
  symbol: string;
  market: string;
  depth: string;
  title: string;
  sections: Array<{ heading: string; content: string }>;
  disclaimer?: string;
  generated_at: string;
};

export function AIResearchReportPage() {
  const [symbol, setSymbol] = useState("");
  const [market, setMarket] = useState("CN");
  const [depth, setDepth] = useState("standard");
  const [submitted, setSubmitted] = useState(false);

  const { data, error, isLoading } = useSWR(
    submitted && symbol.trim()
      ? ["ai-research-report", symbol, market, depth]
      : null,
    () =>
      apiFetchV1<ResearchReport>("/ai/research-report", {
        method: "POST",
        body: JSON.stringify({
          symbol: symbol.trim().toUpperCase(),
          market,
          depth,
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
        <h1 className="text-2xl font-bold">AI 研究报告</h1>
        <p className="text-sm text-slate-500">生成专业的个股研究报告</p>
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
        <div>
          <label className="text-xs font-semibold text-slate-500">深度</label>
          <div className="mt-1 flex gap-1">
            {DEPTH_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`btn btn-sm ${depth === opt.value ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setDepth(opt.value)}
              >
                {opt.label}
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
            "生成报告"
          )}
        </button>
      </div>

      {error && <div className="alert alert-error">{error.message}</div>}
      {isLoading && <PageSkeleton rows={5} />}

      {!submitted && !isLoading && (
        <div className="glass-card flex flex-col items-center gap-3 p-8 text-center">
          <div className="text-4xl">📄</div>
          <p className="text-sm text-slate-400">
            输入标的代码并选择分析深度，生成专业研究报告
          </p>
        </div>
      )}

      {data && !isLoading && (
        <div className="glass-card space-y-4 p-4">
          <div className="border-b pb-3 dark:border-slate-700">
            <h2 className="text-xl font-bold">{data.title}</h2>
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-400">
              <span>{data.symbol}</span>
              <span>{data.market}</span>
              <span className="badge badge-ghost badge-xs">{data.depth}</span>
              <span>{new Date(data.generated_at).toLocaleString("zh-CN")}</span>
            </div>
          </div>

          {data.sections.map((section, idx) => (
            <div key={idx}>
              <h3 className="mb-2 text-sm font-bold text-brand">{section.heading}</h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{section.content}</p>
            </div>
          ))}

          {data.disclaimer && (
            <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700 dark:bg-amber-950/30 dark:text-amber-400">
              {data.disclaimer}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
