import type { HotSector, HotSectorMember } from "../types/hotSector";
import type { PanoramaStockRow } from "../types/market";
import type { PortfolioPosition } from "../types/portfolio";
import type { WatchlistStock } from "../types/watchlist";

export const DEMO_STOCKS: WatchlistStock[] = [
  { symbol: "600519", name: "贵州茅台", price: 1688, change_pct: 1.24, health_score: 72, risk_level: "中" },
  { symbol: "000858", name: "五粮液", price: 128.6, change_pct: -0.62, health_score: 48, risk_level: "中" },
  { symbol: "601318", name: "中国平安", price: 48.2, change_pct: 0.85, health_score: 64, risk_level: "低" },
  { symbol: "000333", name: "美的集团", price: 72.1, change_pct: 0.31, health_score: 58, risk_level: "低" },
  { symbol: "600036", name: "招商银行", price: 36.8, change_pct: -0.22, health_score: 51, risk_level: "中" },
];

export const DEMO_SECTORS: HotSector[] = [
  { sector_code: "bk04741", name: "白酒", change_pct: 1.82, rise_ratio: 0.72, leader_name: "贵州茅台", leader_change_pct: 1.24, source: "demo", kind: "industry", provider: "demo" },
  { sector_code: "bk04765", name: "半导体", change_pct: 2.41, rise_ratio: 0.68, leader_name: "中芯国际", leader_change_pct: 3.1, source: "demo", kind: "industry", provider: "demo" },
  { sector_code: "bk04391", name: "新能源车", change_pct: -0.55, rise_ratio: 0.41, leader_name: "比亚迪", leader_change_pct: -0.8, source: "demo", kind: "concept", provider: "demo" },
  { sector_code: "bk04733", name: "银行", change_pct: 0.44, rise_ratio: 0.61, leader_name: "招商银行", leader_change_pct: -0.22, source: "demo", kind: "industry", provider: "demo" },
];

export const DEMO_MEMBERS: HotSectorMember[] = [
  { symbol: "600519", name: "贵州茅台", price: 1688, change_pct: 1.24, amount: 8.2e9, is_leader: true },
  { symbol: "000858", name: "五粮液", price: 128.6, change_pct: -0.62, amount: 3.1e9 },
  { symbol: "000568", name: "泸州老窖", price: 132.4, change_pct: 0.91, amount: 2.4e9 },
];

export const DEMO_SELECTOR = [
  { code: "600519", name: "贵州茅台", price: 1688, change_pct: 1.24, amount: 8.2e9, pe: 28.4, industry: "白酒", score: 88 },
  { code: "601318", name: "中国平安", price: 48.2, change_pct: 0.85, amount: 4.1e9, pe: 8.6, industry: "保险", score: 81 },
  { code: "000333", name: "美的集团", price: 72.1, change_pct: 0.31, amount: 2.8e9, pe: 14.2, industry: "家电", score: 79 },
  { code: "600036", name: "招商银行", price: 36.8, change_pct: -0.22, amount: 3.5e9, pe: 6.9, industry: "银行", score: 76 },
];

export const DEMO_PANORAMA_ROWS: PanoramaStockRow[] = [
  { code: "600519", name: "贵州茅台", price: 1688, change_pct: 1.24, amount: 8.2e9 },
  { code: "300750", name: "宁德时代", price: 198.4, change_pct: 2.15, amount: 1.1e10 },
  { code: "601318", name: "中国平安", price: 48.2, change_pct: 0.85, amount: 4.1e9 },
  { code: "000858", name: "五粮液", price: 128.6, change_pct: -0.62, amount: 3.1e9 },
  { code: "002594", name: "比亚迪", price: 268.0, change_pct: -1.12, amount: 6.4e9 },
];

export const DEMO_PORTFOLIO_POSITIONS: PortfolioPosition[] = [
  { symbol: "600519", name: "贵州茅台", shares: 20, price: 1688, market_value: 33760, weight: 0.28, return_pct: 4.2, pnl: 1360 },
  { symbol: "601318", name: "中国平安", shares: 400, price: 48.2, market_value: 19280, weight: 0.16, return_pct: 1.1, pnl: 210 },
  { symbol: "000333", name: "美的集团", shares: 200, price: 72.1, market_value: 14420, weight: 0.12, return_pct: 0.6, pnl: 86 },
  { symbol: "600036", name: "招商银行", shares: 300, price: 36.8, market_value: 11040, weight: 0.09, return_pct: -0.4, pnl: -44 },
];

export const DEMO_PORTFOLIO = {
  portfolio: {
    total_value: 120500,
    cash: 42000,
    positions: DEMO_PORTFOLIO_POSITIONS,
    returns: {
      total_return_pct: 2.4,
      total_pnl: 1612,
      benchmark_return_pct: 1.1,
      alpha_pct: 1.3,
    },
  },
  risk_budget: DEMO_PORTFOLIO_POSITIONS.map((p) => ({
    symbol: p.symbol,
    contribution_pct: p.weight,
    marginal_risk: 0.012,
    component_var: 0.008,
  })),
};
