import { useState } from "react";
import useSWR from "swr";
import { Link } from "react-router-dom";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_LONG_TERM_SELECT } from "../lib/demoCatalog";

type StockCandidate = {
  code: string;
  name: string;
  score: number;
  reason?: string;
  price?: number;
  change_pct?: number;
  industry?: string;
  market_cap?: number;
};

export function LongTermSelectPage() {
  const [strategy, setStrategy] = useState("classic");
  const [topN, setTopN] = useState(20);
  const [dataSource, setDataSource] = useState("legacy");
  const [horizon, setHorizon] = useState(20);
  const [ran, setRan] = useState(false);

  const { data, error, isLoading, mutate } = useSWR(
    ran ? ["long-term-select", strategy, topN, dataSource, horizon] : null,
    () => apiFetchV1<{ candidates: StockCandidate[]; strategy?: string; market?: string }>("/long-term-select", {
      method: "POST",
      body: JSON.stringify({ strategy, top_n: topN, data_source: dataSource, horizon_days: horizon, market: "CN" }),
    }),
  );

  const live = data?.candidates ?? [];
  const isDemo = !ran || Boolean(error) || (!isLoading && !live.length);
  const candidates = isDemo ? DEMO_LONG_TERM_SELECT.candidates : live;
  const strategyLabel = isDemo ? DEMO_LONG_TERM_SELECT.strategy : (data?.strategy ?? strategy);
  const marketLabel = isDemo ? DEMO_LONG_TERM_SELECT.market : (data?.market ?? "CN");

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.longTermSelect} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">中长线选股</h1>
          <p className="text-sm text-slate-500">基于多因子模型 + AI 的基本面与量化选股</p>
          <DemoBanner show={isDemo} />
        </div>
      </div>

      <div className="glass-card flex flex-wrap items-end gap-4 p-4">
        <div className="flex-1 min-w-[120px]">
          <label className="text-xs font-semibold text-slate-500">策略</label>
          <select className="select select-bordered select-sm w-full" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
            <option value="classic">经典多因子</option>
            <option value="value">价值优先</option>
            <option value="growth">成长优先</option>
            <option value="momentum">动量优先</option>
            <option value="quality">质量优先</option>
          </select>
        </div>
        <div className="flex-1 min-w-[80px]">
          <label className="text-xs font-semibold text-slate-500">Top N</label>
          <select className="select select-bordered select-sm w-full" value={topN} onChange={(e) => setTopN(Number(e.target.value))}>
            {[10, 20, 30, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="flex-1 min-w-[100px]">
          <label className="text-xs font-semibold text-slate-500">数据源</label>
          <select className="select select-bordered select-sm w-full" value={dataSource} onChange={(e) => setDataSource(e.target.value)}>
            <option value="legacy">传统数据</option>
            <option value="qlib">Qlib</option>
          </select>
        </div>
        <div className="flex-1 min-w-[80px]">
          <label className="text-xs font-semibold text-slate-500">持仓期</label>
          <select className="select select-bordered select-sm w-full" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
            <option value={5}>5天</option>
            <option value={10}>10天</option>
            <option value={20}>20天</option>
            <option value={60}>60天</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500">&nbsp;</label>
          <button type="button" className="btn btn-primary btn-sm w-full" onClick={() => { setRan(true); mutate(); }}>开始选股</button>
        </div>
      </div>

      {isLoading && <PageSkeleton rows={3} />}

      {candidates.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          共选出 {candidates.length} 只标的 · 策略: {strategyLabel} · 市场: {marketLabel}
        </div>
      )}

      {candidates.length > 0 && (
        <section className="glass-card overflow-x-auto p-4">
          <table className="table w-full">
            <thead>
              <tr><th>#</th><th>代码</th><th>名称</th><th>评分</th><th>行业</th><th>理由</th></tr>
            </thead>
            <tbody>
              {candidates.map((c: StockCandidate, i: number) => (
                <tr key={c.code}>
                  <td>{i + 1}</td>
                  <td><Link className="link link-primary font-mono" to={`/stocks/${c.code}`}>{c.code}</Link></td>
                  <td>{c.name}</td>
                  <td className="mono font-bold">{c.score.toFixed(1)}</td>
                  <td>{c.industry ?? "--"}</td>
                  <td className="text-sm text-slate-500">{c.reason ?? "--"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
