export type WorkbenchSnapshot = {
  generated_at?: string;
  market?: string;
  data_mode?: "live" | "demo" | "mixed";
  demo_parts?: string[];
  health_banner?: {
    level?: string;
    headline?: string;
    summary?: string;
    message?: string;
    quotes_full_dump_warn?: boolean;
    quotes_full_dump_count?: number;
    quotes_full_dump_threshold?: number;
    items?: Array<{ label?: string; status?: string }>;
  };
  morning_call?: {
    headline?: string;
    bullets?: string[];
    has_stop_confirm?: boolean;
  };
  decision?: {
    score?: number;
    stance?: string;
    action?: string;
    reasons?: string[];
    confidence?: number;
  };
  market_sentiment?: {
    score?: number;
    level?: string;
    description?: string;
    emoji?: string;
    stats?: { gainers?: number; losers?: number; neutral?: number; total?: number };
  };
  market_panorama?: { up?: number; down?: number; flat?: number; total?: number };
  macro_indices?: Array<{
    label?: string;
    code?: string;
    price?: number;
    change_pct?: number;
  }>;
  watchlist_health?: {
    items?: WatchlistItem[];
    summary?: string;
  };
  observation_cards?: ObservationCard[];
  limit_up_stocks?: Array<{ code?: string; name?: string; change_pct?: number }>;
  recommendations_preview?: {
    items?: Array<{ code?: string; name?: string; reason?: string; score?: number }>;
    note?: string;
  };
  review_strip?: {
    pending?: number;
    overdue?: number;
    items?: Array<{
      decision_id?: string;
      subject?: string;
      reason?: string;
      confidence?: number;
      priority?: string;
      review_by?: string;
    }>;
    cta?: string;
  };
  headlines?: Array<{ title?: string; url?: string; source?: string }>;
};

export type WatchlistItem = {
  code?: string;
  name?: string;
  price?: number;
  change_pct?: number;
  health_score?: number;
};

export type ObservationCard = {
  code?: string;
  name?: string;
  trigger_status?: string;
  source?: string;
  current_price?: number;
  entry_price?: number;
};
