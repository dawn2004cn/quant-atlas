import { useParams, Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_INVESTMENT_MANAGERS } from "../lib/demoCatalog";

/* ── Types ── */
type ManagerDetail = {
  manager_id: string;
  name: string;
  title?: string;
  avatar_url?: string;
  managed_assets?: number;
  total_return_pct?: number;
  annual_return_pct?: number;
  sharpe_ratio?: number;
  max_drawdown_pct?: number;
  win_rate_pct?: number;
  strategy_count?: number;
  description?: string;
  tags?: string[];
  strategies?: Array<{
    strategy_id: string;
    name: string;
    symbol?: string;
    return_pct?: number;
    sharpe?: number;
    status?: string;
  }>;
  recent_performance?: Array<{
    date: string;
    return_pct: number;
  }>;
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

function fmtDate(iso?: string): string {
  if (!iso) return "--";
  try {
    return new Date(iso).toLocaleDateString("zh-CN");
  } catch {
    return iso;
  }
}

/* ── Component ── */
export function InvestmentManagerDetailPage() {
  const { managerId = "" } = useParams();

  const { data, error, isLoading } = useSWR(
    managerId ? ["investment-manager", managerId] : null,
    () => apiFetchV1<ManagerDetail>(`/investment-managers/${encodeURIComponent(managerId)}`),
  );

  if (isLoading && !data && !error) return <PageSkeleton rows={5} />;

  const isDemo = Boolean(error) || !data;
  const m = isDemo
    ? (DEMO_INVESTMENT_MANAGERS.find((row) => row.manager_id === managerId) ?? DEMO_INVESTMENT_MANAGERS[0])
    : data;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.investmentManagerDetail} />
      {/* Back Link */}
      <Link to="/investment-managers" className="btn btn-ghost btn-sm">
        &larr; 返回投资经理列表
      </Link>
      <DemoBanner show={isDemo} />

      {/* Profile Card */}
      <div className="glass-card rounded-2xl p-6 space-y-5">
        <div className="flex flex-wrap items-start gap-4">
          <div className="avatar placeholder">
            <div className="w-16 rounded-full bg-brand/10 text-brand">
              <span className="text-2xl font-bold">
                {m.name?.charAt(0) ?? "?"}
              </span>
            </div>
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{m.name}</h1>
            {m.title && (
              <p className="text-sm text-slate-500">{m.title}</p>
            )}
            {m.description && (
              <p className="mt-2 text-sm text-slate-600">{m.description}</p>
            )}
          </div>
          {m.tags && m.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {m.tags.map((tag) => (
                <span key={tag} className="badge badge-ghost">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <div className="rounded-xl bg-slate-100 p-3 text-center dark:bg-slate-800">
            <div className="text-xs text-slate-500">总收益</div>
            <div
              className={`text-lg font-bold ${
                (m.total_return_pct ?? 0) >= 0
                  ? "text-emerald-600"
                  : "text-rose-600"
              }`}
            >
              {fmtPct(m.total_return_pct)}
            </div>
          </div>
          <div className="rounded-xl bg-slate-100 p-3 text-center dark:bg-slate-800">
            <div className="text-xs text-slate-500">年化收益</div>
            <div
              className={`text-lg font-bold ${
                (m.annual_return_pct ?? 0) >= 0
                  ? "text-emerald-600"
                  : "text-rose-600"
              }`}
            >
              {fmtPct(m.annual_return_pct)}
            </div>
          </div>
          <div className="rounded-xl bg-slate-100 p-3 text-center dark:bg-slate-800">
            <div className="text-xs text-slate-500">夏普比</div>
            <div className="text-lg font-bold">
              {m.sharpe_ratio?.toFixed(2) ?? "--"}
            </div>
          </div>
          <div className="rounded-xl bg-slate-100 p-3 text-center dark:bg-slate-800">
            <div className="text-xs text-slate-500">最大回撤</div>
            <div className="text-lg font-bold text-rose-600">
              {m.max_drawdown_pct != null
                ? `${Math.abs(m.max_drawdown_pct).toFixed(1)}%`
                : "--"}
            </div>
          </div>
          <div className="rounded-xl bg-slate-100 p-3 text-center dark:bg-slate-800">
            <div className="text-xs text-slate-500">胜率</div>
            <div className="text-lg font-bold">
              {m.win_rate_pct != null ? `${m.win_rate_pct.toFixed(1)}%` : "--"}
            </div>
          </div>
          <div className="rounded-xl bg-slate-100 p-3 text-center dark:bg-slate-800">
            <div className="text-xs text-slate-500">策略数</div>
            <div className="text-lg font-bold">{m.strategy_count ?? 0}</div>
          </div>
        </div>

        {/* Assets */}
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <span>管理规模：</span>
          <span className="font-bold text-slate-700 dark:text-slate-300">
            {fmtAssets(m.managed_assets)}
          </span>
        </div>
      </div>

      {/* Strategies Section */}
      {m.strategies && m.strategies.length > 0 && (
        <section className="glass-card rounded-2xl p-5 space-y-3">
          <h2 className="text-lg font-bold">策略列表</h2>
          <div className="overflow-x-auto">
            <table className="table w-full">
              <thead>
                <tr>
                  <th>策略名称</th>
                  <th>标的</th>
                  <th>收益</th>
                  <th>夏普比</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {m.strategies.map((s) => (
                  <tr key={s.strategy_id} className="hover">
                    <td className="font-medium">{s.name}</td>
                    <td>
                      {s.symbol ? (
                        <Link className="link font-mono text-sm" to={`/stock/${encodeURIComponent(s.symbol)}?m=CN`}>
                          {s.symbol}
                        </Link>
                      ) : "--"}
                    </td>
                    <td
                      className={
                        (s.return_pct ?? 0) >= 0
                          ? "text-emerald-600"
                          : "text-rose-600"
                      }
                    >
                      {fmtPct(s.return_pct)}
                    </td>
                    <td>{s.sharpe?.toFixed(2) ?? "--"}</td>
                    <td>
                      <span
                        className={`badge ${
                          s.status === "active"
                            ? "badge-success"
                            : "badge-ghost"
                        }`}
                      >
                        {s.status ?? "--"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Recent Performance */}
      {m.recent_performance && m.recent_performance.length > 0 && (
        <section className="glass-card rounded-2xl p-5 space-y-3">
          <h2 className="text-lg font-bold">近期表现</h2>
          <div className="overflow-x-auto">
            <table className="table w-full">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>收益率</th>
                </tr>
              </thead>
              <tbody>
                {m.recent_performance.map((p, idx) => (
                  <tr key={idx}>
                    <td className="text-xs text-slate-500">
                      {fmtDate(p.date)}
                    </td>
                    <td
                      className={
                        p.return_pct >= 0
                          ? "text-emerald-600"
                          : "text-rose-600"
                      }
                    >
                      {fmtPct(p.return_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}