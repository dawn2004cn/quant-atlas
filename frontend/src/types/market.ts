export type PanoramaStockRow = {
  code?: string;
  name?: string;
  price?: number;
  change_pct?: number;
  volume?: number;
  amount?: number;
};

export type PanoramaRankings = {
  gainers: PanoramaStockRow[];
  losers: PanoramaStockRow[];
  amounts: PanoramaStockRow[];
  turnovers: PanoramaStockRow[];
};

export type PanoramaSector = {
  name?: string;
  change_pct?: number;
  up_count?: number;
  down_count?: number;
};

export type MarketQuotesPage = {
  items: PanoramaStockRow[];
  total: number;
  page: number;
  page_size: number;
  scope?: string;
  stats?: {
    total?: number;
    up?: number;
    down?: number;
    flat?: number;
    limit_up?: number;
    limit_down?: number;
  };
};

export type MarketPanorama = {
  rankings: PanoramaRankings;
  summary?: {
    gainers?: number;
    losers?: number;
    flat?: number;
    total?: number;
    [key: string]: unknown;
  };
  sectors?: PanoramaSector[];
  updated_at?: string;
};