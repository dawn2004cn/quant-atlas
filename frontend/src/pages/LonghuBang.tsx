import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types ── */
type LonghuItem = {
  symbol: string;
  name?: string;
  buy_amount: number;
  sell_amount: number;
  net_amount: number;
  department?: string;
  reason?: string;
  trade_date: string;
  stock_code?: string;
};

type LonghuResponse = {
  items: LonghuItem[];
  total: number;
};

/* ── Format helpers ── */
function fmtAmount(v?: number | null): string {
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

function amountClass(v?: number | null): string {
  if (v == null) return "";
  return v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-600" : "";
}

/* ── Component ── */
export function LonghuBangPage() {
  const [tradeDate, setTradeDate] = useState("");

  const params = new URLSearchParams();
  if (tradeDate) params.set("trade_date", tradeDate);

  const { data, error, isLoading } = useSWR(
    ["longhu", tradeDate],
    () => apiFetchV1<LonghuResponse>(`/market/longhu?${params}`),
    { refreshInterval: 120_000 },
  );

  const items = data?.items ?? [];

  if (isLoading && !items.length) return <PageSkeleton rows={5} />;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">龙虎榜</h1>
        <p className="text-sm text-slate-500">
          机构席位大额交易披露，追踪主力资金动向
        </p>
      </div>

      {/* Filter Bar */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <span>交易日</span>
          <input
            type="date"
            className="input input-bordered input-sm"
            value={tradeDate}
            onChange={(e) => setTradeDate(e.target.value)}
          />
        </div>
      </div>

      {/* Error */}
      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      {/* Table */}
      <section className="glass-card overflow-x-auto p-4">
        <table className="table w-full">
          <thead>
            <tr>
              <th>日期</th>
              <th>代码</th>
              <th>名称</th>
              <th>买入额</th>
              <th>卖出额</th>
              <th>净额</th>
              <th>上榜原因</th>
              <th>营业部</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item: LonghuItem, idx: number) => (
              <tr key={`${item.symbol}-${idx}`} className="hover">
                <td className="text-xs text-slate-500 whitespace-nowrap">
                  {fmtDate(item.trade_date)}
                </td>
                <td><code>{item.stock_code || item.symbol}</code></td>
                <td className="font-medium">{item.name ?? "--"}</td>
                <td className="text-emerald-600">{fmtAmount(item.buy_amount)}</td>
                <td className="text-rose-600">{fmtAmount(item.sell_amount)}</td>
                <td className={`font-semibold ${amountClass(item.net_amount)}`}>
                  {fmtAmount(item.net_amount)}
                </td>
                <td className="max-w-xs text-xs text-slate-500 truncate">
                  {item.reason ?? "--"}
                </td>
                <td className="max-w-[160px] text-xs text-slate-500 truncate">
                  {item.department ?? "--"}
                </td>
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-500">
                  暂无龙虎榜数据
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}