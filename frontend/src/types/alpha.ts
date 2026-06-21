export type AlphaFactoryStatus = {
  total_factors?: number;
  avg_sharpe?: number;
  recent_sharpe?: Array<{ formula: string; sharpe?: number }>;
  failed_count?: number;
  weekly_meeting_next?: string;
  is_weekly_enabled?: boolean;
  active_count?: number;
};

export type AlphaFactorItem = {
  factor_id?: string;
  formula?: string;
  regime?: string;
  sharpe_ratio?: number;
  max_drawdown?: number;
  created_at?: string;
  metadata?: Record<string, unknown>;
};

export type AlphaKnowledge = {
  alphas?: Array<{ name: string; formula: string; category: string; description: string }>;
  operators?: Record<string, { description: string }>;
  templates?: Array<Record<string, unknown>>;
};

export type ValidateResult = {
  valid?: boolean;
  complexity?: string;
  errors?: string[];
  warnings?: string[];
};

export type WeeklyStatus = {
  enabled?: boolean;
  is_weekly?: boolean;
  is_weekly_enabled?: boolean;
  weekly_meeting_next?: string;
  next_run?: string;
};

export type PaperTradingStatus = {
  status?: string;
  queue?: Array<{ model_id?: string; status?: string }>;
  items?: Array<{ model_id?: string; status?: string }>;
};
