/** Client-side paper trading book for retail self-test (not live brokerage). */

export type PaperTrade = {
  id: string;
  side: "buy" | "sell";
  symbol: string;
  name?: string;
  qty: number;
  price: number;
  at: string;
};

export type PaperPosition = {
  symbol: string;
  name?: string;
  qty: number;
  avgPrice: number;
  lastPrice: number;
};

export type PaperBook = {
  cash: number;
  positions: PaperPosition[];
  trades: PaperTrade[];
  updatedAt: string;
};

const STORAGE_KEY = "qa_paper_book_v1";
export const PAPER_INITIAL_CASH = 1_000_000;

export function emptyPaperBook(cash = PAPER_INITIAL_CASH): PaperBook {
  return {
    cash,
    positions: [],
    trades: [],
    updatedAt: new Date().toISOString(),
  };
}

export function loadPaperBook(): PaperBook {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyPaperBook();
    const parsed = JSON.parse(raw) as PaperBook;
    if (typeof parsed.cash !== "number" || !Array.isArray(parsed.positions)) {
      return emptyPaperBook();
    }
    return {
      cash: parsed.cash,
      positions: parsed.positions ?? [],
      trades: Array.isArray(parsed.trades) ? parsed.trades.slice(0, 40) : [],
      updatedAt: parsed.updatedAt || new Date().toISOString(),
    };
  } catch {
    return emptyPaperBook();
  }
}

export function savePaperBook(book: PaperBook): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(book));
  } catch {
    // ignore quota
  }
}

export function resetPaperBook(): PaperBook {
  const book = emptyPaperBook();
  savePaperBook(book);
  return book;
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export function applyPaperOrder(
  book: PaperBook,
  input: {
    side: "buy" | "sell";
    symbol: string;
    name?: string;
    qty: number;
    price: number;
  },
): { ok: true; book: PaperBook } | { ok: false; reason: string } {
  const symbol = input.symbol.trim().toUpperCase();
  const qty = Math.floor(input.qty);
  const price = input.price;
  if (!symbol || qty <= 0 || !(price > 0)) {
    return { ok: false, reason: "请填写有效代码、数量与价格" };
  }

  const notional = qty * price;
  const positions = book.positions.map((p) => ({ ...p }));
  const idx = positions.findIndex((p) => p.symbol === symbol);
  let cash = book.cash;

  if (input.side === "buy") {
    if (notional > cash) return { ok: false, reason: "可用资金不足" };
    cash = round2(cash - notional);
    if (idx >= 0) {
      const cur = positions[idx];
      const totalQty = cur.qty + qty;
      cur.avgPrice = round2((cur.avgPrice * cur.qty + price * qty) / totalQty);
      cur.qty = totalQty;
      cur.lastPrice = price;
      if (input.name) cur.name = input.name;
    } else {
      positions.push({
        symbol,
        name: input.name,
        qty,
        avgPrice: price,
        lastPrice: price,
      });
    }
  } else {
    if (idx < 0 || positions[idx].qty < qty) {
      return { ok: false, reason: "可卖数量不足" };
    }
    cash = round2(cash + notional);
    positions[idx].qty -= qty;
    positions[idx].lastPrice = price;
    if (positions[idx].qty <= 0) positions.splice(idx, 1);
  }

  const trade: PaperTrade = {
    id: `t-${Date.now()}`,
    side: input.side,
    symbol,
    name: input.name,
    qty,
    price,
    at: new Date().toISOString(),
  };

  const next: PaperBook = {
    cash,
    positions,
    trades: [trade, ...book.trades].slice(0, 40),
    updatedAt: trade.at,
  };
  savePaperBook(next);
  return { ok: true, book: next };
}

export function paperEquity(book: PaperBook): number {
  const mv = book.positions.reduce((s, p) => s + p.qty * p.lastPrice, 0);
  return round2(book.cash + mv);
}
