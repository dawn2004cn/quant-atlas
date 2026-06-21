import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types ── */
type InvestmentManager = {
  manager_id: string;
  name: string;
  title?: string;
  avatar_url?: string;
  managed_assets?: number;
  total_return_pct?: number;
  annual_return_pct?: number;
  sharpe_ratio?: number;
  max_drawdown_pct?: number;
  strategy_count?: number;
  win_rate_pct?: number;
  description?: string;
  tags?: string[];
};

type ManagerResponse = {
  items: InvestmentManager[];
  total: number;
};

/* ── Format helpers ── */
function fmtPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function fmtAssets(v?: number | null): string {
  const n = Number(v ?? 0);
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(2)}万`;
  return n.toFixed(0);
}

/* ── Component ── */
export function InvestmentManagersPage() {
  const { data, error, isLoading } = useSWR(
    "investment-managers",
    () => apiFetchV1<ManagerResponse>("/investment-managers"),
    { refreshInterval: 120_000 },
  );

  const managers = data?.items ?? [];

  if (isLoading && !managers.length) return <PageSkeleton rows={4} />;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">投资经理</h1>
        <p className="text-sm text-slate-500">
          策略管理与绩效追踪，覆盖所有投资经理档案
        </p>
      </div>

      {/* Error */}
      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      {/* Card Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {managers.map((m: InvestmentManager) => (
          <Link
            key={m.manager_id}
            to={`/app/investment-managers/${m.manager_id}`}
            className="glass-card rounded-2xl p-5 space-y-4 hover:shadow-md transition-shadow"
          >
            {/* Avatar & Name */}
            <div className="flex items-center gap-3">
              <div className="avatar placeholder">
                <div className="w-12 rounded-full bg-brand/10 text-brand">
                  <span className="text-lg font-bold">
                    {m.name?.charAt(0) ?? "?"}
                  </span>
                </div>
              </div>
              <div>
                <div className="font-bold">{m.name}</div>
                {m.title && (
                  <div className="text-xs text-slate-500">{m.title}</div>
                )}
              </div>
            </div>

            {/* Description */}
            {m.description && (
              <p className="text-xs text-slate-600 line-clamp-2">
                {m.description}
              </p>
            )}

            {/* Stats */}
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                <div className="text-xs text-slate-500">年化收益</div>
                <div
                  className={`text-sm font-bold ${
                    (m.annual_return_pct ?? 0) >= 0
                      ? "text-emerald-600"
                      : "text-rose-600"
                  }`}
                >
                  {fmtPct(m.annual_return_pct)}
                </div>
              </div>
              <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                <div className="text-xs text-slate-500">夏普比</div>
                <div className="text-sm font-bold">
                  {m.sharpe_ratio?.toFixed(2) ?? "--"}
                </div>
              </div>
              <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                <div className="text-xs text-slate-500">回撤</div>
                <div className="text-sm font-bold text-rose-600">
                  {m.max_drawdown_pct != null
                    ? `${Math.abs(m.max_drawdown_pct).toFixed(1)}%`
                    : "--"}
                </div>
              </div>
            </div>

            {/* Bottom row: assets + strategy count */}
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>管理规模 {fmtAssets(m.managed_assets)}</span>
              <span>{m.strategy_count ?? 0} 个策略</span>
            </div>

            {/* Tags */}
            {m.tags && m.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {m.tags.map((tag) => (
                  <span
                    key={tag}
                    className="badge badge-ghost badge-sm"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </Link>
        ))}
      </div>

      {/* Empty */}
      {!managers.length && (
        <div className="py-12 text-center text-slate-500">
          暂无投资经理数据
        </div>
      )}
    </div>
  );
}