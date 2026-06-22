import type { WorkbenchSnapshot } from "../../types/workbench";

/* Surface levels for this dashboard:
 * Level 0 — bare data: plain text, no bg
 * Level 1 — section bg: rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50
 * Level 2 — elevated card: bg-zinc-900 ring-1 ring-zinc-800
 * Level 3 — tooltip/popover: bg-zinc-800/95 ring-1 ring-zinc-700/60
 */

function Section({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>
      {children}
    </div>
  );
}

export function SentimentHero({ data }: { data: WorkbenchSnapshot }) {
  const sentiment = data.market_sentiment ?? {};
  const panorama = data.market_panorama ?? {};
  const gainers = sentiment.stats?.gainers ?? panorama.up ?? 0;
  const neutral = sentiment.stats?.neutral ?? panorama.flat ?? 0;
  const losers = sentiment.stats?.losers ?? panorama.down ?? 0;

  return (
    <Section className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-zinc-800/80 text-2xl">
            {sentiment.emoji ?? "📊"}
          </div>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.15em] text-zinc-500">
              Market Weather
            </p>
            <h2 className="mt-0.5 text-xl font-bold text-zinc-100">
              {sentiment.description ?? sentiment.level ?? "观测中"}
            </h2>
            <div className="mt-0.5 flex items-center gap-3 text-xs text-zinc-500">
              <span>情绪分 <span className="font-semibold text-zinc-300">{sentiment.score ?? "--"}</span></span>
              <span className="h-3 w-px bg-zinc-700/60" />
              <span className="font-mono text-[10px]">{data.generated_at ?? ""}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <div className="min-w-[72px] rounded-lg bg-emerald-500/8 px-4 py-2.5 text-center ring-1 ring-emerald-500/10">
            <div className="text-lg font-bold font-mono tabular-nums text-emerald-400">{gainers}</div>
            <div className="text-[10px] uppercase tracking-[0.1em] text-emerald-400/60">上涨</div>
          </div>
          <div className="min-w-[72px] rounded-lg bg-zinc-800/50 px-4 py-2.5 text-center">
            <div className="text-lg font-bold font-mono tabular-nums text-zinc-300">{neutral}</div>
            <div className="text-[10px] uppercase tracking-[0.1em] text-zinc-500">平盘</div>
          </div>
          <div className="min-w-[72px] rounded-lg bg-rose-500/8 px-4 py-2.5 text-center ring-1 ring-rose-500/10">
            <div className="text-lg font-bold font-mono tabular-nums text-rose-400">{losers}</div>
            <div className="text-[10px] uppercase tracking-[0.1em] text-rose-400/60">下跌</div>
          </div>
        </div>
      </div>
    </Section>
  );
}

export function DecisionPanel({ data }: { data: WorkbenchSnapshot }) {
  const decision = data.decision ?? {};
  const score = decision.score ?? 50;
  const isPositive = score >= 60;
  const isNegative = score <= 40;

  return (
    <Section className="p-5">
      <p className="text-[11px] font-mono uppercase tracking-[0.15em] text-zinc-500">
        Today's Decision
      </p>
      <div className="mt-2 flex flex-col items-center border-b border-zinc-800/60 pb-4">
        <div className={`text-5xl font-black font-mono tabular-nums ${
          isPositive ? "text-emerald-400" : isNegative ? "text-rose-400" : "text-zinc-100"
        }`}>
          {score}
        </div>
        <p className="mt-1 text-lg font-bold text-zinc-200">{decision.stance ?? "中性"}</p>
        <p className="text-sm text-zinc-500">{decision.action ?? ""}</p>
        {decision.confidence != null && (
          <div className="mt-2 flex items-center gap-2 text-xs text-zinc-500">
            <span>置信度</span>
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full bg-emerald-500/60"
                style={{ width: `${(decision.confidence * 100).toFixed(0)}%` }}
              />
            </div>
            <span className="font-mono text-zinc-400">{(decision.confidence * 100).toFixed(0)}%</span>
          </div>
        )}
      </div>
      {decision.reasons?.length ? (
        <ul className="mt-4 space-y-2">
          {decision.reasons.map((reason: string) => (
            <li key={reason} className="flex items-start gap-2 text-sm leading-relaxed text-zinc-400">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-zinc-600" />
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </Section>
  );
}

export function MacroRow({ data }: { data: WorkbenchSnapshot }) {
  const items = data.macro_indices ?? [];
  if (!items.length) return null;

  return (
    <Section className="flex gap-px divide-x divide-zinc-800/60 overflow-hidden">
      {items.map((item: NonNullable<WorkbenchSnapshot["macro_indices"]>[number]) => (
        <div key={item.code ?? item.label} className="flex flex-1 flex-col items-center px-4 py-3">
          <div className="text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
            {item.label}
          </div>
          <div className="mt-0.5 text-base font-bold font-mono tabular-nums text-zinc-200">
            {item.price ?? "--"}
          </div>
          <div className={`text-xs font-semibold font-mono tabular-nums ${
            item.change_pct != null
              ? item.change_pct >= 0 ? "text-emerald-400" : "text-rose-400"
              : "text-zinc-500"
          }`}>
            {item.change_pct != null
              ? `${item.change_pct >= 0 ? "+" : ""}${item.change_pct.toFixed(2)}%`
              : "--"}
          </div>
        </div>
      ))}
    </Section>
  );
}

export function HealthBanner({ data }: { data: WorkbenchSnapshot }) {
  const banner = data.health_banner;
  if (!banner?.headline) return null;
  const level = banner.level ?? "ok";
  const isCritical = level === "critical";
  const isWarning = level === "warning";

  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${
      isCritical
        ? "border-rose-500/20 bg-rose-500/5"
        : isWarning
          ? "border-amber-500/20 bg-amber-500/5"
          : "border-emerald-500/20 bg-emerald-500/5"
    }`}>
      <div className="flex items-center gap-2">
        <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
          isCritical ? "bg-rose-500/20 text-rose-400" :
          isWarning ? "bg-amber-500/20 text-amber-400" :
          "bg-emerald-500/20 text-emerald-400"
        }`}>
          {isCritical ? "!" : isWarning ? "!" : "✓"}
        </span>
        <strong className={isCritical ? "text-rose-300" : isWarning ? "text-amber-300" : "text-emerald-300"}>
          {banner.headline}
        </strong>
        {banner.summary ? <span className="text-zinc-500">{banner.summary}</span> : null}
      </div>
    </div>
  );
}