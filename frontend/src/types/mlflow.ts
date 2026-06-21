export type MlflowRun = {
  run_id: string;
  run_name?: string;
  status?: string;
  start_time?: number;
  end_time?: number;
  experiment_id?: string;
  ui_url?: string;
  metrics?: Record<string, number>;
  params?: Record<string, string>;
};

export type MlflowModelVersion = {
  name: string;
  version?: string;
  stage?: string;
  run_id?: string;
  status?: string;
  metrics?: Record<string, number>;
  params?: Record<string, string>;
  linked_proposals?: Array<{
    proposal_id: string;
    strategy_id: string;
    status: string;
  }>;
};

export type MlflowTrackingConfig = {
  available: boolean;
  tracking_uri?: string | null;
  experiment?: string;
  register_models?: boolean;
};

export type AnalysisChunk = {
  event?: string;
  phase?: string;
  status?: string;
  title?: string;
  message?: string;
  source?: string;
  ts?: string;
  data?: Record<string, unknown>;
};
