import { useState, useCallback } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import type { AlphaFactorItem } from "../types/alpha";
import {
  fetchAlphaFactoryStatus,
  fetchAlphaKnowledge,
  fetchAlphaFactors,
  validateAlphaFormula,
  submitRdAgentRun,
  fetchModelRecommendation,
  fetchWeeklyStatus,
  fetchPaperTradingStatus,
  submitPaperTrading,
} from "../lib/api";

const GOAL_LABELS: Record<string, string> = {
  alpha_discovery: "Alpha 发现",
  regime_adaptation: "动态适应",
  complementary: "互补因子",
  decay_recovery: "失效恢复",
  high_order: "超维发现",
};

const FORMULA_PRESETS = [
  { label: "Rank-TsArgMax", formula: "rank(Ts_ArgMax(SUMS(returns_0_1, 20), 2))" },
  { label: "Decay-Rank", formula: "rank(decay_linear(TSRANK(close, 10), 10))" },
  { label: "Corr-PriceVolume", formula: "rank(correlation(close, volume, 15))" },
  { label: "MA-Crossover", formula: "rank(TSMEAN(close, 20) / TSMEAN(close, 60) - 1)" },
  { label: "Volatility", formula: "rank(TSSTD(returns_0_1, 20))" },
  { label: "Price-Momentum", formula: "rank(close / TSMEAN(close, 20) - 1)" },
];

type Tab = "experiment" | "knowledge" | "validate" | "model" | "weekly" | "paper";

