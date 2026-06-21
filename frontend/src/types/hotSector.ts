/* Hot sectors types */

export type HotSector = {
  sector_code: string;
  name: string;
  change_pct: number;
  rise_ratio: number;
  leader_name?: string;
  leader_change_pct?: number;
  source?: string;
  provider?: string;
  kind?: string;
};

export type HotSectorMember = {
  symbol: string;
  name?: string;
  price?: number;
  change_pct?: number;
  amount?: number;
  is_leader?: boolean;
};

export type HotSectorSnapshot = {
  snapshot_at: string;
  sector_count: number;
};

export type HotSectorQuery = {
  kind?: string;
  source?: string;
  limit?: number;
  snapshot_at?: string;
};

export type HotSectorResponse = {
  sectors: HotSector[];
  snapshot_at?: string;
  source_mode?: string;
  warnings?: string[];
  data_timestamp?: string;
  is_realtime?: boolean;
  freshness?: unknown;
  updated_at?: string;
};