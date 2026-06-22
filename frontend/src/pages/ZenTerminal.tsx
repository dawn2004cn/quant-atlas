import { useState, useCallback, useRef } from "react";
import { apiFetchV1 } from "../lib/api";

type StockResult = { symbol: string; name?: string; price?: number };

export default function ZenTerminal() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockResult[]>([]);
  const [orderSymbol, setOrderSymbol] = useState("");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState("");
  const [orderType, setOrderType] = useState<"market" | "limit">("market");
  const [price, setPrice] = useState("");
  const [log, setLog] = useState<string[]>([]);
  const [searching, setSearching] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const debounceRef = useRef<number | undefined>(undefined);

  const handleSearch = useCallback((q: string) => {
    setQuery(q);
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    if (!q.trim()) { setResults([]); return; }
    debounceRef.current = window.setTimeout(async () => {
      setSearching(true);
      try {
        const data = await apiFetchV1<StockResult[]>(`/stocks/search?q=${encodeURIComponent(q.trim())}`);
        setResults(Array.isArray(data) ? data : []);
      } catch { setResults([]); }
      setSearching(false);
    }, 300);
  }, []);

  const selectStock = (s: StockResult) => {
    setOrderSymbol(s.symbol);
    setResults([]);
    setQuery(`${s.symbol} ${s.name ?? ""}`);
    appendLog(`已选标的: ${s.symbol}`);
  };

  const placeOrder = async () => {
    if (!orderSymbol || !quantity) return;
    setSubmitting(true);
    try {
      const body: Record<string, unknown> = { symbol: orderSymbol, side, quantity: Number(quantity), order_type: orderType };
      if (orderType === "limit") body.price = Number(price);
      await apiFetchV1("/orders/place", { method: "POST", body: JSON.stringify(body) });
      appendLog(`订单已提交: ${side.toUpperCase()} ${quantity} ${orderSymbol}${orderType === "limit" ? ` @ ${price}` : ""}`);
      setQuantity(""); setPrice("");
    } catch (e: unknown) {
      appendLog(`下单失败: ${e instanceof Error ? e.message : "未知错误"}`);
    }
    setSubmitting(false);
  };

  const appendLog = (msg: string) => setLog((prev) => [...prev.slice(-99), `[${new Date().toLocaleTimeString()}] ${msg}`]);

  return (
    <div className="space-y-5">
      <h1 className="page-title">禅终端</h1>
      <div className="grid gap-5 md:grid-cols-2">
        <div className="quant-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider">快速查询</h2>
          <div className="relative">
            <input ref={inputRef} type="text" className="w-full bg-[var(--quant-surface)] border border-[var(--quant-border)] rounded-lg px-4 py-3 text-lg font-mono outline-none focus:border-[var(--quant-accent)] transition-colors" placeholder="输入股票代码或名称..." value={query} onChange={(e) => handleSearch(e.target.value)} />
            {searching ? <div className="absolute right-3 top-3 text-xs text-[var(--quant-muted)]">搜索中...</div> : null}
            {results.length > 0 ? (
              <div className="absolute top-full left-0 right-0 mt-1 bg-[var(--quant-card-bg)] border border-[var(--quant-border)] rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
                {results.map((s) => (
                  <button key={s.symbol} type="button" className="w-full text-left px-4 py-2 text-sm hover:bg-[var(--quant-surface)] transition-colors flex items-center justify-between" onClick={() => selectStock(s)}>
                    <span className="mono font-medium">{s.symbol}</span>
                    <span className="text-[var(--quant-muted)]">{s.name ?? ""} {s.price ? `¥${s.price.toFixed(2)}` : ""}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          {orderSymbol ? (
            <div className="quant-card p-4 space-y-3 bg-[var(--quant-surface)]">
              <div className="flex items-center justify-between">
                <span className="mono font-bold text-lg">{orderSymbol}</span>
                <div className="flex gap-1">
                  <button type="button" className={`px-3 py-1 text-sm rounded ${side === "buy" ? "bg-green-500 text-white" : "bg-[var(--quant-border)] text-[var(--quant-muted)]"}`} onClick={() => setSide("buy")}>买入</button>
                  <button type="button" className={`px-3 py-1 text-sm rounded ${side === "sell" ? "bg-red-500 text-white" : "bg-[var(--quant-border)] text-[var(--quant-muted)]"}`} onClick={() => setSide("sell")}>卖出</button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><div className="text-xs text-[var(--quant-muted)] mb-1">数量</div><input type="number" className="w-full bg-[var(--quant-card-bg)] border border-[var(--quant-border)] rounded px-3 py-2 text-sm font-mono outline-none focus:border-[var(--quant-accent)]" value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="100" /></div>
                <div><div className="text-xs text-[var(--quant-muted)] mb-1">订单类型</div><select className="w-full bg-[var(--quant-card-bg)] border border-[var(--quant-border)] rounded px-3 py-2 text-sm font-mono outline-none focus:border-[var(--quant-accent)]" value={orderType} onChange={(e) => setOrderType(e.target.value as "market" | "limit")}><option value="market">市价单</option><option value="limit">限价单</option></select></div>
                {orderType === "limit" ? (
                  <div className="col-span-2"><div className="text-xs text-[var(--quant-muted)] mb-1">限价</div><input type="number" step="0.01" className="w-full bg-[var(--quant-card-bg)] border border-[var(--quant-border)] rounded px-3 py-2 text-sm font-mono outline-none focus:border-[var(--quant-accent)]" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="0.00" /></div>
                ) : null}
              </div>
              <button type="button" className={`w-full py-2 rounded-lg font-medium text-sm transition-colors ${submitting ? "opacity-50" : ""} ${side === "buy" ? "bg-green-500 hover:bg-green-600 text-white" : "bg-red-500 hover:bg-red-600 text-white"}`} disabled={submitting || !quantity} onClick={placeOrder}>{submitting ? "提交中..." : `${side === "buy" ? "买入" : "卖出"} ${orderSymbol}`}</button>
            </div>
          ) : null}
        </div>
        <div className="quant-card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider">操作日志</h2>
          <div className="bg-black/80 rounded-lg p-4 h-80 overflow-y-auto font-mono text-xs leading-relaxed">
            {log.length === 0 ? <div className="text-[var(--quant-muted)]">等待操作...</div> : log.map((entry, i) => (
              <div key={i} className="text-green-400/90 py-0.5">{entry}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
