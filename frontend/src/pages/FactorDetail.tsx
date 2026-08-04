import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { fetchFactorDetail } from "../lib/api";

type FactorDetail = {
  factor_id: string;
  formula?: string;
  sharpe_ratio?: number;
  max_drawdown?: number;
  ic_mean?: number;
  regime?: string;
  backtest_result?: {
    annual_return?: number;
    sharpe_ratio?: number;
    win_rate?: number;
    profit_loss_ratio?: number;
    max_drawdown?: number;
    trade_count?: number;
  };
  ic_series?: Array<{ date: string; ic: number }>;
  correlations?: Array<{ factor_id: string; name?: string; value: number }>;
  created_at?: string;
  data_range?: string;
  source?: string;
};

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="quant-card text-center">
      <div className={`text-xl font-bold mono ${color ?? ""}`}>{value}</div>
      <div className="text-xs text-[var(--quant-muted)] mt-1">{label}</div>
    </div>
  );
}

export default function FactorDetail() {
  const { factorId } = useParams<{ factorId: string }>();
  const [factor, setFactor] = useState<FactorDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!factorId) return;
    setLoading(true);
    fetchFactorDetail(factorId)
      .then((data) => setFactor(data as FactorDetail))
      .catch(() => setFactor(null))
      .finally(() => setLoading(false));
  }, [factorId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="skeleton skeleton-card h-24" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton skeleton-card h-20" />
          ))}
        </div>
        <div className="skeleton skeleton-card h-64" />
      </div>
    );
  }

  if (!factor) {
    return (
      <div className="text-center py-16">
        <div className="text-lg text-[var(--quant-muted)]">因子未找到</div>
        <Link to="/factor-repository" className="text-[var(--quant-accent)] hover:underline mt-2 inline-block">
          返回因子库
        </Link>
      </div>
    );
  }

  const bt = factor.backtest_result;
  const icData = factor.ic_series ?? [];
  const maxIc = Math.max(...icData.map((d) => Math.abs(d.ic)), 0.01);

  return (
    <div className="space-y-6">
      <PageQuickNav items={QUICK_NAV_PRESETS.factorDetail} />
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-[var(--quant-muted)]">
        <Link to="/factor-repository" className="hover:text-[var(--quant-accent)]">因子库</Link>
        <span>/</span>
        <Link to="/alpha-factory" className="hover:text-[var(--quant-accent)]">Alpha Factory</Link>
        <span>/</span>
        <span className="text-[var(--quant-fg)]">{factor.factor_id}</span>
      </div>

      {/* Header */}
      <div className="quant-card">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold">{factor.factor_id}</h1>
            <div className="mono text-sm text-[var(--quant-muted)] mt-1 break-all">{factor.formula}</div>
          </div>
          {factor.regime && <span className="badge-soft">{factor.regime}</span>}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
          <MetricCard label="Sharpe" value={factor.sharpe_ratio?.toFixed(2) ?? "—"} color={factor.sharpe_ratio != null && factor.sharpe_ratio >= 1 ? "text-up" : ""} />
          <MetricCard label="最大回撤" value={factor.max_drawdown != null ? `${(factor.max_drawdown * 100).toFixed(1)}%` : "—"} color="text-down" />
          <MetricCard label="IC 均值" value={factor.ic_mean != null ? factor.ic_mean.toFixed(4) : "—"} />
          <MetricCard label="数据源" value={factor.source ?? "RD-Agent"} />
        </div>
      </div>

      {/* IC Series Chart */}
      {icData.length > 0 && (
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">IC 时序</div>
          <div className="flex items-end gap-px h-32">
            {icData.map((d, i) => {
              const h = (Math.abs(d.ic) / maxIc) * 100;
              const positive = d.ic >= 0;
              return (
                <div
                  key={i}
                  className="flex-1 rounded-t"
                  style={{
                    height: `${h}%`,
                    background: positive ? "var(--quant-accent)" : "var(--quant-danger)",
                    opacity: 0.8,
                  }}
                  title={`${d.date}: ${d.ic.toFixed(4)}`}
                />
              );
            })}
          </div>
          <div className="flex justify-between text-[10px] text-[var(--quant-muted)] mt-1">
            <span>{icData[0]?.date}</span>
            <span>{icData[icData.length - 1]?.date}</span>
          </div>
        </div>
      )}

      {/* Backtest Results */}
      {bt && (
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">回测结果</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="text-center">
              <div className="text-lg font-bold mono text-up">{bt.annual_return != null ? `${(bt.annual_return * 100).toFixed(1)}%` : "—"}</div>
              <div className="text-xs text-[var(--quant-muted)]">年化收益</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold mono">{bt.sharpe_ratio?.toFixed(2) ?? "—"}</div>
              <div className="text-xs text-[var(--quant-muted)]">Sharpe</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold mono">{bt.win_rate != null ? `${(bt.win_rate * 100).toFixed(0)}%` : "—"}</div>
              <div className="text-xs text-[var(--quant-muted)]">胜率</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold mono">{bt.profit_loss_ratio?.toFixed(2) ?? "—"}</div>
              <div className="text-xs text-[var(--quant-muted)]">盈亏比</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold mono text-down">{bt.max_drawdown != null ? `${(bt.max_drawdown * 100).toFixed(1)}%` : "—"}</div>
              <div className="text-xs text-[var(--quant-muted)]">最大回撤</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold mono">{bt.trade_count ?? "—"}</div>
              <div className="text-xs text-[var(--quant-muted)]">交易次数</div>
            </div>
          </div>
        </div>
      )}

      {/* Correlations */}
      {factor.correlations && factor.correlations.length > 0 && (
        <div className="quant-card">
          <div className="text-sm font-bold mb-3">相关因子</div>
          <div className="space-y-2">
            {factor.correlations.map((c) => (
              <div key={c.factor_id} className="flex items-center justify-between py-1.5 border-b border-[var(--quant-line-soft)] last:border-0">
                <Link to={`/factor/${c.factor_id}`} className="text-sm text-[var(--quant-accent)] hover:underline">
                  {c.name || c.factor_id}
                </Link>
                <span className={`mono text-sm ${c.value >= 0.7 ? "text-up" : c.value <= -0.3 ? "text-down" : ""}`}>
                  {c.value.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metadata */}
      <div className="quant-card">
        <div className="text-sm font-bold mb-3">元数据</div>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-[var(--quant-muted)]">创建时间</span>
            <div className="mt-1">{factor.created_at ?? "—"}</div>
          </div>
          <div>
            <span className="text-[var(--quant-muted)]">数据范围</span>
            <div className="mt-1">{factor.data_range ?? "—"}</div>
          </div>
          <div>
            <span className="text-[var(--quant-muted)]">数据源</span>
            <div className="mt-1">{factor.source ?? "RD-Agent"}</div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Link to={`/backtest?factor=${factor.factor_id}`} className="btn-brand">
          回测此因子
        </Link>
        <Link to="/alpha-factory" className="btn btn-ghost">
          返回 Alpha Factory
        </Link>
      </div>
    </div>
  );
}
