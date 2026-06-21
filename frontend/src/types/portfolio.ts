/* Portfolio management types */

export type PortfolioSnapshot = {
  portfolio: {
    total_value: number;
    cash: number;
    positions: PortfolioPosition[];
    returns: {
      total_return_pct: number;
      total_pnl: number;
      benchmark_return_pct?: number;
      alpha_pct?: number;
    };
  };
};

export type PortfolioPosition = {
  symbol: string;
  name?: string;
  shares: number;
  price: number;
  market_value: number;
  weight: number;
  return_pct?: number;
  pnl?: number;
};

export type OptimizationRequest = {
  symbols: string[];
  method: "markowitz" | "black_litterman";
  target_return?: number;
  risk_aversion?: number;
  analyst_views?: Record<string, unknown>;
};

export type OptimizationResult = {
  method: string;
  optimal_weights: Record<string, number>;
  expected_return: number;
  expected_volatility: number;
  sharpe_ratio: number;
  efficient_frontier?: Array<{ volatility: number; return_val: number }>;
};

export type RebalanceAlert = {
  symbol: string;
  current_weight: number;
  target_weight: number;
  deviation: number;
  action: "buy" | "sell" | "hold";
  amount: number;
};

export type RebalanceResult = {
  snapshot: PortfolioSnapshot["portfolio"];
  actions: RebalanceAlert[];
  holdings: PortfolioPosition[];
};

export type PortfolioAttribution = {
  portfolio_return: number;
  benchmark_return: number;
  alpha: number;
  factor_attribution?: Record<string, number>;
  style_allocation?: Record<string, number>;
};

export type RiskBudgetItem = {
  symbol: string;
  contribution_pct: number;
  marginal_risk: number;
  component_var: number;
};

export type RiskBudgetResult = {
  risk_budget: RiskBudgetItem[];
};

export type PortfolioDetail = {
  id: string;
  name: string;
  created_at: string;
  total_value: number;
  cash: number;
  positions: PortfolioPosition[];
  metrics?: {
    sharpe?: number;
    volatility?: number;
    max_drawdown?: number;
    win_rate?: number;
  };
};