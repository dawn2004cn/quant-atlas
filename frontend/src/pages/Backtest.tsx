import { FormEvent, lazy, Suspense, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
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
    return data
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const row = item as { name?: string; id?: string };
          return row.name || row.id || "";
        }
        return "";
      })
      .filter(Boolean);
  }
  return ["MA"];
}

function buildGovernancePrefillPath(
  strategy: string,
  symbol: string,
  result: BacktestResult,
): string {
  const params = new URLSearchParams({
    strategy,
    symbol,
  });
  const sharpe = result.sharpe ?? result.sharpe_ratio;
  if (sharpe != null && sharpe !== "") {
    params.set("sharpe", String(sharpe));
  }
  const mlflowRunId = result.mlflow_run_id;
  if (typeof mlflowRunId === "string" && mlflowRunId) {
    params.set("mlflow_run_id", mlflowRunId);
  }
  return `/marketplace?${params.toString()}#governance`;
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
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [lastRun, setLastRun] = useState<{ strategy: string; symbol: string } | null>(
    null,
  );
  const [duelLoading, setDuelLoading] = useState(false);
  const [duelError, setDuelError] = useState<string | null>(null);
  const [duelResult, setDuelResult] = useState<BacktestCompareResult | null>(null);

  const { data: strategiesData } = useSWR("strategies", listStrategies);
  const { data: wizardData } = useSWR(
    tab === "preview" ? "wizard-templates" : null,
    fetchWizardTemplates,
  );

  const strategies = normalizeStrategies(strategiesData);
  const templates = wizardData?.templates ?? [];
  const equityCurve = useMemo(() => result ? extractEquityCurve(result) : [], [result]);
  const trades = useMemo(() => result ? extractTrades(result) : [], [result]);
  const metricCards = useMemo(() => result ? extractMetricCards(result) : [], [result]);

  async function onFullSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setLoadingHint(asyncMode ? "已提交异步任务，轮询结果中…" : null);
    setError(null);
    setResult(null);
    try {
      const data = await runBacktest(
        {
          symbol,
          strategy_name: strategy,
          start,
          end,
          initial_capital: capital,
        },
        asyncMode,
      );
      setResult(data);
      setLastRun({ strategy, symbol });
    } catch (err) {
      setError(err instanceof Error ? err.message : "回测失败");
    } finally {
      setLoading(false);
      setLoadingHint(null);
    }
  }

  async function onPreviewSubmit(event: FormEvent) {
    event.preventDefault();
    if (!templateId) {
      setError("请选择策略模板");
      return;
    }
    setLoading(true);
    setLoadingHint(asyncMode ? "已提交异步任务，轮询结果中…" : null);
    setError(null);
    setResult(null);
    try {
      const data = await previewStrategy(templateId, {}, previewSymbol);
      setResult(data as BacktestResult);
      setLastRun({ strategy: templateId, symbol: previewSymbol });
    } catch (err) {
      setError(err instanceof Error ? err.message : "预览失败");
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
      const strategies = Array.from(
        new Set([strategy, "MA", "RSI", "MACD"].filter(Boolean)),
      ).slice(0, 4);
      const data = await compareBacktests({
        symbol,
        strategies,
        start,
        end,
        initial_capital: capital,
      });
      setDuelResult(data);
    } catch (err) {
      setDuelError(err instanceof Error ? err.message : "策略对决失败");
    } finally {
      setDuelLoading(false);
    }
  }

  function formatPct(value: number | undefined) {
    if (value == null || Number.isNaN(value)) return "—";
    const pct = Math.abs(value) <= 1 ? value * 100 : value;
    return `${pct.toFixed(2)}%`;
  }

  const governanceLink =
    features.feature_alpha_marketplace && result && lastRun
      ? buildGovernancePrefillPath(lastRun.strategy, lastRun.symbol, result)
      : null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">策略回测</h1>
          <p className="text-sm text-slate-500">
            v2 <code>/api/v2/strategies/backtest</code> + Recharts 权益曲线
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className={`btn btn-sm ${tab === "full" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setTab("full")}
          >
            完整回测
          </button>
          <button
            type="button"
            className={`btn btn-sm ${tab === "preview" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setTab("preview")}
          >
            快速预览
          </button>
        </div>
      </div>

      {tab === "full" ? (
        <form className="glass-card space-y-4 p-6" onSubmit={onFullSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="form-control">
              <span className="label-text">标的代码</span>
              <input
                className="input input-bordered"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                required
              />
            </label>
            <label className="form-control">
              <span className="label-text">策略</span>
              <select
                className="select select-bordered"
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
              >
                {strategies.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-control">
              <span className="label-text">开始日期</span>
              <input
                type="date"
                className="input input-bordered"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </label>
            <label className="form-control">
              <span className="label-text">结束日期</span>
              <input
                type="date"
                className="input input-bordered"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </label>
            <label className="form-control">
              <span className="label-text">初始资金</span>
              <input
                type="number"
                className="input input-bordered"
                min={1000}
                step={1000}
                value={capital}
                onChange={(e) => setCapital(Number(e.target.value))}
                required
              />
            </label>
            <label className="label cursor-pointer justify-start gap-3 pt-8">
              <input
                type="checkbox"
                className="checkbox"
                checked={asyncMode}
                onChange={(e) => setAsyncMode(e.target.checked)}
              />
              <span className="label-text">异步任务（?async=1）</span>
            </label>
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "运行中…" : "运行回测"}
          </button>
        </form>
      ) : (
        <form className="glass-card space-y-4 p-6" onSubmit={onPreviewSubmit}>
          <label className="form-control">
            <span className="label-text">策略模板</span>
            <select
              className="select select-bordered"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              required
            >
              <option value="">选择模板…</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                  {t.is_recommended ? "（推荐）" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="form-control">
            <span className="label-text">预览标的</span>
            <input
              className="input input-bordered"
              value={previewSymbol}
              onChange={(e) => setPreviewSymbol(e.target.value)}
              required
            />
          </label>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "预览中…" : "快速预览"}
          </button>
        </form>
      )}

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loadingHint ? <div className="alert alert-info text-sm">{loadingHint}</div> : null}

      {result ? (
        <section className="glass-card space-y-4 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-semibold">回测结果</h2>
            {governanceLink ? (
              <Link className="btn btn-secondary btn-sm" to={governanceLink}>
                提交治理提案
              </Link>
            ) : null}
          </div>
          {typeof result.mlflow_run_id === "string" && result.mlflow_run_id ? (
            <p className="text-xs text-slate-500">
              MLflow run：<code>{result.mlflow_run_id}</code>
              {typeof result.mlflow_model_name === "string" && result.mlflow_model_name ? (
                <span className="ml-2">
                  模型 {result.mlflow_model_name}
                  {result.mlflow_model_version
                    ? ` v${String(result.mlflow_model_version)}`
                    : ""}
                </span>
              ) : null}
            </p>
          ) : null}
          {metricCards.length ? (
            <dl className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {metricCards.map((row) => (
                <div
                  key={row.label}
                  className="rounded-lg bg-slate-100/80 px-3 py-2 dark:bg-slate-800/80"
                >
                  <dt className="text-xs text-slate-500">{row.label}</dt>
                  <dd className="font-mono text-sm">{String(row.value)}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-slate-200/50" />}>
            <EquityCurveChart data={equityCurve} trades={trades} />
          </Suspense>
          {trades.length ? (
            <div className="overflow-x-auto rounded-lg border border-slate-200/80 dark:border-slate-700">
              <table className="table table-zebra table-sm">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>方向</th>
                    <th className="text-right">价格</th>
                    <th className="text-right">数量</th>
                    <th className="text-right">盈亏</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t, i) => (
                    <tr key={`${t.date}-${t.side}-${i}`}>
                      <td>{t.date}</td>
                      <td className={t.side === "buy" ? "text-emerald-600" : "text-rose-600"}>
                        {t.side === "buy" ? "买入" : "卖出"}
                      </td>
                      <td className="text-right font-mono">{t.price.toFixed(2)}</td>
                      <td className="text-right font-mono">{t.quantity ?? "—"}</td>
                      <td className="text-right font-mono">
                        {t.pnl != null ? t.pnl.toFixed(0) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <details className="text-sm">
            <summary className="cursor-pointer text-slate-500">原始 JSON</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-900/90 p-3 text-xs text-slate-100">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </section>
      ) : null}

      <section className="glass-card space-y-3 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold">策略对决</h2>
            <p className="text-sm text-slate-500">
              同一标的与区间下并行回测多个策略，按总收益排名
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={duelLoading}
            onClick={onStrategyDuel}
          >
            {duelLoading ? "对决中…" : "开始对决"}
          </button>
        </div>
        {duelError ? <div className="alert alert-error text-sm">{duelError}</div> : null}
        {duelResult?.comparisons?.length ? (
          <div className="overflow-x-auto rounded-lg border border-slate-200/80 dark:border-slate-700">
            <table className="table table-zebra table-sm">
              <thead>
                <tr>
                  <th>策略</th>
                  <th className="text-right">总收益</th>
                  <th className="text-right">年化</th>
                  <th className="text-right">夏普</th>
                  <th className="text-right">最大回撤</th>
                </tr>
              </thead>
              <tbody>
                {duelResult.comparisons.map((row) => (
                  <tr
                    key={row.strategy_name}
                    className={
                      row.strategy_name === duelResult.winner
                        ? "bg-emerald-500/10"
                        : undefined
                    }
                  >
                    <td>
                      {row.strategy_name === duelResult.winner ? "🏆 " : ""}
                      {row.strategy_name}
                    </td>
                    {row.status === "error" ? (
                      <td colSpan={4} className="text-rose-600">
                        {row.error ?? "回测失败"}
                      </td>
                    ) : (
                      <>
                        <td className="text-right font-mono">{formatPct(row.total_return)}</td>
                        <td className="text-right font-mono">{formatPct(row.annual_return)}</td>
                        <td className="text-right font-mono">
                          {row.sharpe != null ? row.sharpe.toFixed(2) : "—"}
                        </td>
                        <td className="text-right font-mono text-rose-600">
                          {formatPct(row.max_drawdown)}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <div className="flex flex-wrap gap-3">
        <a className="btn btn-outline btn-sm" href="/strategy-wizard">
          经典策略向导
        </a>
        <a className="btn btn-outline btn-sm" href="/quant-lab">
          量化实验室
        </a>
      </div>
    </div>
  );
}
