import { FormEvent, lazy, Suspense, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { CoreNextSteps, CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { AsyncProgressBar } from "../components/PageSkeleton";
import { usePlatformFeatures } from "../hooks/usePlatformFeatures";
import {
  extractEquityCurve,
  extractMetricCards,
  extractTrades,
} from "../lib/backtestMetrics";
import {
  fetchWizardTemplates,
  listStrategies,
  compareBacktests,
  previewStrategy,
  runBacktest,
} from "../lib/api";
import { DemoBanner } from "../components/DemoBanner";
import { DEMO_BACKTEST } from "../lib/demoCatalog";
import type { BacktestCompareResult, BacktestResult } from "../types/backtest";

const EquityCurveChart = lazy(() =>
  import("../components/charts/EquityCurveChart").then((mod) => ({
    default: mod.EquityCurveChart,
  })),
);

type Tab = "full" | "preview";

function defaultDates() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(end.getFullYear() - 1);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { start: fmt(start), end: fmt(end) };
}

function normalizeStrategies(data: unknown): string[] {
  if (Array.isArray(data)) {
    return data.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object") {
        const row = item as { name?: string; id?: string };
        return row.name || row.id || "";
      }
      return "";
    }).filter(Boolean);
  }
  return ["MA"];
}

function buildGovernancePrefillPath(strategy: string, symbol: string, result: BacktestResult): string {
  const params = new URLSearchParams({ strategy, symbol });
  const sharpe = result.sharpe ?? result.sharpe_ratio;
  if (sharpe != null && sharpe !== "") params.set("sharpe", String(sharpe));
  const mlflowRunId = result.mlflow_run_id;
  if (typeof mlflowRunId === "string" && mlflowRunId) params.set("mlflow_run_id", mlflowRunId);
  return `/marketplace?${params.toString()}#governance`;
}

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

function fmtPctVal(v: number | undefined) {
  if (v == null || Number.isNaN(v)) return "—";
  const pct = Math.abs(v) <= 1 ? v * 100 : v;
  return `${pct.toFixed(2)}%`;
}

function pctClass(v: number | undefined | null) {
  if (v == null) return "text-zinc-400";
  return Number(v) >= 0 ? "text-emerald-400" : "text-rose-400";
}

