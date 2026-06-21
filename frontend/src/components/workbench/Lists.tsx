import { Link } from "react-router-dom";
import type { WatchlistItem, WorkbenchSnapshot } from "../../types/workbench";

function pctClass(value?: number) {
  if (value == null) return "";
  return value >= 0 ? "text-emerald-600" : "text-rose-600";
}

export function WatchlistPanel({
  items,
  market,
}: {
  items: WatchlistItem[];
  market: string;
}) {
  return (
    <section className="glass-card p-5">
      <h3 className="mb-3 font-bold">自选股健康度</h3>
      {!items.length ? (
        <p className="text-sm text-slate-500">暂无自选行情，请先在经典版自选股中添加。</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.code}>
              <Link
                to={`/stock/${item.code}?m=${market}`}
                className="flex items-center justify-between rounded-xl border border-slate-200/80 bg-white/50 px-3 py-2 transition hover:border-brand dark:border-slate-700 dark:bg-slate-900/40"
              >
                <div>
                  <div className="font-semibold">
                    {item.name ?? item.code}{" "}
                    <span className="text-xs text-slate-500">{item.code}</span>
                  </div>
                  <div className="text-sm">
                    <span>{item.price ?? "--"}</span>
                    <span className={`ml-2 font-semibold ${pctClass(item.change_pct)}`}>
                      {item.change_pct != null
                        ? `${item.change_pct >= 0 ? "+" : ""}${item.change_pct.toFixed(2)}%`
                        : ""}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className={`text-lg font-bold ${
                      (item.health_score ?? 0) >= 55 ? "text-emerald-600" : "text-rose-600"
                    }`}
                  >
                    {item.health_score ?? "--"}
                  </div>
                  <div className="text-xs text-slate-500">健康度</div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function RecommendPanel({
  data,
  market = "CN",
}: {
  data: WorkbenchSnapshot;
  market?: string;
}) {
  const rec = data.recommendations_preview;
  const items = rec?.items ?? [];
  return (
    <section className="glass-card p-5">
      <h3 className="mb-3 font-bold">AI Top 推荐</h3>
      {!items.length ? (
        <p className="text-sm text-slate-500">{rec?.note ?? "暂无推荐"}</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {items.slice(0, 3).map((item) => (
            <li key={item.code} className="rounded-lg bg-slate-900/5 px-3 py-2 dark:bg-white/5">
              {item.code ? (
                <Link
                  to={`/stock/${item.code}?m=${market}`}
                  className="font-semibold text-brand hover:underline"
                >
                  {item.name ?? item.code}
                </Link>
              ) : (
                <strong>{item.name ?? item.code}</strong>
              )}
              <div className="text-slate-500">{item.reason ?? ""}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ReviewPanel({ data }: { data: WorkbenchSnapshot }) {
  const strip = data.review_strip;
  if (!strip?.items?.length && !strip?.pending) return null;
  return (
    <section className="glass-card p-5">
      <h3 className="mb-2 font-bold">
        待复核决策
        {strip.pending != null ? (
          <span className="ml-2 badge badge-outline">{strip.pending} 条</span>
        ) : null}
      </h3>
      <ul className="space-y-2 text-sm">
        {(strip.items ?? []).slice(0, 5).map((item) => (
          <li key={item.decision_id ?? item.subject}>
            <strong>{item.subject ?? item.decision_id}</strong>
            <div className="text-slate-500">{item.reason}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
