import { useState } from "react";
import useSWR from "swr";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_AI_RESEARCH_REPORT } from "../lib/demoCatalog";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

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
  const [symbol, setSymbol] = useState("600519");
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
    <div className="mx-auto max-w-[1400px] space-y-5">
      <CoreWorkflowStrip />
      <PageQuickNav items={QUICK_NAV_PRESETS.aiResearchReport} />
      <div>
        <h1 className="text-2xl font-bold">AI 研究报告</h1>
        <p className="text-sm text-zinc-500">生成专业的个股研究报告</p>
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
        <div>
          <label className="text-xs font-semibold text-zinc-500">深度</label>
          <div className="mt-1 flex gap-1">
            {DEPTH_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${depth === opt.value ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30 hover:bg-emerald-500/20" : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"}`}
                onClick={() => setDepth(opt.value)}
              >
                {opt.label}
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
            "生成报告"
          )}
        </button>
      </Panel>

      {isLoading && <PageSkeleton rows={5} />}

      {(() => {
        const isDemo = !isLoading && (Boolean(error) || !data);
        const view = (!isLoading && data) ? data : DEMO_AI_RESEARCH_REPORT;
        if (isLoading) return null;
        return (
        <Panel className="space-y-4 p-4">
          <DemoBanner show={isDemo || !submitted} />
          <div className="border-b pb-3 dark:border-zinc-700">
            <h2 className="text-xl font-bold">{view.title}</h2>
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-400">
              <span>{view.symbol}</span>
              <span>{view.market}</span>
              <span className="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold bg-zinc-800/60 text-zinc-400">{view.depth}</span>
              <span>{new Date(view.generated_at).toLocaleString("zh-CN")}</span>
            </div>
          </div>

          {view.sections.map((section, idx) => (
            <div key={idx}>
              <h3 className="mb-2 text-sm font-bold text-brand">{section.heading}</h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{section.content}</p>
            </div>
          ))}

          {view.disclaimer && (
            <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700 dark:bg-amber-950/30 dark:text-amber-400">
              {view.disclaimer}
            </div>
          )}
        </Panel>
        );
      })()}
    </div>
  );
}
