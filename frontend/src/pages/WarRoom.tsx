import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_WAR_ROOM } from "../lib/demoCatalog";

type PerspectivePanel = {
  label: string;
  summary: string;
  score: number;
  color: string;
};

type WarRoomDataRow = {
  symbol: string;
  market: string;
  price: number;
  change_pct: number;
  volume: number;
  signal: "buy" | "sell" | "hold";
  confidence: number;
};

type WarRoomStatus = {
  room_name: string;
  perspectives: PerspectivePanel[];
  data_grid: WarRoomDataRow[];
  last_updated: string;
};

const SIGNAL_MAP = {
  buy: { label: "买入", className: "badge-success" },
  sell: { label: "卖出", className: "badge-error" },
  hold: { label: "持有", className: "badge-ghost" },
} as const;

export function WarRoomPage() {
  const { data, error, isLoading } = useSWR(
    "war-room-status",
    () => apiFetchV1<WarRoomStatus>("/war-room/status"),
    { refreshInterval: 30_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={5} />;

  const isDemo = Boolean(error) || !data || !(data.data_grid ?? []).length;
  const view = isDemo ? DEMO_WAR_ROOM : data;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.warRoom} />
      <div>
        <h1 className="text-2xl font-bold">{view.room_name || "作战室"}</h1>
        <p className="text-sm text-slate-500">多视角市场分析与数据面板</p>
        <DemoBanner show={isDemo} />
        {view.last_updated && (
          <p className="mt-1 text-xs text-slate-400">
            更新于：{view.last_updated === "演示" ? "演示" : new Date(view.last_updated).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      {/* Perspectives */}
      {view.perspectives.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {view.perspectives.map((p) => (
            <div
              key={p.label}
              className="glass-card p-4"
              style={{
                borderLeftColor: p.color,
                borderLeftWidth: 3,
              }}
            >
              <div className="mb-1 flex items-center justify-between">
                <h3 className="text-sm font-bold">{p.label}</h3>
                <span className="text-lg font-bold" style={{ color: p.color }}>
                  {(p.score * 100).toFixed(0)}
                </span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">{p.summary}</p>
            </div>
          ))}
        </div>
      )}

      {/* Data grid */}
      <div className="glass-card p-4">
        <h2 className="mb-3 text-sm font-bold text-slate-500">数据面板</h2>
        {view.data_grid.length === 0 ? (
          <p className="text-sm text-slate-400">暂无数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>标的</th>
                  <th>市场</th>
                  <th className="text-right">价格</th>
                  <th className="text-right">涨跌幅</th>
                  <th className="text-right">成交量</th>
                  <th className="text-center">信号</th>
                  <th className="text-right">信心</th>
                </tr>
              </thead>
              <tbody>
                {view.data_grid.map((row) => {
                  const signal = SIGNAL_MAP[row.signal];
                  return (
                    <tr key={row.symbol}>
                      <td className="font-medium">
                        <Link className="link" to={`/stock/${encodeURIComponent(row.symbol)}?m=CN`}>
                          {row.symbol}
                        </Link>
                      </td>
                      <td>{row.market}</td>
                      <td className="text-right font-mono">{row.price.toFixed(2)}</td>
                      <td
                        className={`text-right font-mono font-bold ${
                          row.change_pct >= 0 ? "text-emerald-600" : "text-rose-600"
                        }`}
                      >
                        {row.change_pct >= 0 ? "+" : ""}
                        {row.change_pct.toFixed(2)}%
                      </td>
                      <td className="text-right font-mono">
                        {row.volume >= 10000
                          ? `${(row.volume / 10000).toFixed(1)}万`
                          : row.volume.toLocaleString()}
                      </td>
                      <td className="text-center">
                        <span className={`badge badge-xs ${signal.className}`}>
                          {signal.label}
                        </span>
                      </td>
                      <td className="text-right font-mono">
                        {(row.confidence * 100).toFixed(0)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
