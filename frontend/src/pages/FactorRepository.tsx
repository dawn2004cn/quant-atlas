import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { fetchFactorRepository } from "../lib/api";
import type { AlphaFactorItem } from "../types/alpha";

const REGIMES = [
  { key: "", label: "全部" },
  { key: "trending_up", label: "上涨" },
  { key: "trending_down", label: "下跌" },
  { key: "ranging", label: "震荡" },
  { key: "volatile", label: "高波动" },
  { key: "low_volatility", label: "低波动" },
];

function SharpeBadge({ value }: { value?: number }) {
  if (value == null) return <span className="text-[var(--quant-muted)]">—</span>;
  const color = value >= 1 ? "text-up" : value >= 0 ? "text-[var(--quant-warn)]" : "text-down";
  return <span className={`mono font-bold ${color}`}>{value.toFixed(2)}</span>;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="quant-card text-center">
      <div className="text-2xl font-bold mono">{value}</div>
      <div className="text-xs text-[var(--quant-muted)] mt-1">{label}</div>
    </div>
  );
}

export default function FactorRepository() {
  const [factors, setFactors] = useState<AlphaFactorItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [regime, setRegime] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [avgSharpe, setAvgSharpe] = useState(0);
  const [activeCount, setActiveCount] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFactorRepository({ page, limit: 12, regime, search });
      setFactors(data.factors ?? []);
      setTotal(data.total ?? 0);
      if (data.avg_sharpe != null) setAvgSharpe(data.avg_sharpe);
      if (data.active_count != null) setActiveCount(data.active_count);
    } catch {
      setFactors([]);
    } finally {
      setLoading(false);
    }
  }, [page, regime, search]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const totalPages = Math.max(1, Math.ceil(total / 12));

  return (
    <div className="space-y-6">
      <CoreWorkflowStrip />
      <PageQuickNav items={QUICK_NAV_PRESETS.factorRepository} />
      {/* Header */}
      <div>
        <h1 className="page-title">因子库</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">浏览和搜索已有的 Alpha 因子</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 max-w-lg">
        <StatCard label="因子总数" value={total} />
        <StatCard label="平均 Sharpe" value={avgSharpe.toFixed(2)} />
        <StatCard label="活跃因子" value={activeCount} />
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="搜索公式..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="input input-bordered input-sm w-48 bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
        />
        <div className="flex gap-1">
          {REGIMES.map((r) => (
            <button
              key={r.key}
              type="button"
              onClick={() => { setRegime(r.key); setPage(1); }}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                regime === r.key
                  ? "bg-[var(--quant-accent)]/15 text-[var(--quant-accent)] border border-[var(--quant-accent)]/30"
                  : "bg-[var(--quant-surface)] text-[var(--quant-muted)] hover:text-[var(--quant-fg)]"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Factor Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton skeleton-card" />
          ))}
        </div>
      ) : factors.length === 0 ? (
        <div className="text-center py-16 text-[var(--quant-muted)]">暂无因子数据</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {factors.map((f) => (
            <Link
              key={f.factor_id}
              to={`/factor/${f.factor_id}`}
              className="quant-card hover:border-[var(--quant-accent)] transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-start justify-between mb-3">
                <span className="text-sm font-bold group-hover:text-[var(--quant-accent)] transition-colors">
                  {f.factor_id}
                </span>
                {f.regime && (
                  <span className="badge-soft text-[10px]">{f.regime}</span>
                )}
              </div>
              <div className="mono text-xs text-[var(--quant-muted)] truncate mb-3" title={f.formula}>
                {f.formula}
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-xs text-[var(--quant-muted)]">Sharpe</div>
                  <SharpeBadge value={f.sharpe_ratio} />
                </div>
                <div>
                  <div className="text-xs text-[var(--quant-muted)]">MaxDD</div>
                  <span className="mono text-sm text-down">
                    {f.max_drawdown != null ? `${(f.max_drawdown * 100).toFixed(1)}%` : "—"}
                  </span>
                </div>
                <div>
                  <div className="text-xs text-[var(--quant-muted)]">IC</div>
                  <span className="mono text-sm">
                    {(f.metadata as Record<string, unknown>)?.ic_mean != null
                      ? ((f.metadata as Record<string, number>).ic_mean * 100).toFixed(1) + "%"
                      : "—"}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className="btn btn-ghost btn-sm"
          >
            上一页
          </button>
          <span className="text-sm text-[var(--quant-muted)] py-1">
            {page} / {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
            className="btn btn-ghost btn-sm"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}
