import { Link } from "react-router-dom";
import type { WatchlistItem, WorkbenchSnapshot } from "../../types/workbench";

/* Surface: bg-zinc-900/50 ring-1 ring-zinc-800/50 rounded-xl p-5 */
function Section({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>
      {children}
    </div>
  );
}

function pctClass(value?: number) {
  if (value == null) return "";
  return value >= 0 ? "text-emerald-400" : "text-rose-400";
}

function healthColor(score?: number) {
  if (score == null) return "text-zinc-500";
  if (score >= 70) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-rose-400";
}

export function WatchlistPanel({
  items,
  market,
}: {
  items: WatchlistItem[];
  market: string;
}) {
  return (
    <Section className="p-5">
      <h3 className="mb-4 text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">
        自选股健康度
        {items.length > 0 && (
          <span className="ml-2 font-mono text-[10px] font-normal tracking-normal text-zinc-600">
            · {items.length} 只
          </span>
        )}
      </h3>
      {!items.length ? (
        <div className="flex flex-col items-center py-8">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-800/60 text-lg">📋</div>
          <p className="mt-3 text-sm text-zinc-500">暂无自选行情</p>
          <p className="mt-1 text-xs text-zinc-600">请先在自选股中添加标的</p>
        </div>
      ) : (
        <div className="divide-y divide-zinc-800/40">
          {items.map((item) => (
            <Link
              key={item.code}
              to={`/stock/${item.code}?m=${market}`}
              className="flex items-center justify-between px-1 py-2.5 transition-colors hover:bg-zinc-800/30 first:pt-0 last:pb-0"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-semibold text-zinc-200">
                    {item.name ?? item.code}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-zinc-600">{item.code}</span>
                </div>
                <div className="mt-0.5 flex items-center gap-2">
                  <span className="font-mono text-sm tabular-nums text-zinc-400">
                    {item.price ?? "--"}
                  </span>
                  <span className={`font-mono text-xs font-semibold tabular-nums ${pctClass(item.change_pct)}`}>
                    {item.change_pct != null
                      ? `${item.change_pct >= 0 ? "+" : ""}${item.change_pct.toFixed(2)}%`
                      : ""}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-lg font-bold font-mono tabular-nums ${healthColor(item.health_score)}`}>
                  {item.health_score ?? "--"}
                </div>
                <div className="text-[10px] uppercase tracking-[0.1em] text-zinc-600">健康度</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </Section>
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
    <Section className="p-5">
      <h3 className="mb-4 text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">
        AI Top 推荐
      </h3>
      {!items.length ? (
        <p className="text-sm text-zinc-500">{rec?.note ?? "暂无推荐"}</p>
      ) : (
        <div className="space-y-2">
          {items.slice(0, 3).map((item) => (
            <div key={item.code} className="rounded-lg bg-zinc-800/40 px-3 py-2.5">
              {item.code ? (
                <Link
                  to={`/stock/${item.code}?m=${market}`}
                  className="text-sm font-semibold text-emerald-400 transition-colors hover:text-emerald-300"
                >
                  {item.name ?? item.code}
                </Link>
              ) : (
                <span className="text-sm font-semibold text-zinc-200">{item.name ?? item.code}</span>
              )}
              {item.reason && (
                <p className="mt-0.5 text-xs leading-relaxed text-zinc-500">{item.reason}</p>
              )}
              {item.score != null && (
                <div className="mt-1 flex items-center gap-1.5">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-zinc-700/60">
                    <div className="h-full rounded-full bg-emerald-500/40" style={{ width: `${Math.min(item.score * 10, 100)}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-zinc-500">{(item.score * 10).toFixed(0)}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

export function ReviewPanel({ data }: { data: WorkbenchSnapshot }) {
  const strip = data.review_strip;
  if (!strip?.items?.length && !strip?.pending) return null;
  return (
    <Section className="p-5">
      <div className="mb-4 flex items-center gap-2">
        <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">待复核决策</h3>
        {strip.pending != null && (
          <span className="rounded bg-amber-500/15 px-1.5 py-0.5 font-mono text-[10px] text-amber-400">
            {strip.pending}
          </span>
        )}
      </div>
      <div className="space-y-2">
        {(strip.items ?? []).slice(0, 5).map((item) => (
          <div key={item.decision_id ?? item.subject} className="rounded-lg bg-zinc-800/40 px-3 py-2">
            <p className="text-sm font-semibold text-zinc-200">{item.subject ?? item.decision_id}</p>
            <p className="mt-0.5 text-xs text-zinc-500">{item.reason}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}