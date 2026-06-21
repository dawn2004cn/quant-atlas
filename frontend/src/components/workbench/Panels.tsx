import type { WorkbenchSnapshot } from "../../types/workbench";

function pctClass(value?: number) {
  if (value == null) return "";
  return value >= 0 ? "text-emerald-600" : "text-rose-600";
}

export function SentimentHero({ data }: { data: WorkbenchSnapshot }) {
  const sentiment = data.market_sentiment ?? {};
  const panorama = data.market_panorama ?? {};
  const gainers = sentiment.stats?.gainers ?? panorama.up ?? 0;
  const neutral = sentiment.stats?.neutral ?? panorama.flat ?? 0;
  const losers = sentiment.stats?.losers ?? panorama.down ?? 0;

  return (
    <section className="glass-card p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="text-4xl" aria-hidden>
            {sentiment.emoji ?? "📊"}
          </span>
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              市场天气
            </p>
            <h2 className="text-xl font-bold">
              {sentiment.description ?? sentiment.level ?? "行情观测中"}
            </h2>
            <p className="text-sm text-slate-500">
              情绪分 {sentiment.score ?? "--"} · 更新 {data.generated_at ?? "--"}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="rounded-xl bg-emerald-50 px-4 py-3 dark:bg-emerald-950/40">
            <div className="text-2xl font-bold text-emerald-600">{gainers}</div>
            <div className="text-xs text-slate-500">上涨</div>
          </div>
          <div className="rounded-xl bg-slate-100 px-4 py-3 dark:bg-slate-800/60">
            <div className="text-2xl font-bold">{neutral}</div>
            <div className="text-xs text-slate-500">平盘</div>
          </div>
          <div className="rounded-xl bg-rose-50 px-4 py-3 dark:bg-rose-950/40">
            <div className="text-2xl font-bold text-rose-600">{losers}</div>
            <div className="text-xs text-slate-500">下跌</div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function DecisionPanel({ data }: { data: WorkbenchSnapshot }) {
  const decision = data.decision ?? {};
  return (
    <section className="glass-card p-6 text-center">
      <p className="text-sm font-semibold text-slate-500">今日决策</p>
      <div className="my-2 text-5xl font-black text-brand">{decision.score ?? "--"}</div>
      <p className="text-lg font-bold">{decision.stance ?? "中性"}</p>
      <p className="text-sm text-slate-500">{decision.action ?? ""}</p>
      {decision.reasons?.length ? (
        <ul className="mt-4 space-y-1 text-left text-sm text-slate-600 dark:text-slate-300">
          {decision.reasons.map((reason: string) => (
            <li key={reason}>• {reason}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function MacroRow({ data }: { data: WorkbenchSnapshot }) {
  const items = data.macro_indices ?? [];
  if (!items.length) return null;
  return (
    <section className="flex gap-3 overflow-x-auto pb-1">
      {items.map((item: NonNullable<WorkbenchSnapshot["macro_indices"]>[number]) => (
        <div key={item.code ?? item.label} className="glass-card min-w-[140px] shrink-0 p-4">
          <p className="text-xs font-bold uppercase text-slate-500">{item.label}</p>
          <p className="mt-1 text-lg font-bold">{item.price ?? "--"}</p>
          <p className={`text-sm font-semibold ${pctClass(item.change_pct)}`}>
            {item.change_pct != null
              ? `${item.change_pct >= 0 ? "+" : ""}${item.change_pct.toFixed(2)}%`
              : "--"}
          </p>
        </div>
      ))}
    </section>
  );
}

export function HealthBanner({ data }: { data: WorkbenchSnapshot }) {
  const banner = data.health_banner;
  if (!banner?.headline) return null;
  const level = banner.level ?? "ok";
  const tone =
    level === "critical"
      ? "border-rose-300 bg-rose-50 dark:border-rose-900 dark:bg-rose-950/30"
      : level === "warning"
        ? "border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30"
        : "border-emerald-300 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30";
  return (
    <div className={`rounded-2xl border px-4 py-3 text-sm ${tone}`}>
      <strong>{banner.headline}</strong>
      {banner.summary ? <span className="ml-2 text-slate-600">{banner.summary}</span> : null}
    </div>
  );
}
