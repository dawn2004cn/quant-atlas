/* Self-stocks (watchlist) types */

export type Watchlist = {
  id: number;
  name: string;
  description?: string;
  stock_count?: number;
  stocks?: WatchlistStock[];
};

export type WatchlistStock = {
  symbol: string;
  name?: string;
  price?: number;
  change_pct?: number;
  health_score?: number;
  priority?: number;
  risk_level?: string;
  amount?: number;
  industry?: string;
};

export type WatchlistSummary = {
  total: number;
  avg_health: number;
  strong_count: number;
  risk_count: number;
  summary_text?: string;
};

export type WatchlistData = {
  items: WatchlistStock[];
  summary: WatchlistSummary;
  groups?: WatchlistGroup[];
  generated_at?: string;
};

export type WatchlistGroup = {
  id: number;
  name: string;
  stock_count: number;
};

/* Self-Stocks page-specific */
export type SelfStocksState = {
  groups: WatchlistGroup[];
  activeGroupId: number | null;
  stocks: WatchlistStock[];
  summary: WatchlistSummary | null;
  sortBy: "priority" | "health" | "change" | "risk" | "amount";
  searchQuery: string;
};