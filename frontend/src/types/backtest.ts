export type TradeMarker = {
  date: string;
  price: number;
  side: "buy" | "sell";
  quantity?: number;
  pnl?: number;
};

export type BacktestRequest = {
  symbol: string;
  strategy_name: string;
  start: string;
  end: string;
  initial_capital: number;
  commission_rate?: number;
  slippage_bps?: number;
};

export type BacktestCompareRow = {
  strategy_name: string;
  status: "ok" | "error";
  total_return?: number;
  annual_return?: number;
  sharpe?: number;
  max_drawdown?: number;
  win_rate?: number;
  trade_count?: number;
  error?: string;
};

export type BacktestCompareResult = {
  symbol: string;
  start: string;
  end: string;
  initial_capital: number;
  comparisons: BacktestCompareRow[];
  winner?: string | null;
};

export type BacktestResult = Record<string, unknown>;

export type EquityPoint = {
  date: string;
  value: number;
};

export type MarketplaceListing = {
  listing_id?: string;
  token_id?: string;
  seller_id?: number;
  reputation_cost?: number;
  price_tokens?: number;
  signal_count?: number;
  diversity_bonus?: number;
  zk_proof_hash?: string;
};

export type MarketplaceOrder = {
  order_id?: string;
  listing_id?: string;
  reputation_spent?: number;
  tokens_spent?: number;
  status?: string;
  created_at?: string;
};

export type WizardPreviewResult = {
  status?: string;
  metrics?: Record<string, string | number>;
  warnings?: string[];
  data_source?: string;
  warning?: string;
  equity_curve?: EquityPoint[];
};
