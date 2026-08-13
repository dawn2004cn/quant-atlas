import { useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_WIZARD_TEMPLATES } from "../lib/demoCatalog";

type WizardTemplate = {
  id: string;
  name: string;
  description?: string;
  is_recommended?: boolean;
};

type WizardPreview = {
  status?: string;
  metrics?: Record<string, string | number>;
  warnings?: string[];
};

const DEFAULT_PARAMS = `{
  "fast_period": 5,
  "slow_period": 20,
  "signal_period": 9
}`;

export function StrategyWizardPage() {
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [symbol, setSymbol] = useState("600519");
  const [paramsJson, setParamsJson] = useState(DEFAULT_PARAMS);
  const [previewResult, setPreviewResult] = useState<WizardPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const { data: templatesData, error: tmplErr, isLoading } = useSWR(
    "strategy-wizard/templates",
    () => apiFetchV1<{ templates?: WizardTemplate[] }>("/strategy/wizard/templates"),
  );

  const liveTemplates = templatesData?.templates ?? [];
  const isDemo = Boolean(tmplErr) || (!isLoading && !liveTemplates.length);
  const templates = isDemo ? DEMO_WIZARD_TEMPLATES : liveTemplates;

  const handlePreview = async () => {
    if (!selectedTemplate) return;
    setPreviewLoading(true);
    setPreviewResult(null);
    try {
      let params = {};
      try { params = JSON.parse(paramsJson); } catch { /* use defaults */ }
      const result = await apiFetchV1<WizardPreview>("/strategy/wizard/preview", {
        method: "POST",
        body: JSON.stringify({ template_id: selectedTemplate, params: { ...params, symbol, market: "CN" } }),
      });
      setPreviewResult(result);
    } catch (err: unknown) {
      setPreviewResult({ status: "error", warnings: [err instanceof Error ? err.message : String(err)] });
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.strategyWizard} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">策略向导</h1>
          <p className="text-sm text-slate-500">从模板快速创建量化策略</p>
          <DemoBanner show={isDemo} />
        </div>
      </div>

      {tmplErr && <div className="alert alert-error">加载模板失败：{tmplErr.message}</div>}

      <div className="glass-card space-y-4 p-4">
        {/* Template Selection */}
        <div>
          <label className="text-xs font-semibold text-slate-500">策略模板</label>
          <select
            className="select select-bordered mt-1 w-full"
            value={selectedTemplate}
            onChange={(e) => setSelectedTemplate(e.target.value)}
          >
            <option value="">请选择模板</option>
            {templates.map((t: WizardTemplate) => (
              <option key={t.id} value={t.id}>{t.name}{t.is_recommended ? " (推荐)" : ""}</option>
            ))}
          </select>
          {!templates.length && <p className="mt-1 text-xs text-slate-400">暂无可用模板</p>}
        </div>

        {/* Symbol */}
        <div>
          <label className="text-xs font-semibold text-slate-500">标的</label>
          <input type="text" className="input input-bordered input-sm mt-1 w-full max-w-xs" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        </div>

        {/* Params */}
        <div>
          <label className="text-xs font-semibold text-slate-500">参数（JSON）</label>
          <textarea className="textarea textarea-bordered mt-1 w-full font-mono text-xs" rows={6} value={paramsJson} onChange={(e) => setParamsJson(e.target.value)} />
        </div>

        <button type="button" className="btn btn-primary" onClick={handlePreview} disabled={!selectedTemplate || previewLoading}>
          {previewLoading ? "预览中..." : "预览策略"}
        </button>
      </div>

      {/* Preview Result */}
      {previewResult && (
        <section className="glass-card space-y-4 p-4">
          <h2 className="text-sm font-bold">预览结果</h2>
          <div className={`rounded-xl p-3 ${previewResult.status === "error" ? "bg-rose-50 dark:bg-rose-950/30" : "bg-emerald-50 dark:bg-emerald-950/30"}`}>
            <p className="text-sm font-semibold">状态: {previewResult.status ?? "ok"}</p>
          </div>

          {previewResult.metrics && (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {Object.entries(previewResult.metrics).map(([key, val]) => (
                <div key={key} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
                  <div className="text-xs text-slate-500">{key}</div>
                  <div className="text-lg font-bold">{typeof val === "number" ? val.toFixed(4) : String(val)}</div>
                </div>
              ))}
            </div>
          )}

          {previewResult.warnings?.length && (
            <div className="space-y-1">
              {previewResult.warnings.map((w, i) => (
                <p key={i} className="rounded bg-amber-50 p-2 text-xs text-amber-700 dark:bg-amber-950/30 dark:text-amber-400">{w}</p>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}