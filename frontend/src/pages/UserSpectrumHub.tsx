import { useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type SpectrumData = {
  stats?: Record<string, number>;
  tiers?: Array<{ name: string; count: number }>;
  recent?: Array<{ username: string; action: string; time: string }>;
};

export default function UserSpectrumHub() {
  const { data, error, isLoading, mutate } = useSWR<SpectrumData>("/user/spectrum-hub", apiFetchV1, { refreshInterval: 15000 });

  const [filter, setFilter] = useState("all");
  const stats = data?.stats ?? {};
  const tiers = data?.tiers ?? [];
  const recent = data?.recent ?? [];
  const maxTierCount = Math.max(...tiers.map((t) => t.count), 1);

  const filteredRecent = filter === "all" ? recent : recent.filter((r) => r.action.includes(filter));

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.userSpectrumHub} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">用户光谱</h1>
          <p className="text-[var(--quant-muted)] text-sm">社区活跃度与用户分布</p>
        </div>
        <button type="button" className="btn-brand btn-sm" onClick={() => mutate()}>刷新</button>
      </div>

      {isLoading && !data ? <div className="quant-card p-6 text-center text-[var(--quant-muted)]">加载中...</div> : null}
      {error ? <div className="quant-card p-6 text-red-500">加载失败: {error.message}</div> : null}

      {data ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            {[["总用户", stats.total_users ?? 0], ["活跃交易者", stats.active_traders ?? 0], ["研究员", stats.researchers ?? 0]].map(([label, value]) => (
              <div key={String(label)} className="quant-card p-4 text-center">
                <div className="text-xs text-[var(--quant-muted)]">{label}</div>
                <div className="text-3xl font-bold mono">{String(value)}</div>
              </div>
            ))}
          </div>

          <div className="quant-card p-5">
            <h2 className="text-lg font-semibold mb-4">用户层级分布</h2>
            <div className="space-y-3">
              {tiers.map((tier) => (
                <div key={tier.name} className="flex items-center gap-3">
                  <div className="w-24 text-sm font-medium text-right">{tier.name}</div>
                  <div className="flex-1 h-7 bg-[var(--quant-surface)] rounded overflow-hidden">
                    <div className="h-full bg-[var(--quant-accent)] rounded transition-all duration-500 flex items-center px-2" style={{ width: `${(tier.count / maxTierCount) * 100}%` }}>
                      <span className="text-xs text-white font-medium">{tier.count}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="quant-card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">最近动态</h2>
              <div className="flex gap-1">
                {["all", "trade", "research", "social"].map((f) => (
                  <button key={f} type="button" className={`px-2 py-1 text-xs rounded ${filter === f ? "bg-[var(--quant-accent)] text-white" : "bg-[var(--quant-surface)] text-[var(--quant-muted)]"}`} onClick={() => setFilter(f)}>{f === "all" ? "全部" : f}</button>
                ))}
              </div>
            </div>
            {filteredRecent.length === 0 ? <p className="text-[var(--quant-muted)] text-sm">暂无动态</p> : (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {filteredRecent.map((r, i) => (
                  <div key={i} className="flex items-center gap-3 p-2 rounded hover:bg-[var(--quant-surface)] transition-colors">
                    <div className="w-8 h-8 rounded-full bg-[var(--quant-accent)]/20 flex items-center justify-center text-xs font-bold text-[var(--quant-accent)]">{r.username.charAt(0).toUpperCase()}</div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm"><span className="font-medium">{r.username}</span> <span className="text-[var(--quant-muted)]">{r.action}</span></div>
                    </div>
                    <div className="text-xs text-[var(--quant-muted)] whitespace-nowrap">{r.time}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
