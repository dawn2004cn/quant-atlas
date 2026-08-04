import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

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
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无作战室数据</div>;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.warRoom} />
      <div>
        <h1 className="text-2xl font-bold">{data.room_name || "作战室"}</h1>
        <p className="text-sm text-slate-500">多视角市场分析与数据面板</p>
        {data.last_updated && (
          <p className="mt-1 text-xs text-slate-400">
            更新于：{new Date(data.last_updated).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      {/* Perspectives */}
      {data.perspectives.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {data.perspectives.map((p) => (
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
        {data.data_grid.length === 0 ? (
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
                {data.data_grid.map((row) => {
                  const signal = SIGNAL_MAP[row.signal];
                  return (
                    <tr key={row.symbol}>
                      <td className="font-medium">{row.symbol}</td>
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
