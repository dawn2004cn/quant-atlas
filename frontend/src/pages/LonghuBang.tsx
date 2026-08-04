import { useState } from "react";
import useSWR from "swr";
import { useNavigate } from "react-router-dom";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { fetchLonghuPage } from "../lib/api";

type LonghuItem = {
  code?: string;
  name?: string;
  reason?: string;
  trade_date?: string;
  updated_at?: string;
  detail?: Record<string, unknown>;
};

export function LonghuBangPage() {
  const navigate = useNavigate();
  const [tradeDate, setTradeDate] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 48;

  const { data, error, isLoading } = useSWR(
    ["longhu", tradeDate, page],
    () => fetchLonghuPage({ page, page_size: pageSize, date: tradeDate || undefined }),
    { refreshInterval: 120_000, revalidateOnFocus: false },
  );

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  if (isLoading && !items.length) return <PageSkeleton rows={5} />;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.longhuBang} />
      <div>
        <h1 className="text-2xl font-bold">龙虎榜</h1>
        <p className="text-sm text-slate-500">机构席位大额交易披露，追踪主力资金动向</p>
      </div>

      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <span>交易日</span>
          <input
            type="date"
            className="input input-bordered input-sm"
            value={tradeDate}
            onChange={(e) => {
              setTradeDate(e.target.value);
              setPage(1);
            }}
          />
        </div>
        {data?.trade_date ? (
          <span className="text-xs text-slate-500">
            共 {total} 条 · 第 {page}/{pageCount} 页 · {data.trade_date}
          </span>
        ) : null}
      </div>

      {error ? <div className="alert alert-error">加载失败：{error.message}</div> : null}

      <section className="glass-card overflow-x-auto p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item: LonghuItem, idx: number) => (
            <article
              key={`${item.code}-${idx}`}
              className="cursor-pointer rounded-lg border border-slate-200/60 p-4 transition hover:border-slate-300"
              onClick={() => navigate(`/stock/${encodeURIComponent(item.code ?? "")}?m=CN`)}
            >
              <div className="font-mono text-sm text-slate-500">{item.trade_date ?? data?.trade_date}</div>
              <div className="mt-1 font-semibold">{item.name ?? "—"}</div>
              <div className="font-mono text-xs text-slate-500">{item.code}</div>
              <p className="mt-2 line-clamp-3 text-xs text-slate-600">{item.reason ?? "—"}</p>
            </article>
          ))}
          {!items.length ? (
            <p className="col-span-full py-12 text-center text-slate-500">暂无龙虎榜数据</p>
          ) : null}
        </div>
        {pageCount > 1 ? (
          <div className="mt-4 flex items-center justify-end gap-2 text-sm">
            <button
              type="button"
              className="btn btn-sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              上一页
            </button>
            <span className="text-slate-500">{page} / {pageCount}</span>
            <button
              type="button"
              className="btn btn-sm"
              disabled={page >= pageCount}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
