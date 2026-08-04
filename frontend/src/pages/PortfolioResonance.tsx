import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type ResonanceData = {
  resonance_score?: number;
  alignment?: number;
  sectors?: Array<{ name: string; weight: number }>;
  correlations?: Array<Array<number>>;
};

export default function PortfolioResonance() {
  const { data, error, isLoading, mutate } = useSWR<ResonanceData>("/portfolio/resonance", apiFetchV1, { refreshInterval: 30000 });

  const score = data?.resonance_score ?? 0;
  const alignment = data?.alignment ?? 0;
  const sectors = data?.sectors ?? [];
  const correlations = data?.correlations ?? [];

  const scoreColor = score >= 70 ? "text-green-500" : score >= 40 ? "text-yellow-500" : "text-red-500";
  const alignColor = alignment >= 70 ? "stroke-green-500" : alignment >= 40 ? "stroke-yellow-500" : "stroke-red-500";

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.portfolioResonance} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">组合共鸣</h1>
          <p className="text-[var(--quant-muted)] text-sm">组合谐波分析与共振检测</p>
        </div>
        <button type="button" className="btn-brand btn-sm" onClick={() => mutate()}>刷新</button>
      </div>

      {isLoading && !data ? <div className="quant-card p-6 text-center text-[var(--quant-muted)]">加载中...</div> : null}
      {error ? <div className="quant-card p-6 text-red-500">加载失败: {error.message}</div> : null}

      {data ? (
        <div className="grid gap-5 md:grid-cols-2">
          <div className="quant-card p-6 flex flex-col items-center justify-center">
            <h2 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider mb-4">共振指数</h2>
            <div className="relative w-40 h-40">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="54" fill="none" stroke="var(--quant-border)" strokeWidth="8" />
                <circle cx="60" cy="60" r="54" fill="none" className={alignColor} strokeWidth="8" strokeDasharray={`${(score / 100) * 339.292} 339.292`} strokeLinecap="round" />
              </svg>
              <div className={`absolute inset-0 flex items-center justify-center text-4xl font-bold mono ${scoreColor}`}>{score}</div>
            </div>
            <div className="mt-2 text-xs text-[var(--quant-muted)]">/ 100</div>
          </div>

          <div className="quant-card p-6 flex flex-col items-center justify-center">
            <h2 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider mb-4">组合对齐度</h2>
            <div className="relative w-40 h-40">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="54" fill="none" stroke="var(--quant-border)" strokeWidth="8" />
                <circle cx="60" cy="60" r="54" fill="none" className={alignColor} strokeWidth="8" strokeDasharray={`${(alignment / 100) * 339.292} 339.292`} strokeLinecap="round" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center text-4xl font-bold mono">{alignment}</div>
            </div>
            <div className="mt-2 text-xs text-[var(--quant-muted)]">/ 100</div>
          </div>

          <div className="quant-card p-5">
            <h2 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider mb-4">行业构成</h2>
            <div className="space-y-3">
              {sectors.map((s) => (
                <div key={s.name} className="flex items-center gap-3">
                  <div className="w-20 text-sm truncate">{s.name}</div>
                  <div className="flex-1 h-5 bg-[var(--quant-surface)] rounded overflow-hidden">
                    <div className="h-full bg-[var(--quant-accent)] rounded transition-all" style={{ width: `${s.weight * 100}%` }} />
                  </div>
                  <div className="mono text-xs w-12 text-right">{(s.weight * 100).toFixed(1)}%</div>
                </div>
              ))}
            </div>
          </div>

          <div className="quant-card p-5">
            <h2 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider mb-4">相关性矩阵</h2>
            {correlations.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <tbody>
                    {correlations.map((row, i) => (
                      <tr key={i}>
                        {row.map((val, j) => {
                          const color = val > 0.5 ? "bg-green-500/30" : val > 0 ? "bg-green-500/10" : val > -0.5 ? "bg-red-500/10" : "bg-red-500/30";
                          return <td key={j} className={`${color} p-2 text-center mono font-medium ${Math.abs(val) > 0.7 ? "text-white" : ""}`}>{val.toFixed(2)}</td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="text-[var(--quant-muted)] text-sm">暂无数据</p>}
          </div>
        </div>
      ) : null}
    </div>
  );
}
