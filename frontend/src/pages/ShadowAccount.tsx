import { useState, useEffect, useRef } from "react";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type AnalysisResult = {
  total_trades?: number;
  win_rate?: number;
  total_return?: number;
  summary?: string;
};

export default function ShadowAccountPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetchV1<AnalysisResult>("/shadow-account/status")
      .then(setResult)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleUpload = async () => {
    if (!file || uploading) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/v1/shadow-account/analyze", {
        method: "POST",
        credentials: "same-origin",
        body: form,
      });
      if (!res.ok) throw new Error(`上传失败 (${res.status})`);
      const json = await res.json();
      setResult(json?.data ?? json);
      setFile(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return <div className="space-y-4"><div className="skeleton skeleton-card"></div></div>;
  }

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.shadowAccount} />
      <div>
        <h1 className="page-title">影子账户</h1>
        <p className="text-sm text-slate-500 mt-1">导入 CSV/Excel 成交记录，模拟账户分析</p>
      </div>

      {error && <div className="alert alert-error text-sm">{error}</div>}

      <div
        ref={dropRef}
        className="quant-card border-2 border-dashed border-slate-300 dark:border-slate-600 text-center py-12 cursor-pointer hover:border-brand transition-colors"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = ".csv,.xlsx,.xls";
          input.onchange = () => { if (input.files?.[0]) setFile(input.files[0]); };
          input.click();
        }}
      >
        <div className="text-4xl mb-3">📄</div>
        <p className="font-semibold">{file ? file.name : "点击或拖拽上传成交记录"}</p>
        <p className="text-sm text-slate-500 mt-1">支持 CSV / XLSX / XLS 格式</p>
        {file && (
          <button
            type="button"
            className="btn-brand mt-4"
            disabled={uploading}
            onClick={(e) => { e.stopPropagation(); handleUpload(); }}
          >
            {uploading ? "分析中..." : "开始分析"}
          </button>
        )}
      </div>

      {result && (
        <section className="quant-card space-y-4">
          <h2 className="text-lg font-bold">分析结果</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <div><div className="hero-caption">总交易</div><div className="text-xl font-bold">{result.total_trades ?? "--"}</div></div>
            <div><div className="hero-caption">胜率</div><div className="text-xl font-bold">{result.win_rate != null ? `${(result.win_rate * 100).toFixed(1)}%` : "--"}</div></div>
            <div><div className="hero-caption">总收益</div><div className={`text-xl font-bold ${(result.total_return ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>{result.total_return != null ? `${(result.total_return >= 0 ? "+" : "")}${(result.total_return * 100).toFixed(2)}%` : "--"}</div></div>
          </div>
          {result.summary && <p className="text-sm text-slate-500">{result.summary}</p>}
        </section>
      )}
    </div>
  );
}