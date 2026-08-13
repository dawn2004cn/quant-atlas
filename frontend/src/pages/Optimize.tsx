import { useState } from "react";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_OPTIMIZE } from "../lib/demoCatalog";

type OptimizationResult = {
  status?: string;
  weights?: Record<string, number>;
  expected_return?: number;
  expected_risk?: number;
  sharpe_ratio?: number;
};

export default function OptimizePage() {
  const [targetReturn, setTargetReturn] = useState("0.15");
  const [maxRisk, setMaxRisk] = useState("0.20");
  const [constraints, setConstraints] = useState("long_only");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OptimizationResult | null>(DEMO_OPTIMIZE);
  const [isDemo, setIsDemo] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {};
      if (targetReturn) body.target_return = parseFloat(targetReturn);
      if (maxRisk) body.max_risk = parseFloat(maxRisk);
      if (constraints) body.constraints = constraints.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await apiFetchV1<OptimizationResult>("/portfolio/optimize", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setResult(res);
      setIsDemo(false);
    } catch (e: any) {
      setError(e.message);
      setResult(DEMO_OPTIMIZE);
      setIsDemo(true);
    } finally {
      setLoading(false);
    }
  };

  const view = result ?? DEMO_OPTIMIZE;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.optimize} />
      <CoreWorkflowStrip />
      <div>
        <h1 className="page-title">组合优化</h1>
        <p className="text-sm text-slate-500 mt-1">均值-方差优化器</p>
        <DemoBanner show={isDemo} />
      </div>

      {error && <div className="alert alert-error text-sm">{error}</div>}

      <section className="quant-card space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="form-control">
            <label className="label"><span className="label-text">目标收益</span></label>
            <input className="input input-bordered input-sm" type="number" step="0.01" value={targetReturn} onChange={(e) => setTargetReturn(e.target.value)} placeholder="0.15" />
          </div>
          <div className="form-control">
            <label className="label"><span className="label-text">最大风险</span></label>
            <input className="input input-bordered input-sm" type="number" step="0.01" value={maxRisk} onChange={(e) => setMaxRisk(e.target.value)} placeholder="0.20" />
          </div>
          <div className="form-control">
            <label className="label"><span className="label-text">约束 (逗号分隔)</span></label>
            <input className="input input-bordered input-sm" value={constraints} onChange={(e) => setConstraints(e.target.value)} placeholder="long_only, no_sector_>0.3" />
          </div>
        </div>
        <button type="button" className="btn-brand" disabled={loading} onClick={run}>
          {loading ? "优化中..." : "执行优化"}
        </button>
      </section>

      <section className="quant-card space-y-4">
        <h2 className="text-lg font-bold">优化结果</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <div><div className="hero-caption">预期收益</div><div className="text-xl font-bold text-emerald-600">{view.expected_return != null ? `${(view.expected_return * 100).toFixed(2)}%` : "--"}</div></div>
          <div><div className="hero-caption">预期风险</div><div className="text-xl font-bold text-rose-600">{view.expected_risk != null ? `${(view.expected_risk * 100).toFixed(2)}%` : "--"}</div></div>
          <div><div className="hero-caption">夏普比</div><div className="text-xl font-bold">{view.sharpe_ratio?.toFixed(3) ?? "--"}</div></div>
        </div>
        {view.weights && Object.keys(view.weights).length > 0 && (
          <div className="overflow-x-auto">
            <table className="table w-full text-sm">
              <thead><tr><th>标的</th><th className="text-right">权重</th></tr></thead>
              <tbody>
                {Object.entries(view.weights).map(([k, v]) => (
                  <tr key={k}><td className="font-semibold">{k}</td><td className="text-right mono">{(v * 100).toFixed(2)}%</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
