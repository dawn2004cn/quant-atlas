export type SignalFlagItem = {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  amount: number;
  turnover: number;
  source: string;
  industry: string;
  signal_strategies?: Array<{ id: string; name: string }>;
  signal_strategies_sell?: Array<{ id: string; name: string }>;
  long_horizon?: { buy: string[]; sell: string[] };
  mid_horizon?: { buy: string[]; sell: string[] };
  short_horizon?: { buy: string[]; sell: string[] };
  safety_score: number;
  pe?: number;
  pb?: number;
};

export type SignalFlagPoolResponse = {
  items: SignalFlagItem[];
  total?: number;
};

export type SignalFlagScanResponse = {
  mode?: string;
  task_id?: string;
  message?: string;
  hits?: number;
  persisted?: number;
  scanned?: number;
};