export function BacktestPage() {
  const dates = useMemo(() => defaultDates(), []);
  const { features } = usePlatformFeatures();
  const [tab, setTab] = useState<Tab>("full");

  const [symbol, setSymbol] = useState("600519");
  const [strategy, setStrategy] = useState("MA");
  const [start, setStart] = useState(dates.start);
  const [end, setEnd] = useState(dates.end);
  const [capital, setCapital] = useState(100_000);
  const [asyncMode, setAsyncMode] = useState(false);

  const [templateId, setTemplateId] = useState("");
  const [previewSymbol, setPreviewSymbol] = useState("600519");

  const [loading, setLoading] = useState(false);
  const [loadingHint, setLoadingHint] = useState<string | null>(null);
  const [asyncTaskId, setAsyncTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(DEMO_BACKTEST as BacktestResult);
  const [isDemo, setIsDemo] = useState(true);
  const [lastRun, setLastRun] = useState<{ strategy: string; symbol: string } | null>(null);
  const [duelLoading, setDuelLoading] = useState(false);
  const [duelError, setDuelError] = useState<string | null>(null);
  const [duelResult, setDuelResult] = useState<BacktestCompareResult | null>(null);

  const { data: strategiesData } = useSWR("strategies", listStrategies);
  const { data: wizardData } = useSWR(tab === "preview" ? "wizard-templates" : null, fetchWizardTemplates);

  const strategies = normalizeStrategies(strategiesData);
  const templates = wizardData?.templates ?? [];
  const equityCurve = useMemo(() => result ? extractEquityCurve(result) : [], [result]);
  const trades = useMemo(() => result ? extractTrades(result) : [], [result]);
  const metricCards = useMemo(() => result ? extractMetricCards(result) : [], [result]);

  async function onFullSubmit(event: FormEvent) {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setAsyncTaskId(null);
    setLoadingHint(asyncMode ? "已提交异步任务，轮询结果中…" : null);
    setError(null);
    try {
      const data = await runBacktest(
        { symbol, strategy_name: strategy, start, end, initial_capital: capital },
        asyncMode,
        (progress) => {
          setAsyncTaskId(progress.taskId);
          const pct = progress.maxAttempts
            ? Math.min(99, Math.round((progress.attempt / progress.maxAttempts) * 100))
            : 0;
          setLoadingHint(
            `异步回测 ${progress.state || "PENDING"} · ${progress.attempt}/${progress.maxAttempts}（约 ${pct}%）`,
          );
        },
      );
      setResult(data);
      setIsDemo(false);
      setLastRun({ strategy, symbol });
    } catch (err) {
      setError(err instanceof Error ? err.message : "回测失败");
      setResult(DEMO_BACKTEST as BacktestResult);
      setIsDemo(true);
    } finally {
      setLoading(false);
      setLoadingHint(null);
    }
  }

  async function onPreviewSubmit(event: FormEvent) {
    event.preventDefault();
    if (loading) return;
    if (!templateId) { setError("请选择策略模板"); return; }
    setLoading(true);
    setLoadingHint(null);
    setError(null);
    try {
      const data = await previewStrategy(templateId, {}, previewSymbol);
      setResult(data as BacktestResult);
      setIsDemo(false);
      setLastRun({ strategy: templateId, symbol: previewSymbol });
    } catch (err) {
      setError(err instanceof Error ? err.message : "预览失败");
      setResult(DEMO_BACKTEST as BacktestResult);
      setIsDemo(true);
    } finally {
      setLoading(false);
      setLoadingHint(null);
    }
  }

  async function onStrategyDuel() {
    setDuelLoading(true);
    setDuelError(null);
    setDuelResult(null);
    try {
      const strategies = Array.from(new Set([strategy, "MA", "RSI", "MACD"].filter(Boolean))).slice(0, 4);
      const data = await compareBacktests({ symbol, strategies, start, end, initial_capital: capital });
      setDuelResult(data);
    } catch (err) {
      setDuelError(err instanceof Error ? err.message : "策略对决失败");
    } finally {
      setDuelLoading(false);
    }
  }

  const governanceLink = features.feature_alpha_marketplace && result && lastRun
    ? buildGovernancePrefillPath(lastRun.strategy, lastRun.symbol, result) : null;

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.backtest} />
      <CoreWorkflowStrip />
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Backtest Hub</div>
        <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">策略回测中心</h1>
        <p className="mt-1 text-sm text-zinc-500">历史回测、绩效指标与净值曲线</p>
        <DemoBanner show={isDemo} />
      </div>

      {/* Tab switch */}
      <div className="flex gap-px rounded-lg bg-zinc-800/60 p-0.5 w-fit">
        {(["full" as const, "preview" as const]).map((t) => (
          <button key={t} type="button" onClick={() => setTab(t)}
            className={`rounded-md px-4 py-1.5 text-xs font-medium transition-all ${
              tab === t ? "bg-zinc-800 text-zinc-200 shadow-sm" : "text-zinc-500 hover:text-zinc-300"
            }`}
          >{t === "full" ? "完整回测" : "快速预览"}</button>
        ))}
      </div>

      {/* Form */}
      <Panel className="p-5">
        {tab === "full" ? (
          <form className="space-y-4" onSubmit={onFullSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">标的代码</label>
                <input className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">策略</label>
                <select className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                  {strategies.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">开始日期</label>
                <input type="date" className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20" value={start} onChange={(e) => setStart(e.target.value)} required />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">结束日期</label>
                <input type="date" className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20" value={end} onChange={(e) => setEnd(e.target.value)} required />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">初始资金</label>
                <input type="number" className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20" min={1000} step={1000} value={capital} onChange={(e) => setCapital(Number(e.target.value))} required />
              </div>
              <div className="flex items-center gap-3 pt-6">
                <input type="checkbox" id="async" className="h-4 w-4 rounded border-zinc-700 bg-zinc-800 text-emerald-500 focus:ring-emerald-500/30" checked={asyncMode} onChange={(e) => setAsyncMode(e.target.checked)} />
                <label htmlFor="async" className="text-xs text-zinc-400">异步任务 (?async=1)</label>
              </div>
            </div>
            <button type="submit" disabled={loading}
              className="rounded-lg bg-emerald-500/15 px-5 py-2 text-sm font-semibold text-emerald-400 ring-1 ring-emerald-500/30 transition-all hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >{loading ? "运行中…" : "运行回测"}</button>
          </form>
        ) : (
          <form className="space-y-4" onSubmit={onPreviewSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">策略模板</label>
                <select className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20" value={templateId} onChange={(e) => setTemplateId(e.target.value)} required>
                  <option value="">选择模板…</option>
                  {templates.map((t) => <option key={t.id} value={t.id}>{t.name}{t.is_recommended ? "（推荐）" : ""}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">预览标的</label>
                <input className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20" value={previewSymbol} onChange={(e) => setPreviewSymbol(e.target.value)} required />
              </div>
            </div>
            <button type="submit" disabled={loading}
              className="rounded-lg bg-emerald-500/15 px-5 py-2 text-sm font-semibold text-emerald-400 ring-1 ring-emerald-500/30 transition-all hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >{loading ? "预览中…" : "快速预览"}</button>
          </form>
        )}
      </Panel>

      {error && <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">{error}</div>}
      {loadingHint && (
        <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-sm text-sky-400">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>{loadingHint}</span>
            {asyncTaskId ? (
              <div className="flex flex-wrap gap-2">
                <Link
                  className="rounded-lg bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-300 ring-1 ring-sky-500/30 hover:bg-sky-500/20"
                  to={`/task/${encodeURIComponent(asyncTaskId)}`}
                >
                  任务详情
                </Link>
                <Link
                  className="rounded-lg bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-300 ring-1 ring-sky-500/30 hover:bg-sky-500/20"
                  to={`/task-center?task_id=${encodeURIComponent(asyncTaskId)}`}
                >
                  打开任务中心
                </Link>
              </div>
            ) : null}
          </div>
          {loading ? (
            <div className="mt-3">
              <AsyncProgressBar label="异步回测" indeterminate />
            </div>
          ) : null}
          {asyncTaskId ? (
            <p className="mt-2 font-mono text-[10px] text-sky-500/80">task_id: {asyncTaskId}</p>
          ) : null}
        </div>
      )}

      {/* Results */}
      {result && (
        <Panel className="space-y-5 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-bold text-zinc-200">回测结果</h2>
            {governanceLink && <Link className="rounded-lg bg-zinc-800/60 px-3 py-1.5 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-colors hover:bg-zinc-800 hover:text-zinc-200" to={governanceLink}>提交治理提案</Link>}
          </div>
          {typeof result.mlflow_run_id === "string" && result.mlflow_run_id && (
            <p className="text-[10px] font-mono text-zinc-600">
              MLflow run: <span className="text-zinc-400">{result.mlflow_run_id}</span>
              {typeof result.mlflow_model_name === "string" && result.mlflow_model_name && (
                <span className="ml-2">模型 {result.mlflow_model_name}{result.mlflow_model_version ? ` v${String(result.mlflow_model_version)}` : ""}</span>
              )}
            </p>
          )}
          {metricCards.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {metricCards.map((row) => (
                <div key={row.label} className="rounded-lg bg-zinc-800/40 px-3 py-2.5">
                  <div className="text-[10px] font-mono uppercase text-zinc-500">{row.label}</div>
                  <div className="font-mono text-sm font-semibold tabular-nums text-zinc-200">{String(row.value)}</div>
                </div>
              ))}
            </div>
          )}
          <CoreNextSteps symbol={lastRun?.symbol} />
          <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-zinc-800/40" />}>
            <EquityCurveChart data={equityCurve} trades={trades} />
          </Suspense>
          {trades.length > 0 && (
            <div className="overflow-x-auto rounded-lg ring-1 ring-zinc-800/40">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800/60 text-left text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
                    <th className="px-4 py-2.5">日期</th>
                    <th className="px-4 py-2.5">方向</th>
                    <th className="px-4 py-2.5 text-right">价格</th>
                    <th className="px-4 py-2.5 text-right">数量</th>
                    <th className="px-4 py-2.5 text-right">盈亏</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/30">
                  {trades.map((t, i) => (
                    <tr key={`${t.date}-${t.side}-${i}`} className="transition-colors hover:bg-zinc-800/30">
                      <td className="px-4 py-2 font-mono text-xs text-zinc-400">{t.date}</td>
                      <td className={`px-4 py-2 font-mono text-xs font-semibold ${t.side === "buy" ? "text-emerald-400" : "text-rose-400"}`}>{t.side === "buy" ? "买入" : "卖出"}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums text-zinc-300">{t.price.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums text-zinc-300">{t.quantity ?? "—"}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums text-zinc-300">{t.pnl != null ? t.pnl.toFixed(0) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <details className="text-xs">
            <summary className="cursor-pointer text-zinc-500">原始 JSON</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-zinc-900/90 p-3 font-mono text-[10px] text-zinc-300">{JSON.stringify(result, null, 2)}</pre>
          </details>
        </Panel>
      )}

      {/* Duel */}
      <Panel className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-zinc-200">策略对决</h2>
            <p className="text-xs text-zinc-500">同一标的与区间下并行回测多个策略，按总收益排名</p>
          </div>
          <button type="button" disabled={duelLoading} onClick={onStrategyDuel}
            className="rounded-lg bg-zinc-800/60 px-4 py-1.5 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-all hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-50"
          >{duelLoading ? "对决中…" : "开始对决"}</button>
        </div>
        {duelError && <div className="mt-4 rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">{duelError}</div>}
        {duelResult?.comparisons?.length ? (
          <div className="mt-4 overflow-x-auto rounded-lg ring-1 ring-zinc-800/40">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800/60 text-left text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
                  <th className="px-4 py-2.5">策略</th>
                  <th className="px-4 py-2.5 text-right">总收益</th>
                  <th className="px-4 py-2.5 text-right">年化</th>
                  <th className="px-4 py-2.5 text-right">夏普</th>
                  <th className="px-4 py-2.5 text-right">最大回撤</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/30">
                {duelResult.comparisons.map((row) => (
                  <tr key={row.strategy_name} className={`transition-colors hover:bg-zinc-800/30 ${row.strategy_name === duelResult.winner ? "bg-emerald-500/8" : ""}`}>
                    <td className="px-4 py-2.5 font-medium text-zinc-200">
                      {row.strategy_name === duelResult.winner ? <span className="mr-1">🏆</span> : null}
                      {row.strategy_name}
                    </td>
                    {row.status === "error" ? (
                      <td colSpan={4} className="px-4 py-2.5 text-rose-400">{row.error ?? "回测失败"}</td>
                    ) : (
                      <>
                        <td className={`px-4 py-2.5 text-right font-mono tabular-nums font-semibold ${pctClass(row.total_return)}`}>{fmtPctVal(row.total_return)}</td>
                        <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-300">{fmtPctVal(row.annual_return)}</td>
                        <td className="px-4 py-2.5 text-right font-mono tabular-nums text-zinc-300">{row.sharpe != null ? row.sharpe.toFixed(2) : "—"}</td>
                        <td className="px-4 py-2.5 text-right font-mono tabular-nums text-rose-400">{fmtPctVal(row.max_drawdown)}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>

      <div className="flex flex-wrap gap-3">
        <a className="rounded-lg bg-zinc-800/40 px-4 py-2 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-colors hover:bg-zinc-800 hover:text-zinc-200" href="/strategy-wizard">经典策略向导</a>
        <a className="rounded-lg bg-zinc-800/40 px-4 py-2 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-colors hover:bg-zinc-800 hover:text-zinc-200" href="/quant-lab">量化实验室</a>
      </div>
    </div>
  );
}