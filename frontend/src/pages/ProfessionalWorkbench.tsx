import { useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type WorkbenchData = {
  portfolio_optimization?: { allocations?: Array<{ symbol: string; target: number; current: number }>; status?: string };
  brinson_attribution?: { total_effect?: number; allocation_effect?: number; selection_effect?: number; sectors?: Array<{ name: string; allocation: number; selection: number; total: number }> };
  compliance_check?: { passed?: boolean; violations?: Array<{ rule: string; severity: string; detail: string }> };
  execution_algorithms?: { algorithms?: Array<{ name: string; status: string; pnl?: number }> };
};

const TABS = [
  { key: "optimization", label: "组合优化" },
  { key: "brinson", label: "Brinson 归因" },
  { key: "compliance", label: "合规预检" },
  { key: "execution", label: "执行算法" },
];

export default function ProfessionalWorkbench() {
  const [tab, setTab] = useState("optimization");
  const { data, error, isLoading, mutate } = useSWR<WorkbenchData>("/workbench/professional", apiFetchV1, { refreshInterval: 30000 });

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.professionalWorkbench} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">专业工作台</h1>
          <p className="text-[var(--quant-muted)] text-sm">机构级组合管理与分析</p>
        </div>
        <button type="button" className="btn-brand btn-sm" onClick={() => mutate()}>刷新</button>
      </div>

      <div className="flex gap-1 border-b border-[var(--quant-border)] pb-1">
        {TABS.map((t) => (
          <button key={t.key} type="button" className={`px-4 py-2 text-sm rounded-t-md transition-colors ${tab === t.key ? "bg-[var(--quant-card-bg)] text-[var(--quant-accent)] font-semibold border border-b-0 border-[var(--quant-border)]" : "text-[var(--quant-muted)] hover:text-[var(--quant-fg)]"}`} onClick={() => setTab(t.key)}>{t.label}</button>
        ))}
      </div>

      {isLoading && !data ? <div className="quant-card p-6 text-center text-[var(--quant-muted)]">加载工作台数据...</div> : null}
      {error ? <div className="quant-card p-6 text-red-500">加载失败: {error.message}</div> : null}

      {data && tab === "optimization" ? (
        <div className="quant-card p-5 space-y-4">
          <h2 className="text-lg font-semibold">组合优化</h2>
          <div className="badge-soft">{data.portfolio_optimization?.status || "就绪"}</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-[var(--quant-muted)] border-b border-[var(--quant-border)]"><th className="text-left py-2">标的</th><th className="text-right py-2">目标权重</th><th className="text-right py-2">当前权重</th><th className="text-right py-2">偏差</th></tr></thead>
              <tbody>{(data.portfolio_optimization?.allocations ?? []).map((a, i) => (
                <tr key={i} className="border-b border-[var(--quant-border)]/50"><td className="py-2 mono">{a.symbol}</td><td className="py-2 text-right">{(a.target * 100).toFixed(1)}%</td><td className="py-2 text-right">{(a.current * 100).toFixed(1)}%</td><td className={`py-2 text-right ${Math.abs(a.target - a.current) > 0.02 ? "text-orange-500" : "text-green-500"}`}>{(a.target - a.current) > 0 ? "+" : ""}{((a.target - a.current) * 100).toFixed(1)}%</td></tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      ) : null}

      {data && tab === "brinson" ? (
        <div className="quant-card p-5 space-y-4">
          <h2 className="text-lg font-semibold">Brinson 绩效归因</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="quant-card p-4 text-center"><div className="text-xs text-[var(--quant-muted)]">总效应</div><div className="text-2xl font-bold mono">{(data.brinson_attribution?.total_effect ?? 0).toFixed(2)}%</div></div>
            <div className="quant-card p-4 text-center"><div className="text-xs text-[var(--quant-muted)]">配置效应</div><div className="text-2xl font-bold mono">{(data.brinson_attribution?.allocation_effect ?? 0).toFixed(2)}%</div></div>
            <div className="quant-card p-4 text-center"><div className="text-xs text-[var(--quant-muted)]">选股效应</div><div className="text-2xl font-bold mono">{(data.brinson_attribution?.selection_effect ?? 0).toFixed(2)}%</div></div>
          </div>
          <div className="overflow-x-auto mt-4">
            <table className="w-full text-sm">
              <thead><tr className="text-[var(--quant-muted)] border-b border-[var(--quant-border)]"><th className="text-left py-2">板块</th><th className="text-right py-2">配置效应</th><th className="text-right py-2">选股效应</th><th className="text-right py-2">总效应</th></tr></thead>
              <tbody>{(data.brinson_attribution?.sectors ?? []).map((s, i) => (
                <tr key={i} className="border-b border-[var(--quant-border)]/50"><td className="py-2">{s.name}</td><td className="py-2 text-right mono">{s.allocation.toFixed(2)}%</td><td className="py-2 text-right mono">{s.selection.toFixed(2)}%</td><td className="py-2 text-right mono font-semibold">{s.total.toFixed(2)}%</td></tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      ) : null}

      {data && tab === "compliance" ? (
        <div className="quant-card p-5 space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold">合规预检</h2>
            {data.compliance_check?.passed ? <span className="badge-soft text-green-600">通过</span> : <span className="badge-soft text-red-500">未通过</span>}
          </div>
          <div className="space-y-3">
            {(data.compliance_check?.violations ?? []).length === 0 ? (
              <p className="text-[var(--quant-muted)] text-sm">无违规项</p>
            ) : (data.compliance_check?.violations ?? []).map((v, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-[var(--quant-surface)] border border-[var(--quant-border)]">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${v.severity === "high" ? "bg-red-100 text-red-700" : v.severity === "medium" ? "bg-orange-100 text-orange-700" : "bg-yellow-100 text-yellow-700"}`}>{v.severity}</span>
                <div><div className="text-sm font-medium">{v.rule}</div><div className="text-xs text-[var(--quant-muted)]">{v.detail}</div></div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {data && tab === "execution" ? (
        <div className="quant-card p-5 space-y-4">
          <h2 className="text-lg font-semibold">执行算法监控</h2>
          <div className="grid gap-3 md:grid-cols-2">{(data.execution_algorithms?.algorithms ?? []).map((a, i) => (
            <div key={i} className="quant-card p-4 flex items-center justify-between">
              <div><div className="font-medium">{a.name}</div><div className="text-xs text-[var(--quant-muted)]">{a.status}</div></div>
              <div className={`mono text-lg font-bold ${(a.pnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>{a.pnl ? `${a.pnl >= 0 ? "+" : ""}${a.pnl.toFixed(2)}%` : "—"}</div>
            </div>
          ))}</div>
        </div>
      ) : null}
    </div>
  );
}
