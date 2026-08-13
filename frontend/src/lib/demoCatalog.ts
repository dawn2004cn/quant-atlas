import type { AlphaFactorItem } from "../types/alpha";
import type { HotSector, HotSectorMember } from "../types/hotSector";
import type { PanoramaStockRow } from "../types/market";
import type { PortfolioPosition } from "../types/portfolio";
import type { SignalFlagItem } from "../types/signalflag";
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

export const DEMO_GLOBAL_RADAR = {
  total_assets: 4,
  gainers: 3,
  losers: 1,
  last_update: "演示",
  markets: [
    {
      name: "A股",
      code: "CN",
      indices: [
        { label: "上证指数", code: "000001", price: 3284.6, change_pct: 0.42 },
        { label: "深证成指", code: "399001", price: 10412.3, change_pct: 0.18 },
        { label: "创业板指", code: "399006", price: 2088.1, change_pct: -0.31 },
      ],
    },
    {
      name: "港股",
      code: "HK",
      indices: [
        { label: "恒生指数", code: "HSI", price: 17620.4, change_pct: 0.55 },
        { label: "恒生科技", code: "HSTECH", price: 3821.7, change_pct: 1.12 },
      ],
    },
    {
      name: "美股",
      code: "US",
      indices: [
        { label: "标普500", code: "SPX", price: 5482.1, change_pct: 0.28 },
        { label: "纳斯达克", code: "NDX", price: 19204.6, change_pct: 0.61 },
      ],
    },
    {
      name: "加密货币",
      code: "CRYPTO",
      indices: [
        { label: "比特币", code: "BTC", price: 67840, change_pct: 1.84 },
        { label: "以太坊", code: "ETH", price: 3482, change_pct: -0.44 },
      ],
    },
  ],
  linkages: [
    {
      us_sector: "半导体",
      cn_sector: "芯片",
      correlation: 0.72,
      signal: "positive" as const,
      summary: "美股芯片走强时，A 股半导体板块同向波动偏多。",
    },
    {
      us_sector: "利率",
      cn_sector: "银行",
      correlation: -0.38,
      signal: "negative" as const,
      summary: "美债利率上行阶段，国内银行相对收益常承压。",
    },
  ],
};

export const DEMO_LONGHU = [
  { code: "600519", name: "贵州茅台", reason: "日涨幅偏离值达7%", trade_date: "2026-08-12" },
  { code: "300750", name: "宁德时代", reason: "日换手率达20%", trade_date: "2026-08-12" },
  { code: "002594", name: "比亚迪", reason: "连续三个交易日内涨幅偏离值累计达20%", trade_date: "2026-08-11" },
  { code: "000858", name: "五粮液", reason: "日振幅达15%", trade_date: "2026-08-11" },
];

export const DEMO_TDX_BLOCKS = [
  { block_code: "880390", block_name: "白酒", change_pct: 1.82, rise_ratio: 0.72, leader_name: "贵州茅台", leader_change_pct: 1.24, stock_count: 18 },
  { block_code: "880491", block_name: "半导体", change_pct: 2.41, rise_ratio: 0.68, leader_name: "中芯国际", leader_change_pct: 3.1, stock_count: 42 },
  { block_code: "880752", block_name: "新能源车", change_pct: -0.55, rise_ratio: 0.41, leader_name: "比亚迪", leader_change_pct: -0.8, stock_count: 36 },
];

export const DEMO_TDX_MEMBERS = [
  { symbol: "600519", name: "贵州茅台", price: 1688, change_pct: 1.24 },
  { symbol: "000858", name: "五粮液", price: 128.6, change_pct: -0.62 },
  { symbol: "000568", name: "泸州老窖", price: 132.4, change_pct: 0.91 },
];

export const DEMO_FACTORS: AlphaFactorItem[] = [
  { factor_id: "mom_20", formula: "Rank(Close / Delay(Close, 20) - 1)", regime: "trending_up", sharpe_ratio: 1.42, max_drawdown: 0.12, metadata: { ic_mean: 0.046 } },
  { factor_id: "rev_5", formula: "-Rank(Close / Delay(Close, 5) - 1)", regime: "ranging", sharpe_ratio: 0.88, max_drawdown: 0.09, metadata: { ic_mean: 0.021 } },
  { factor_id: "vol_shrink", formula: "Rank(-Std(Returns, 20))", regime: "low_volatility", sharpe_ratio: 1.05, max_drawdown: 0.07, metadata: { ic_mean: 0.033 } },
  { factor_id: "turnover_drop", formula: "Rank(-Delta(Turnover, 10))", regime: "volatile", sharpe_ratio: 0.61, max_drawdown: 0.18, metadata: { ic_mean: 0.014 } },
];

export const DEMO_YANBAO = [
  {
    id: "demo-yb-1",
    title: "高端白酒景气延续，维持买入",
    stock_name: "贵州茅台",
    stock_code: "600519",
    rating: "买入",
    rating_change: "维持",
    agency: "演示券商",
    analyst: "张三",
    publish_date: "2026-08-10",
    summary: "渠道库存健康，批价稳中有升。",
    target_price: 1850,
    current_price: 1688,
  },
  {
    id: "demo-yb-2",
    title: "动力电池出货回暖",
    stock_name: "宁德时代",
    stock_code: "300750",
    rating: "增持",
    rating_change: "上调",
    agency: "演示研究所",
    analyst: "李四",
    publish_date: "2026-08-09",
    summary: "储能需求对冲车用淡季。",
    target_price: 230,
    current_price: 198.4,
  },
  {
    id: "demo-yb-3",
    title: "家电龙头份额稳固",
    stock_name: "美的集团",
    stock_code: "000333",
    rating: "买入",
    rating_change: "维持",
    agency: "演示证券",
    analyst: "王五",
    publish_date: "2026-08-08",
    summary: "外销与渠道改革支撑估值。",
    target_price: 82,
    current_price: 72.1,
  },
];

export const DEMO_SIGNAL_FLAGS: SignalFlagItem[] = [
  {
    code: "600519",
    name: "贵州茅台",
    price: 1688,
    change_pct: 1.24,
    amount: 8.2e9,
    turnover: 0.42,
    source: "demo",
    industry: "白酒",
    signal_strategies: [{ id: "ma_cross", name: "均线金叉" }],
    safety_score: 72,
    pe: 28.4,
    pb: 8.1,
  },
  {
    code: "601318",
    name: "中国平安",
    price: 48.2,
    change_pct: 0.85,
    amount: 4.1e9,
    turnover: 0.61,
    source: "demo",
    industry: "保险",
    signal_strategies: [{ id: "rsi_rebound", name: "RSI 回升" }],
    safety_score: 64,
    pe: 8.6,
    pb: 0.9,
  },
  {
    code: "000333",
    name: "美的集团",
    price: 72.1,
    change_pct: 0.31,
    amount: 2.8e9,
    turnover: 0.38,
    source: "demo",
    industry: "家电",
    signal_strategies: [{ id: "macd_hist", name: "MACD 翻红" }],
    safety_score: 58,
    pe: 14.2,
    pb: 2.4,
  },
];
