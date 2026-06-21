import type { StockRealtime } from "../../types/stock";

function pctClass(value?: number) {
  if (value == null) return "text-slate-500";
  return value >= 0 ? "text-emerald-600" : "text-rose-600";
}

function fmtNum(value?: number | null, digits = 2) {
  if (value == null || Number.isNaN(value)) return "--";
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function StockQuoteCard({ quote }: { quote: StockRealtime }) {
  const name = quote.name || quote.code || "—";
  const change = quote.change_pct;

  return (
    <section className="glass-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">{name}</h2>
          <p className="text-sm text-slate-500">
            {quote.code}
            {quote.industry ? ` · ${quote.industry}` : ""}
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold tabular-nums">{fmtNum(quote.price)}</div>
          <div className={`text-sm font-semibold tabular-nums ${pctClass(change)}`}>
            {change != null ? (
              <>
                {change >= 0 ? "+" : ""}
                {change.toFixed(2)}%
                {quote.change_amount != null ? (
                  <span className="ml-2">
                    ({change >= 0 ? "+" : ""}
                    {quote.change_amount.toFixed(2)})
                  </span>
                ) : null}
              </>
            ) : (
              "--"
            )}
          </div>
        </div>
      </div>

      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-slate-500">今开</dt>
          <dd className="font-mono">{fmtNum(quote.open_price)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">最高</dt>
          <dd className="font-mono">{fmtNum(quote.high_price)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">最低</dt>
          <dd className="font-mono">{fmtNum(quote.low_price)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">昨收</dt>
          <dd className="font-mono">{fmtNum(quote.prev_close)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">成交量</dt>
          <dd className="font-mono">{fmtNum(quote.volume, 0)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">成交额</dt>
          <dd className="font-mono">{fmtNum(quote.amount, 0)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">PE</dt>
          <dd className="font-mono">{quote.pe ?? "--"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">PB</dt>
          <dd className="font-mono">{quote.pb ?? "--"}</dd>
        </div>
      </dl>
    </section>
  );
}
