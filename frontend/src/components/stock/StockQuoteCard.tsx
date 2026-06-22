import type { StockRealtime } from "../../types/stock";

function pctClass(value?: number) {
  if (value == null) return "text-zinc-500";
  return value >= 0 ? "text-emerald-400" : "text-rose-400";
}

function fmtNum(value?: number | null, digits = 2) {
  if (value == null || Number.isNaN(value)) return "--";
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

export function StockQuoteCard({ quote }: { quote: StockRealtime }) {
  const name = quote.name || quote.code || "—";
  const change = quote.change_pct;

  return (
    <Panel className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-zinc-100">{name}</h2>
          <p className="mt-0.5 text-sm text-zinc-500">
            <span className="font-mono text-xs">{quote.code}</span>
            {quote.industry ? <span className="ml-2">{quote.industry}</span> : ""}
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-black font-mono tabular-nums text-zinc-100">{fmtNum(quote.price)}</div>
          <div className={`text-sm font-semibold font-mono tabular-nums ${pctClass(change)}`}>
            {change != null ? (
              <>{change >= 0 ? "+" : ""}{change.toFixed(2)}%
                {quote.change_amount != null ? (
                  <span className="ml-1">({change >= 0 ? "+" : ""}{quote.change_amount.toFixed(2)})</span>
                ) : null}</>
            ) : "--"}
          </div>
        </div>
      </div>

      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["今开", fmtNum(quote.open_price)],
          ["最高", fmtNum(quote.high_price)],
          ["最低", fmtNum(quote.low_price)],
          ["昨收", fmtNum(quote.prev_close)],
          ["成交量", fmtNum(quote.volume, 0)],
          ["成交额", fmtNum(quote.amount, 0)],
          ["PE", quote.pe ?? "--"],
          ["PB", quote.pb ?? "--"],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-lg bg-zinc-800/40 px-3 py-2">
            <dt className="text-[10px] font-mono uppercase tracking-[0.1em] text-zinc-500">{String(label)}</dt>
            <dd className="mt-0.5 font-mono tabular-nums text-zinc-200">{String(value)}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}