export function AlphaFactoryPage() {
  const [tab, setTab] = useState<Tab>("experiment");
  const { data: status } = useSWR("alpha-status", () => fetchAlphaFactoryStatus(), { refreshInterval: 30000 });
  const { data: knowledge } = useSWR("alpha-knowledge", () => fetchAlphaKnowledge());
  const { data: factors, mutate: reloadFactors } = useSWR("alpha-factors", () => fetchAlphaFactors());

  return (
    <div className="space-y-6">
      <PageQuickNav items={QUICK_NAV_PRESETS.alphaFactory} />
      <section className="glass-card p-6">
        <div className="hero-caption">Alpha Factory</div>
        <h1 className="text-2xl font-bold">智能因子工厂</h1>
        <p className="text-sm text-slate-500 mt-1">
          整合 RD-Agent 因子生成 + Qlib 回测 + 因子仓库，自动化从因子发现到模型部署闭环
        </p>
        <div className="flex flex-wrap gap-3 mt-4">
          <StatCard label="因子总数" value={status?.total_factors} />
          <StatCard label="平均 Sharpe" value={status?.avg_sharpe?.toFixed(2)} />
          <StatCard label="活跃因子" value={status?.active_count} />
          <StatCard label="失败次数" value={status?.failed_count} />
          <StatCard label="投研周会" value={status?.is_weekly_enabled ? "已启用" : "未启用"} />
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        {(["experiment", "knowledge", "validate", "model", "weekly", "paper"] as Tab[]).map((t) => (
          <button
            key={t}
            className={`btn ${tab === t ? "btn-primary" : "btn-ghost"} btn-sm`}
            onClick={() => setTab(t)}
          >
            {t === "experiment" ? "因子实验" :
             t === "knowledge" ? "知识库" :
             t === "validate" ? "验证" :
             t === "model" ? "模型选择" :
             t === "weekly" ? "投研周会" : "影子测试"}
          </button>
        ))}
      </div>

      {tab === "experiment" && (
        <ExperimentTab
          factors={factors?.items}
          onSubmitted={reloadFactors}
        />
      )}
      {tab === "knowledge" && <KnowledgeTab knowledge={knowledge} />}
      {tab === "validate" && <ValidateTab />}
      {tab === "model" && <ModelTab />}
      {tab === "weekly" && <WeeklyTab />}
      {tab === "paper" && <PaperTab />}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="bg-slate-100 rounded-xl px-4 py-3 min-w-[100px]">
      <div className="text-lg font-bold text-purple-600">{value ?? "--"}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function ExperimentTab({ factors, onSubmitted }: { factors?: AlphaFactorItem[]; onSubmitted: () => void }) {
  const [formula, setFormula] = useState("");
  const [goal, setGoal] = useState("alpha_discovery");
  const [searchSpace, setSearchSpace] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ run_id?: string; poll_url?: string } | null>(null);
  const [error, setError] = useState("");

  const handleSubmit = useCallback(async () => {
    if (!formula.trim() || submitting) return;
    setSubmitting(true);
    setError("");
    setResult(null);
    try {
      const res = await submitRdAgentRun({
        formula: formula.trim(),
        goal,
        goal_label: GOAL_LABELS[goal] || goal,
        search_space: searchSpace || undefined,
        data_scope: { start_date: "2024-01-01", end_date: "2025-04-27" },
      });
      setResult(res);
      onSubmitted();
    } catch (e: any) {
      setError(e.message || "提交失败");
    } finally {
      setSubmitting(false);
    }
  }, [formula, goal, searchSpace, onSubmitted]);

  return (
    <section className="glass-card p-6 space-y-4">
      <h3 className="font-semibold">提交因子实验</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">实验目标</label>
          <select className="select select-bordered w-full mt-1" value={goal} onChange={(e) => setGoal(e.target.value)}>
            <option value="alpha_discovery">Alpha 发现 (寻找新因子)</option>
            <option value="regime_adaptation">动态适应 (根据市场状态调整)</option>
            <option value="complementary">互补因子 (与现有组合低相关)</option>
            <option value="decay_recovery">失效恢复 (修复失效因子)</option>
            <option value="high_order">超维发现 (高阶非线性)</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">搜索空间</label>
          <select className="select select-bordered w-full mt-1" value={searchSpace} onChange={(e) => setSearchSpace(e.target.value)}>
            <option value="">默认搜索空间</option>
            <option value="momentum">动量因子</option>
            <option value="mean_reversion">均值回归</option>
            <option value="volatility">波动率因子</option>
          </select>
        </div>
      </div>

      <div>
        <label className="text-sm font-medium">因子表达式</label>
        <textarea
          className="textarea textarea-bordered w-full mt-1 font-mono text-sm h-28"
          placeholder="例如: rank(Ts_ArgMax(SUMS(returns_0_1, 20), 2))"
          value={formula}
          onChange={(e) => setFormula(e.target.value)}
        />
        <div className="flex flex-wrap gap-2 mt-2">
          {FORMULA_PRESETS.map((p) => (
            <button key={p.label} className="btn btn-ghost btn-xs" onClick={() => setFormula(p.formula)}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting || !formula.trim()}>
        {submitting ? "提交中…" : "🚀 提交实验"}
      </button>

      {error && <div className="alert alert-error text-sm">{error}</div>}

      {result && (
        <div className="border rounded-lg p-4 space-y-2 bg-purple-50">
          <div className="font-semibold">实验已提交</div>
          <div className="text-sm text-purple-700">🎯 实验目标: {GOAL_LABELS[goal]}</div>
          <div className="font-mono text-xs bg-purple-100 p-2 rounded">{formula}</div>
          <div className="text-xs text-slate-500">Run ID: {result.run_id || "N/A"}</div>
          {result.poll_url && <div className="text-xs">Poll URL: <a href={result.poll_url} className="link">{result.poll_url}</a></div>}
        </div>
      )}

      {factors && factors.length > 0 && (
        <div>
          <h4 className="font-medium mt-4 mb-2">因子库</h4>
          <div className="overflow-x-auto">
            <table className="table table-sm">
              <thead>
                <tr><th>公式</th><th>Sharpe</th><th>状态</th></tr>
              </thead>
              <tbody>
                {factors.slice(0, 10).map((f, i) => (
                  <tr key={i}>
                    <td className="font-mono text-xs max-w-md truncate">{f.formula}</td>
                    <td>{f.sharpe_ratio?.toFixed(2) ?? "--"}</td>
                    <td><span className="badge badge-ghost">{f.regime || "unknown"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

function KnowledgeTab({ knowledge }: { knowledge?: any }) {
  return (
    <section className="glass-card p-6 space-y-4">
      <h3 className="font-semibold">WorldQuant 101 Alphas</h3>
      {(!knowledge || !knowledge.alphas || knowledge.alphas.length === 0) && (
        <div className="text-sm text-slate-400">暂无知识库数据</div>
      )}
      {knowledge?.alphas?.slice(0, 10).map((a: any, i: number) => (
        <div key={i} className="border rounded-lg p-3">
          <div className="font-semibold text-sm">{a.name}</div>
          <div className="font-mono text-xs text-purple-600 bg-purple-50 p-2 rounded mt-1">{a.formula}</div>
          <div className="text-xs text-slate-500 mt-1">{a.description}</div>
        </div>
      ))}
      {knowledge?.operators && (
        <div>
          <h4 className="font-medium mt-4 mb-2">可用算子</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(knowledge.operators).map(([name, info]: any) => (
              <div key={name} className="border rounded p-2">
                <div className="font-bold text-purple-700 text-xs">{name}</div>
                <div className="text-xs text-slate-500">{info.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function ValidateTab() {
  const [formula, setFormula] = useState("");
  const [result, setResult] = useState<{ valid?: boolean; complexity?: string; errors?: string[] } | null>(null);
  const [error, setError] = useState("");

  const handleValidate = useCallback(async () => {
    if (!formula.trim()) return;
    setError("");
    setResult(null);
    try {
      setResult(await validateAlphaFormula(formula.trim()));
    } catch (e: any) {
      setError(e.message);
    }
  }, [formula]);

  return (
    <section className="glass-card p-6 space-y-4">
      <h3 className="font-semibold">Alpha 表达式验证</h3>
      <textarea
        className="textarea textarea-bordered w-full font-mono text-sm h-24"
        placeholder="输入因子表达式"
        value={formula}
        onChange={(e) => setFormula(e.target.value)}
      />
      <button className="btn btn-primary" onClick={handleValidate} disabled={!formula.trim()}>验证表达式</button>
      {error && <div className="alert alert-error text-sm">{error}</div>}
      {result && (
        <div className={`border rounded-lg p-3 ${result.valid ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
          {result.valid ? "✓ 表达式验证通过" : "✕ 验证失败"}
          {result.complexity && <div className="text-xs text-slate-500 mt-1">复杂度: {result.complexity}</div>}
          {result.errors?.map((e, i) => <div key={i} className="text-xs text-red-500">{e}</div>)}
        </div>
      )}
    </section>
  );
}

function ModelTab() {
  const [symbol, setSymbol] = useState("");
  const [rec, setRec] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRecommend = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const r = await fetchModelRecommendation(symbol || undefined);
      setRec(r.recommendation || null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  return (
    <section className="glass-card p-6 space-y-4">
      <h3 className="font-semibold">Meta-Learner 模型自动选择</h3>
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="text-sm font-medium">股票代码</label>
          <input className="input input-bordered w-full mt-1" placeholder="600519" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={handleRecommend} disabled={loading}>
          {loading ? "查询中…" : "🎯 获取模型建议"}
        </button>
      </div>
      {error && <div className="alert alert-error text-sm">{error}</div>}
      {rec && <div className="bg-purple-50 border rounded-lg p-3"><strong>推荐模型:</strong> {rec}</div>}
    </section>
  );
}

function WeeklyTab() {
  const { data } = useSWR("weekly-status", () => fetchWeeklyStatus(), { refreshInterval: 15000 });
  const enabled = data?.is_weekly || data?.is_weekly_enabled || data?.enabled;
  const nextRun = data?.weekly_meeting_next || data?.next_run || "N/A";

  return (
    <section className="glass-card p-6 space-y-4">
      <h3 className="font-semibold">自动化投研周会</h3>
      <div className="flex items-center gap-3">
        <span className={`badge ${enabled ? "badge-success" : "badge-ghost"}`}>
          {enabled ? "周会已启用" : "周会未启用"}
        </span>
        <span className="text-sm text-slate-500">下次运行: {nextRun}</span>
      </div>
    </section>
  );
}

function PaperTab() {
  const { data, mutate } = useSWR("paper-status", () => fetchPaperTradingStatus(), { refreshInterval: 10000 });
  const [modelId, setModelId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = useCallback(async () => {
    if (!modelId.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await submitPaperTrading(modelId.trim());
      setModelId("");
      mutate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }, [modelId, mutate]);

  const items = data?.queue || data?.items || [];

  return (
    <section className="glass-card p-6 space-y-4">
      <h3 className="font-semibold">影子测试 / Paper Trading</h3>
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="text-sm font-medium">模型 ID</label>
          <input className="input input-bordered w-full mt-1" placeholder="model-xxx" value={modelId} onChange={(e) => setModelId(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting || !modelId.trim()}>
          提交测试
        </button>
      </div>
      {error && <div className="alert alert-error text-sm">{error}</div>}
      {items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="table table-sm">
            <thead><tr><th>模型</th><th>状态</th></tr></thead>
            <tbody>
              {items.map((m, i) => (
                <tr key={i}><td>{m.model_id}</td><td><span className="badge badge-ghost">{m.status || "pending"}</span></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {items.length === 0 && <div className="text-sm text-slate-400">暂无影子测试任务</div>}
    </section>
  );
}
