import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_HEDGE_FUND } from "../lib/demoCatalog";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

type HedgeFundStatus = {
  nav: {
    current: number;
    daily_change_pct: number;
    inception_return_pct: number;
  };
  returns: {
    daily: number;
    weekly: number;
    monthly: number;
    yearly: number;
  };
  positions: Array<{
    symbol: string;
    market: string;
    weight_pct: number;
    pnl_pct: number;
    direction: "long" | "short";
  }>;
  metrics: {
    sharpe: number;
    max_drawdown_pct: number;
    win_rate: number;
    total_trades: number;
  };
  updated_at: string;
};

export function AIHedgeFundPage() {
  const { data, error, isLoading } = useSWR(
    "ai-hedge-fund-status",
    () => apiFetchV1<HedgeFundStatus>("/ai-hedge-fund/status"),
    { refreshInterval: 60_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={4} />;

  const isDemo = Boolean(error) || !data || !(data.positions ?? []).length;
  const view = isDemo ? DEMO_HEDGE_FUND : data;

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.aiHedgeFund} />
      <div>
        <h1 className="text-2xl font-bold">AI 对冲基金</h1>
        <p className="text-sm text-zinc-500">AI 驱动的自动化对冲基金管理面板</p>
        <DemoBanner show={isDemo} />
        {view.updated_at && (
          <p className="mt-1 text-xs text-zinc-400">
            更新于：{view.updated_at === "演示" ? "演示" : new Date(view.updated_at).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      {/* NAV */}
      <Panel className="p-4">
        <h2 className="mb-3 text-sm font-bold text-zinc-500">基金净值</h2>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
            <div className="text-xs text-zinc-500">当前净值</div>
            <div className="text-2xl font-bold">{view.nav.current.toFixed(4)}</div>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
            <div className="text-xs text-zinc-500">日涨跌幅</div>
            <div className={`text-2xl font-bold ${view.nav.daily_change_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {view.nav.daily_change_pct >= 0 ? "+" : ""}
              {view.nav.daily_change_pct.toFixed(2)}%
            </div>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
            <div className="text-xs text-zinc-500">累计收益</div>
            <div className={`text-2xl font-bold ${view.nav.inception_return_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {view.nav.inception_return_pct >= 0 ? "+" : ""}
              {view.nav.inception_return_pct.toFixed(2)}%
            </div>
          </div>
        </div>
      </Panel>

      {/* Returns */}
      <Panel className="p-4">
        <h2 className="mb-3 text-sm font-bold text-zinc-500">收益表现</h2>
        <div className="grid grid-cols-4 gap-3">
          {(["daily", "weekly", "monthly", "yearly"] as const).map((period) => {
            const val = view.returns[period];
            return (
              <div key={period} className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
                <div className="text-xs text-zinc-500">
                  {period === "daily" ? "日收益" : period === "weekly" ? "周收益" : period === "monthly" ? "月收益" : "年收益"}
                </div>
                <div className={`text-lg font-bold ${val >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {val >= 0 ? "+" : ""}
                  {val.toFixed(2)}%
                </div>
              </div>
            );
          })}
        </div>
      </Panel>

      {/* Metrics */}
      <Panel className="p-4">
        <h2 className="mb-3 text-sm font-bold text-zinc-500">风险指标</h2>
        <div className="grid grid-cols-4 gap-3">
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
            <div className="text-xs text-zinc-500">夏普比</div>
            <div className="text-lg font-bold">{view.metrics.sharpe.toFixed(3)}</div>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
            <div className="text-xs text-zinc-500">最大回撤</div>
            <div className="text-lg font-bold text-rose-400">
              {Math.abs(view.metrics.max_drawdown_pct).toFixed(2)}%
            </div>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
            <div className="text-xs text-zinc-500">胜率</div>
            <div className="text-lg font-bold">{(view.metrics.win_rate * 100).toFixed(1)}%</div>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800">
            <div className="text-xs text-zinc-500">总交易</div>
            <div className="text-lg font-bold">{view.metrics.total_trades}</div>
          </div>
        </div>
      </Panel>

      {/* Positions */}
      <Panel className="p-4">
        <h2 className="mb-3 text-sm font-bold text-zinc-500">当前持仓</h2>
        {view.positions.length === 0 ? (
          <p className="text-sm text-zinc-400">暂无持仓</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th>标的</th>
                  <th>市场</th>
                  <th>方向</th>
                  <th className="text-right">权重</th>
                  <th className="text-right">盈亏</th>
                </tr>
              </thead>
              <tbody>
                {view.positions.map((pos) => (
                  <tr key={pos.symbol}>
                    <td className="font-medium">
                      <Link className="link" to={`/stock/${encodeURIComponent(pos.symbol)}?m=CN`}>
                        {pos.symbol}
                      </Link>
                    </td>
                    <td>{pos.market}</td>
                    <td>
                      <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${pos.direction === "long" ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30" : "bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/30"}`}>
                        {pos.direction === "long" ? "多头" : "空头"}
                      </span>
                    </td>
                    <td className="text-right">{pos.weight_pct.toFixed(1)}%</td>
                    <td className={`text-right font-bold ${pos.pnl_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {pos.pnl_pct >= 0 ? "+" : ""}
                      {pos.pnl_pct.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
