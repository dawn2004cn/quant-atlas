export type TimeseriesSyncRun = {
  recorded_at?: string;
  source?: string;
  ok?: boolean;
  mode?: string;
  questdb_rows_written?: number;
  failed_samples?: number;
};

export type TimeseriesHealth = {
  ok?: boolean;
  questdb?: {
    enabled?: boolean;
    connected?: boolean;
    endpoint?: string;
  };
  clickhouse?: {
    enabled?: boolean;
    connected?: boolean;
  };
  ohlcv_tables?: {
    questdb_rows?: number;
    clickhouse_rows?: number;
  };
  celery_beat?: {
    enabled?: boolean;
    schedule_label?: string;
    last_beat_run_at?: string;
    last_beat_run_ok?: boolean;
    sync_in_progress?: boolean;
    sync_progress?: { percent?: number };
    recent_beat_runs?: TimeseriesSyncRun[];
  };
  execution?: {
    qmt?: {
      execution_mode?: string;
      live_submit?: boolean;
    };
  };
  warnings?: string[];
};

export type TimeseriesSyncHistory = {
  runs: TimeseriesSyncRun[];
  count: number;
  limit?: number;
  source_filter?: string | null;
};
