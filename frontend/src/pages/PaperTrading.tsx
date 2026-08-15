import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { fetchPaperTradingStatus } from "../lib/api";
import { DEMO_STOCKS } from "../lib/demoCatalog";
import {
  applyPaperOrder,
  loadPaperBook,
  paperEquity,
  PAPER_INITIAL_CASH,
  resetPaperBook,
  type PaperBook,
} from "../lib/paperBook";

function fmtMoney(n: number): string {
  return n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function fmtPct(n: number): string {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${(n * 100).toFixed(2)}%`;
}

export function PaperTradingPage() {
  const [book, setBook] = useState<PaperBook>(() => loadPaperBook());
  const [symbol, setSymbol] = useState(DEMO_STOCKS[0]?.symbol ?? "600519");
  const [name, setName] = useState(DEMO_STOCKS[0]?.name ?? "");
  const [price, setPrice] = useState(DEMO_STOCKS[0]?.price ?? 100);
  const [qty, setQty] = useState(100);
  const [msg, setMsg] = useState<string | null>(null);

  const { data: factoryStatus } = useSWR("paper-trading-factory", () => fetchPaperTradingStatus(), {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  const equity = paperEquity(book);
  const pnl = equity - PAPER_INITIAL_CASH;
  const pnlPct = PAPER_INITIAL_CASH > 0 ? pnl / PAPER_INITIAL_CASH : 0;
  const queue = factoryStatus?.queue ?? factoryStatus?.items ?? [];
  const factoryLive = Boolean(factoryStatus?.status) || queue.length > 0;

  const picks = useMemo(
    () =>
      DEMO_STOCKS.slice(0, 6).map((s) => ({
        symbol: s.symbol,
        name: s.name,
        price: s.price && s.price > 0 ? s.price : 100,
      })),
    [],
  );

  function pickDemo(s: { symbol: string; name?: string; price: number }) {
    setSymbol(s.symbol);
    setName(s.name ?? "");
    setPrice(s.price);
    setMsg(null);
  }

  function submit(side: "buy" | "sell") {
    const result = applyPaperOrder(book, { side, symbol, name, qty, price: Number(price) });
    if (!result.ok) {
      setMsg(result.reason);
      return;
    }
    setBook(result.book);
    setMsg(side === "buy" ? "模拟买入已记账" : "模拟卖出已记账");
  }

  function onReset() {
    setBook(resetPaperBook());
    setMsg("已重置模拟账户");
  }

  return (
    <div className="mx-auto max-w-[960px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.portfolio} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Paper Trading</div>
          <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">模拟交易</h1>
          <p className="mt-1 text-sm text-zinc-500">本地记账练手，不连接真实券商；可导入影子账户做复盘。</p>
          <DemoBanner show={!factoryLive} />
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onReset}
            className="rounded-lg px-3 py-1.5 text-xs text-zinc-400 ring-1 ring-zinc-700/60 hover:bg-zinc-800"
          >
            重置账户
          </button>
          <Link
            to="/shadow-account"
            className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30"
          >
            影子复盘
          </Link>
        </div>
      </div>

      <section className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-zinc-900/50 p-4 ring-1 ring-zinc-800/50">
          <div className="text-[11px] uppercase tracking-wide text-zinc-500">权益</div>
          <div className="mt-1 font-mono text-xl text-zinc-100">¥{fmtMoney(equity)}</div>
        </div>
        <div className="rounded-xl bg-zinc-900/50 p-4 ring-1 ring-zinc-800/50">
          <div className="text-[11px] uppercase tracking-wide text-zinc-500">现金</div>
          <div className="mt-1 font-mono text-xl text-zinc-100">¥{fmtMoney(book.cash)}</div>
        </div>
        <div className="rounded-xl bg-zinc-900/50 p-4 ring-1 ring-zinc-800/50">
          <div className="text-[11px] uppercase tracking-wide text-zinc-500">盈亏</div>
          <div className={`mt-1 font-mono text-xl ${pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
            {fmtPct(pnlPct)} · ¥{fmtMoney(pnl)}
          </div>
        </div>
      </section>

      <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
        <h2 className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">下单</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {picks.map((s) => (
            <button
              key={s.symbol}
              type="button"
              onClick={() => pickDemo(s)}
              className={`rounded-lg px-2.5 py-1 text-xs ring-1 ${
                symbol === s.symbol
                  ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30"
                  : "text-zinc-400 ring-zinc-700/50 hover:bg-zinc-800"
              }`}
            >
              {s.symbol} {s.name}
            </button>
          ))}
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <label className="text-xs text-zinc-500">
            代码
            <input
              className="mt-1 w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 font-mono text-sm text-zinc-200"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
            />
          </label>
          <label className="text-xs text-zinc-500">
            名称
            <input
              className="mt-1 w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="text-xs text-zinc-500">
            价格
            <input
              type="number"
              min={0.01}
              step={0.01}
              className="mt-1 w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 font-mono text-sm text-zinc-200"
              value={price}
              onChange={(e) => setPrice(Number(e.target.value))}
            />
          </label>
          <label className="text-xs text-zinc-500">
            数量
            <input
              type="number"
              min={1}
              step={100}
              className="mt-1 w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 font-mono text-sm text-zinc-200"
              value={qty}
              onChange={(e) => setQty(Number(e.target.value))}
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => submit("buy")}
            className="rounded-lg bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-400 ring-1 ring-emerald-500/30"
          >
            模拟买入
          </button>
          <button
            type="button"
            onClick={() => submit("sell")}
            className="rounded-lg bg-rose-500/10 px-4 py-2 text-sm font-semibold text-rose-300 ring-1 ring-rose-500/25"
          >
            模拟卖出
          </button>
          {msg ? <span className="self-center text-xs text-zinc-400">{msg}</span> : null}
        </div>
      </section>

      <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
        <h2 className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">持仓</h2>
        {book.positions.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">暂无持仓。点上方样本股试一笔买入。</p>
        ) : (
          <div className="mt-3 divide-y divide-zinc-800/80">
            {book.positions.map((p) => {
              const mv = p.qty * p.lastPrice;
              const cost = p.qty * p.avgPrice;
              const uPnl = mv - cost;
              return (
                <div key={p.symbol} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                  <div>
                    <Link className="font-mono text-emerald-400" to={`/stock/${encodeURIComponent(p.symbol)}?m=CN`}>
                      {p.symbol}
                    </Link>
                    <span className="ml-2 text-zinc-300">{p.name || "—"}</span>
                    <div className="mt-0.5 font-mono text-[11px] text-zinc-500">
                      {p.qty} 股 · 成本 {p.avgPrice} · 现价 {p.lastPrice}
                    </div>
                  </div>
                  <div className={`font-mono text-xs ${uPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    ¥{fmtMoney(uPnl)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
        <h2 className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">最近成交</h2>
        {book.trades.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">尚无成交记录。</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm">
            {book.trades.slice(0, 12).map((t) => (
              <li key={t.id} className="flex flex-wrap gap-2 text-zinc-300">
                <span className={t.side === "buy" ? "text-emerald-400" : "text-rose-300"}>
                  {t.side === "buy" ? "买" : "卖"}
                </span>
                <span className="font-mono">{t.symbol}</span>
                <span className="text-zinc-500">
                  {t.qty}@{t.price}
                </span>
                <span className="font-mono text-[11px] text-zinc-600">{t.at.replace("T", " ").slice(0, 19)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {factoryLive ? (
        <p className="text-xs text-zinc-600">
          工厂影子队列状态：{factoryStatus?.status || "running"}（{queue.length} 项）— 与本页本地账本相互独立。
        </p>
      ) : (
        <p className="text-xs text-zinc-600">
          本地模拟与 Alpha 工厂 paper-trading 队列解耦；导入真实成交请用{" "}
          <Link className="text-emerald-400/90 hover:underline" to="/shadow-account">
            影子账户
          </Link>
          。
        </p>
      )}
    </div>
  );
}
