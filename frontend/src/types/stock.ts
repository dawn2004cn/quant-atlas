export type StockRealtime = {
  code?: string;
  name?: string;
  price?: number;
  change_amount?: number;
  change_pct?: number;
  volume?: number;
  amount?: number;
  turnover?: number;
  pe?: number | null;
  pb?: number | null;
  industry?: string;
  open_price?: number;
  high_price?: number;
  low_price?: number;
  prev_close?: number;
};

export type StockDetailPayload = {
  code?: string;
  market?: string;
  profile?: {
    name?: string;
    industry?: string;
    realtime?: StockRealtime;
  };
  indicators?: Record<string, unknown>;
};

export type BarPoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export function extractRealtime(payload: StockDetailPayload): StockRealtime {
  const rt = payload.profile?.realtime ?? {};
  return {
    code: rt.code ?? payload.code,
    name: rt.name ?? payload.profile?.name,
    industry: rt.industry ?? payload.profile?.industry,
    price: rt.price,
    change_amount: rt.change_amount,
    change_pct: rt.change_pct,
    volume: rt.volume,
    amount: rt.amount,
    turnover: rt.turnover,
    pe: rt.pe,
    pb: rt.pb,
    open_price: rt.open_price,
    high_price: rt.high_price,
    low_price: rt.low_price,
    prev_close: rt.prev_close,
  };
}

export function normalizeBars(raw: unknown): BarPoint[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((row, index) => {
      if (!row || typeof row !== "object") return null;
      const bar = row as Record<string, unknown>;
      const close = Number(bar.close ?? bar.c);
      if (Number.isNaN(close)) return null;
      const open = Number(bar.open ?? bar.o ?? close);
      const high = Number(bar.high ?? bar.h ?? close);
      const low = Number(bar.low ?? bar.l ?? close);
      const volume = Number(bar.volume ?? bar.vol ?? bar.v ?? 0);
      const date = String(bar.date ?? bar.dt ?? bar.time ?? index);
      return { date, open, high, low, close, volume };
    })
    .filter((p): p is BarPoint => p !== null);
}

export type TradePlan = {
  generated_at?: string;
  symbol?: string;
  market?: string;
  name?: string;
  status?: string;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  recommended_shares?: number;
  plan?: {
    entry_price?: number;
    stop_loss?: number;
    take_profit_1?: number;
    target_price?: number;
    risk_reward_ratio?: number;
    recommended_shares?: number;
    position_weight_pct?: number;
    max_loss_amount?: number;
    max_loss_pct?: number;
    buy_reason?: string[];
    failure_conditions?: string[];
    execution_notes?: string[];
  };
  risk_cards?: Array<{
    title?: string;
    level?: string;
    content?: string;
  }>;
  scenario_analysis?: Array<{
    name?: string;
    price?: number;
    pnl?: number;
    account_impact_pct?: number;
    is_worst_case?: boolean;
  }>;
  soft_warnings?: Array<{
    code?: string;
    level?: string;
    message?: string;
    suggested_stop_loss?: number;
    nearest_support?: number;
  }>;
  risk_check?: {
    allowed?: boolean;
    reason?: string;
  };
  worst_case_30d?: {
    worst_drawdown_pct?: number;
    worst_price?: number;
    note?: string;
  };
};
