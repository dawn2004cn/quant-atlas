import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetchV1 } from "../lib/api";
import { DEMO_STOCKS } from "../lib/demoCatalog";

type StockHit = { symbol: string; name?: string; price?: number; market?: string };

type CommandItem = {
  id: string;
  kind: "stock" | "action";
  label: string;
  hint?: string;
  run: () => void;
};

const QUICK_ACTIONS: Array<{ id: string; label: string; hint: string; to: string }> = [
  { id: "act-desk", label: "今日操盘台", hint: "总览", to: "/" },
  { id: "act-watch", label: "自选股", hint: "Watchlist", to: "/self-stocks" },
  { id: "act-brief", label: "自选晨报", hint: "Briefing", to: "/watchlist-briefing" },
  { id: "act-ai", label: "AI 诊股", hint: "分析", to: "/ai-analysis" },
  { id: "act-select", label: "智能选股", hint: "选股", to: "/stock-selector" },
  { id: "act-panorama", label: "市场全景", hint: "行情", to: "/market-panorama" },
  { id: "act-coverage", label: "数据与市场说明", hint: "局限", to: "/market-coverage" },
  { id: "act-onboard", label: "使用偏好引导", hint: "Persona", to: "/onboarding" },
];

function normalizeHits(raw: unknown): StockHit[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((row) => {
      const r = row as Record<string, unknown>;
      const symbol = String(r.symbol ?? r.code ?? "").trim();
      if (!symbol) return null;
      return {
        symbol,
        name: r.name != null ? String(r.name) : undefined,
        price: typeof r.price === "number" ? r.price : undefined,
        market: r.market != null ? String(r.market) : "CN",
      };
    })
    .filter((x): x is StockHit => Boolean(x));
}

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<StockHit[]>([]);
  const [isDemoHits, setIsDemoHits] = useState(true);
  const [searching, setSearching] = useState(false);
  const [active, setActive] = useState(0);
  const debounceRef = useRef<number | undefined>(undefined);

  const go = useCallback(
    (to: string) => {
      onClose();
      navigate(to);
    },
    [navigate, onClose],
  );

  const items: CommandItem[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    const stockItems: CommandItem[] = (hits.length ? hits : DEMO_STOCKS.slice(0, 5).map((s) => ({
      symbol: s.symbol,
      name: s.name,
      price: s.price,
      market: "CN",
    }))).map((s) => ({
      id: `stock-${s.symbol}`,
      kind: "stock" as const,
      label: `${s.symbol} ${s.name ?? ""}`.trim(),
      hint: s.price != null ? `¥${s.price}` : "个股",
      run: () => go(`/stock/${encodeURIComponent(s.symbol)}?m=${encodeURIComponent(s.market || "CN")}`),
    }));

    const actions = QUICK_ACTIONS.filter((a) => {
      if (!q) return true;
      return a.label.toLowerCase().includes(q) || a.hint.toLowerCase().includes(q) || a.id.includes(q);
    }).map((a) => ({
      id: a.id,
      kind: "action" as const,
      label: a.label,
      hint: a.hint,
      run: () => go(a.to),
    }));

    // Prefer stocks when user typed a query that looks like a code/name search.
    if (q) return [...stockItems, ...actions];
    return [...actions.slice(0, 4), ...stockItems, ...actions.slice(4)];
  }, [go, hits, query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setHits([]);
    setIsDemoHits(true);
    setActive(0);
    const t = window.setTimeout(() => inputRef.current?.focus(), 20);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    setActive(0);
  }, [query, hits]);

  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    const q = query.trim();
    if (!q) {
      setHits([]);
      setIsDemoHits(true);
      setSearching(false);
      return;
    }
    debounceRef.current = window.setTimeout(async () => {
      setSearching(true);
      try {
        const data = await apiFetchV1<unknown>(`/stocks/search?q=${encodeURIComponent(q)}`);
        const next = normalizeHits(data);
        if (next.length) {
          setHits(next);
          setIsDemoHits(false);
        } else {
          setHits(
            DEMO_STOCKS.filter(
              (s) => s.symbol.includes(q) || (s.name ?? "").includes(q),
            ).map((s) => ({ symbol: s.symbol, name: s.name, price: s.price, market: "CN" })),
          );
          setIsDemoHits(true);
        }
      } catch {
        setHits(
          DEMO_STOCKS.filter(
            (s) => s.symbol.includes(q) || (s.name ?? "").includes(q),
          ).map((s) => ({ symbol: s.symbol, name: s.name, price: s.price, market: "CN" })),
        );
        setIsDemoHits(true);
      } finally {
        setSearching(false);
      }
    }, 220);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [open, query]);

  if (!open) return null;

  const clamped = items.length ? Math.min(active, items.length - 1) : 0;

  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center bg-black/60 px-4 pt-[12vh] backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="命令面板">
      <button type="button" className="absolute inset-0 cursor-default" aria-label="关闭命令面板" onClick={onClose} />
      <div className="relative z-[81] w-full max-w-xl overflow-hidden rounded-2xl border border-zinc-700/70 bg-zinc-950 shadow-2xl ring-1 ring-zinc-800">
        <div className="flex items-center gap-3 border-b border-zinc-800 px-4 py-3">
          <span className="text-xs font-mono text-zinc-500">⌘K</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((i) => Math.min(i + 1, Math.max(items.length - 1, 0)));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter" && items[clamped]) {
                e.preventDefault();
                items[clamped].run();
              }
            }}
            placeholder="搜股票代码/名称，或跳转页面…"
            className="flex-1 bg-transparent text-sm text-zinc-100 placeholder:text-zinc-600 outline-none"
          />
          {searching ? <span className="text-[10px] font-mono text-zinc-500">搜索中</span> : null}
        </div>
        {isDemoHits && query.trim() ? (
          <p className="border-b border-zinc-800/80 px-4 py-1.5 text-[11px] font-mono text-amber-400/90">
            演示候选 · 行情源未返回结果
          </p>
        ) : null}
        <ul className="max-h-[50vh] overflow-auto py-2">
          {items.length === 0 ? (
            <li className="px-4 py-6 text-center text-sm text-zinc-500">无匹配项</li>
          ) : (
            items.map((item, idx) => (
              <li key={item.id}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(idx)}
                  onClick={() => item.run()}
                  className={`flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                    idx === clamped ? "bg-emerald-500/10 text-emerald-200" : "text-zinc-200 hover:bg-zinc-900"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] font-mono uppercase text-zinc-400">
                      {item.kind === "stock" ? "股票" : "跳转"}
                    </span>
                    <span>{item.label}</span>
                  </span>
                  {item.hint ? <span className="font-mono text-[11px] text-zinc-500">{item.hint}</span> : null}
                </button>
              </li>
            ))
          )}
        </ul>
        <div className="flex items-center justify-between border-t border-zinc-800 px-4 py-2 text-[10px] font-mono text-zinc-600">
          <span>↑↓ 选择 · Enter 确认 · Esc 关闭</span>
          <span>个股 / 自选 / 诊股 / 晨报</span>
        </div>
      </div>
    </div>
  );
}

/** Global ⌘/Ctrl+K listener + open state for Layout. */
export function useCommandPaletteHotkey(onOpen: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpen();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onOpen]);
}
