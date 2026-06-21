import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

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
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无对冲基金数据</div>;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">AI 对冲基金</h1>
        <p className="text-sm text-slate-500">AI 驱动的自动化对冲基金管理面板</p>
        {data.updated_at && (
          <p className="mt-1 text-xs text-slate-400">
            更新于：{new Date(data.updated_at).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      {/* NAV */}
      <div className="glass-card p-4">
        <h2 className="mb-3 text-sm font-bold text-slate-500">基金净值</h2>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <div className="text-xs text-slate-500">当前净值</div>
            <div className="text-2xl font-bold">{data.nav.current.toFixed(4)}</div>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <div className="text-xs text-slate-500">日涨跌幅</div>
            <div className={`text-2xl font-bold ${data.nav.daily_change_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
              {data.nav.daily_change_pct >= 0 ? "+" : ""}
              {data.nav.daily_change_pct.toFixed(2)}%
            </div>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <div className="text-xs text-slate-500">累计收益</div>
            <div className={`text-2xl font-bold ${data.nav.inception_return_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
              {data.nav.inception_return_pct >= 0 ? "+" : ""}
              {data.nav.inception_return_pct.toFixed(2)}%
            </div>
          </div>
        </div>
      </div>

      {/* Returns */}
      <div className="glass-card p-4">
        <h2 className="mb-3 text-sm font-bold text-slate-500">收益表现</h2>
        <div className="grid grid-cols-4 gap-3">
          {(["daily", "weekly", "monthly", "yearly"] as const).map((period) => {
            const val = data.returns[period];
            return (
              <div key={period} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
                <div className="text-xs text-slate-500">
                  {period === "daily" ? "日收益" : period === "weekly" ? "周收益" : period === "monthly" ? "月收益" : "年收益"}
                </div>
                <div className={`text-lg font-bold ${val >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {val >= 0 ? "+" : ""}
                  {val.toFixed(2)}%
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Metrics */}
      <div className="glass-card p-4">
        <h2 className="mb-3 text-sm font-bold text-slate-500">风险指标</h2>
        <div className="grid grid-cols-4 gap-3">
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <div className="text-xs text-slate-500">夏普比</div>
            <div className="text-lg font-bold">{data.metrics.sharpe.toFixed(3)}</div>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <div className="text-xs text-slate-500">最大回撤</div>
            <div className="text-lg font-bold text-rose-600">
              {Math.abs(data.metrics.max_drawdown_pct).toFixed(2)}%
            </div>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <div className="text-xs text-slate-500">胜率</div>
            <div className="text-lg font-bold">{(data.metrics.win_rate * 100).toFixed(1)}%</div>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <div className="text-xs text-slate-500">总交易</div>
            <div className="text-lg font-bold">{data.metrics.total_trades}</div>
          </div>
        </div>
      </div>

      {/* Positions */}
      <div className="glass-card p-4">
        <h2 className="mb-3 text-sm font-bold text-slate-500">当前持仓</h2>
        {data.positions.length === 0 ? (
          <p className="text-sm text-slate-400">暂无持仓</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="table table-sm">
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
                {data.positions.map((pos) => (
                  <tr key={pos.symbol}>
                    <td className="font-medium">{pos.symbol}</td>
                    <td>{pos.market}</td>
                    <td>
                      <span className={`badge badge-xs ${pos.direction === "long" ? "badge-success" : "badge-error"}`}>
                        {pos.direction === "long" ? "多头" : "空头"}
                      </span>
                    </td>
                    <td className="text-right">{pos.weight_pct.toFixed(1)}%</td>
                    <td className={`text-right font-bold ${pos.pnl_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {pos.pnl_pct >= 0 ? "+" : ""}
                      {pos.pnl_pct.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
