export type ExperimentSummary = {
  id: string;
  name: string;
  status: string;
  created_at?: string | null;
  metrics?: Record<string, number>;
};

export type ExperimentDetail = {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at?: string | null;
  metrics?: Record<string, number>;
  artifacts?: Record<string, unknown>;
  equity_curve?: Array<{ date?: string; value?: number; equity?: number }>;
  strategy_code?: string;
  findings?: string[];
  swarm_run_id?: string;
  preset_name?: string;
};
