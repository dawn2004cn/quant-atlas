import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types ── */
type Yanbao = {
  id: string;
  title: string;
  stock_name?: string;
  stock_code?: string;
  rating?: string;
  rating_change?: string;
  agency?: string;
  analyst?: string;
  publish_date: string;
  summary?: string;
  target_price?: number;
  current_price?: number;
  url?: string;
};

type YanbaoResponse = {
  items: Yanbao[];
  total: number;
};

/* ── Format helpers ── */
function fmtDate(iso?: string): string {
  if (!iso) return "--";
  try {
    return new Date(iso).toLocaleDateString("zh-CN");
  } catch {
    return iso;
  }
}

function ratingClass(rating?: string): string {
  if (!rating) return "";
  const r = rating.toLowerCase();
  if (r.includes("买入") || r.includes("增持") || r.includes("强烈推荐"))
    return "text-emerald-600";
  if (r.includes("中性") || r.includes("持有")) return "text-amber-600";
  if (r.includes("卖出") || r.includes("减持") || r.includes("回避"))
    return "text-rose-600";
  return "";
}

/* ── Component ── */
export function YanbaoHubPage() {
  const [stockFilter, setStockFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const params = new URLSearchParams();
  if (stockFilter) params.set("stock", stockFilter);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);

  const { data, error, isLoading } = useSWR(
    ["yanbao/list", stockFilter, dateFrom, dateTo],
    () => apiFetchV1<YanbaoResponse>(`/yanbao/list?${params}`),
    { refreshInterval: 120_000 },
  );

  const items = data?.items ?? [];

  if (isLoading && !items.length) return <PageSkeleton rows={5} />;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">研报 Hub</h1>
        <p className="text-sm text-slate-500">
          券商研究报告聚合，覆盖评级变动与目标价
        </p>
      </div>

      {/* Filter Bar */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <input
          type="text"
          className="input input-bordered input-sm w-32"
          placeholder="股票代码/名称"
          value={stockFilter}
          onChange={(e) => setStockFilter(e.target.value)}
        />
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <span>从</span>
          <input
            type="date"
            className="input input-bordered input-sm"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <span>至</span>
          <input
            type="date"
            className="input input-bordered input-sm"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
      </div>

      {/* Error */}
      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      {/* Report List */}
      <section className="glass-card overflow-x-auto p-4">
        <table className="table w-full">
          <thead>
            <tr>
              <th>日期</th>
              <th>股票</th>
              <th>标题</th>
              <th>机构</th>
              <th>分析师</th>
              <th>评级</th>
              <th>目标价</th>
              <th>现价</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r: Yanbao, idx: number) => (
              <tr key={r.id ?? idx} className="hover">
                <td className="text-xs text-slate-500 whitespace-nowrap">
                  {fmtDate(r.publish_date)}
                </td>
                <td>
                  {r.stock_code ? (
                    <span>
                      <code>{r.stock_code}</code>
                      {r.stock_name ? (
                        <span className="ml-1 text-xs text-slate-500">
                          {r.stock_name}
                        </span>
                      ) : null}
                    </span>
                  ) : (
                    <span className="text-slate-400">--</span>
                  )}
                </td>
                <td className="max-w-xs">
                  <div className="font-medium truncate">{r.title}</div>
                  {r.summary && (
                    <div className="text-xs text-slate-500 truncate">
                      {r.summary}
                    </div>
                  )}
                </td>
                <td className="text-xs text-slate-500">{r.agency ?? "--"}</td>
                <td className="text-xs text-slate-500">{r.analyst ?? "--"}</td>
                <td>
                  <span className={ratingClass(r.rating)}>
                    {r.rating ?? "--"}
                  </span>
                  {r.rating_change && (
                    <span className="text-xs text-slate-400 ml-1">
                      ({r.rating_change})
                    </span>
                  )}
                </td>
                <td className="text-xs">
                  {r.target_price != null
                    ? `¥${r.target_price.toFixed(2)}`
                    : "--"}
                </td>
                <td className="text-xs">
                  {r.current_price != null
                    ? `¥${r.current_price.toFixed(2)}`
                    : "--"}
                </td>
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-500">
                  暂无研报数据
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}