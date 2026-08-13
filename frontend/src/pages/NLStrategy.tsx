import { useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_NL_STRATEGY } from "../lib/demoCatalog";

type NLStrategyResult = {
  task_id?: string;
  status: string;
  symbol: string;
  strategy_name: string;
  strategy_description: string;
  params: Record<string, unknown>;
  backtest_metrics?: {
    total_return_pct: number;
    annual_return_pct: number;
    sharpe: number;
    max_drawdown_pct: number;
  };
  errors?: string[];
};

export function NLStrategyPage() {
  const [mode, setMode] = useState<"v1" | "v2">("v1");
  const [symbol, setSymbol] = useState("600519");
  const [prompt, setPrompt] = useState("当 5 日均线上穿 20 日均线时买入，跌破时卖出");
  const [submitted, setSubmitted] = useState(false);

  const { data, error, isLoading, mutate } = useSWR(
    submitted && prompt ? ["nl-strategy", mode, symbol, prompt] : null,
    () => apiFetchV1<NLStrategyResult>(mode === "v1" ? "/nl/strategy" : "/nl/strategy/v2", {
      method: "POST",
      body: JSON.stringify({ symbol: symbol || "600519", prompt }),
    }),
  );

  const handleSubmit = () => {
    if (!prompt.trim()) return;
    setSubmitted(true);
    mutate();
  };

  const isDemo = !submitted || Boolean(error) || (!isLoading && !data);
  const view = (!isLoading && data) ? data : DEMO_NL_STRATEGY;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.nlStrategy} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">自然语言策略</h1>
          <p className="text-sm text-slate-500">用中文描述交易策略，AI 自动生成并回测</p>
          <DemoBanner show={isDemo} />
        </div>
        <div className="tabs tabs-box">
          <button type="button" className={`tab ${mode === "v1" ? "tab-active" : ""}`} onClick={() => setMode("v1")}>V1</button>
          <button type="button" className={`tab ${mode === "v2" ? "tab-active" : ""}`} onClick={() => setMode("v2")}>V2</button>
        </div>
      </div>

      <div className="glass-card space-y-4 p-4">
        <div>
          <label className="text-xs font-semibold text-slate-500">标的（可选，默认为 600519）</label>
          <input type="text" className="input input-bordered input-sm mt-1 w-full max-w-xs" placeholder="600519" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500">策略描述</label>
          <textarea
            className="textarea textarea-bordered mt-1 w-full"
            rows={4}
            placeholder='例如："当 5 日均线上穿 20 日均线时买入，跌破时卖出，每次交易 1000 股"'
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>
        <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={!prompt.trim() || isLoading}>
          {isLoading ? "生成中..." : "生成策略"}
        </button>
      </div>

      {isLoading && <PageSkeleton rows={3} />}

      {!isLoading && (
        <section className="glass-card space-y-4 p-4">
          <div className="rounded-xl bg-emerald-50 p-3 dark:bg-emerald-950/30">
            <div className="text-sm font-bold">{view.strategy_name}</div>
            <p className="mt-1 text-xs text-slate-600">{view.strategy_description}</p>
          </div>

          {view.backtest_metrics && (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                <div className="text-xs text-slate-500">总收益</div>
                <div className={`text-lg font-bold ${view.backtest_metrics.total_return_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {view.backtest_metrics.total_return_pct.toFixed(2)}%
                </div>
              </div>
              <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                <div className="text-xs text-slate-500">年化收益</div>
                <div className="text-lg font-bold">{view.backtest_metrics.annual_return_pct.toFixed(2)}%</div>
              </div>
              <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                <div className="text-xs text-slate-500">夏普比</div>
                <div className="text-lg font-bold">{view.backtest_metrics.sharpe.toFixed(2)}</div>
              </div>
              <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                <div className="text-xs text-slate-500">最大回撤</div>
                <div className="text-lg font-bold text-rose-600">{view.backtest_metrics.max_drawdown_pct.toFixed(2)}%</div>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
