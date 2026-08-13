import type { AlphaFactorItem } from "../types/alpha";
import type { MarketplaceListing } from "../types/backtest";
import type { HotSector, HotSectorMember } from "../types/hotSector";
import type { PanoramaStockRow } from "../types/market";
import type { MlflowRun } from "../types/mlflow";
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

export const DEMO_WIZARD_TEMPLATES = [
  { id: "ma_cross", name: "均线金叉", description: "快慢均线交叉", is_recommended: true },
  { id: "rsi_reversion", name: "RSI 回归", description: "超买超卖回归", is_recommended: false },
  { id: "macd_trend", name: "MACD 趋势", description: "MACD 柱翻红跟趋势", is_recommended: true },
];

export const DEMO_STRATEGY_SNAPSHOTS = [
  {
    run_id: "demo-snap-1",
    strategy_name: "MA",
    symbol: "600519",
    created_at: "2026-08-12T10:00:00Z",
    metrics: { total_return_pct: 12.4, annual_return_pct: 18.2, sharpe: 1.42, max_drawdown_pct: -8.6 },
    status: "completed",
  },
  {
    run_id: "demo-snap-2",
    strategy_name: "RSI",
    symbol: "601318",
    created_at: "2026-08-11T09:30:00Z",
    metrics: { total_return_pct: 4.1, annual_return_pct: 6.8, sharpe: 0.88, max_drawdown_pct: -5.2 },
    status: "completed",
  },
  {
    run_id: "demo-snap-3",
    strategy_name: "MACD",
    symbol: "000333",
    created_at: "2026-08-10T14:20:00Z",
    metrics: { total_return_pct: -1.6, annual_return_pct: -2.1, sharpe: 0.21, max_drawdown_pct: -11.4 },
    status: "completed",
  },
];

export const DEMO_MLFLOW_RUNS: MlflowRun[] = [
  {
    run_id: "demo-run-1",
    run_name: "MA - 600519",
    start_time: Date.parse("2026-08-12T10:00:00Z"),
    metrics: { total_return: 0.124, sharpe: 1.42, max_drawdown: -0.086 },
    params: { strategy_name: "MA", symbol: "600519" },
  },
  {
    run_id: "demo-run-2",
    run_name: "RSI - 600519",
    start_time: Date.parse("2026-08-11T09:30:00Z"),
    metrics: { total_return: 0.041, sharpe: 0.88, max_drawdown: -0.052 },
    params: { strategy_name: "RSI", symbol: "600519" },
  },
  {
    run_id: "demo-run-3",
    run_name: "MACD - 000333",
    start_time: Date.parse("2026-08-10T14:20:00Z"),
    metrics: { total_return: -0.016, sharpe: 0.21, max_drawdown: -0.114 },
    params: { strategy_name: "MACD", symbol: "000333" },
  },
];

export const DEMO_OBSERVATIONS = [
  {
    id: "demo-obs-1",
    symbol: "600519",
    name: "贵州茅台",
    signal_type: "均线金叉",
    trigger_status: "triggered" as const,
    entry_price: 1620,
    current_price: 1688,
    target_price: 1850,
    stop_loss: 1550,
    pnl_pct: 4.2,
    created_at: "2026-08-10 10:22",
    updated_at: "2026-08-13 09:31",
  },
  {
    id: "demo-obs-2",
    symbol: "601318",
    name: "中国平安",
    signal_type: "RSI 回升",
    trigger_status: "pending" as const,
    entry_price: 47.8,
    current_price: 48.2,
    target_price: 52.0,
    stop_loss: 45.5,
    pnl_pct: 0.84,
    created_at: "2026-08-12 14:05",
    updated_at: "2026-08-13 09:31",
  },
  {
    id: "demo-obs-3",
    symbol: "000858",
    name: "五粮液",
    signal_type: "突破回踩",
    trigger_status: "expired" as const,
    entry_price: 130.0,
    current_price: 128.6,
    target_price: 142.0,
    stop_loss: 124.0,
    pnl_pct: -1.08,
    created_at: "2026-08-08 11:18",
    updated_at: "2026-08-12 15:00",
  },
];

export const DEMO_ALERTS = [
  {
    id: "demo-alert-1",
    title: "自选股异动",
    message: "贵州茅台涨幅超过 1%",
    severity: "warning" as const,
    source: "demo",
    category: "data",
    symbol: "600519",
    created_at: "2026-08-13T09:31:00Z",
    action_url: "/stock/600519",
  },
  {
    id: "demo-alert-2",
    title: "信号触发",
    message: "中国平安 RSI 回升待确认",
    severity: "info" as const,
    source: "demo",
    category: "factor",
    symbol: "601318",
    created_at: "2026-08-13T09:20:00Z",
    action_url: "/signal-observations",
  },
  {
    id: "demo-alert-3",
    title: "回测任务失败",
    message: "MACD / 000333 回测因数据缺口中止",
    severity: "critical" as const,
    source: "demo",
    category: "task",
    symbol: "000333",
    created_at: "2026-08-12T16:40:00Z",
    action_url: "/run-history",
  },
];

export const DEMO_ZEN = {
  pnl: { daily: 0.62, total: 4.18 },
  holdings: [
    { symbol: "600519", shares: 20, value: 33760, change_pct: 1.24 },
    { symbol: "601318", shares: 400, value: 19280, change_pct: 0.85 },
    { symbol: "000333", shares: 200, value: 14420, change_pct: 0.31 },
  ],
  recent_trades: [
    { symbol: "600519", side: "buy", quantity: 20, price: 1620, time: "2026-08-10 10:22" },
    { symbol: "000333", side: "buy", quantity: 200, price: 71.6, time: "2026-08-11 13:08" },
    { symbol: "000858", side: "sell", quantity: 100, price: 130.2, time: "2026-08-12 14:41" },
  ],
};

export const DEMO_SELECTION_RESULT = {
  task_id: "demo-select",
  status: "completed",
  created_at: "2026-08-12T09:00:00Z",
  completed_at: "2026-08-12T09:01:20Z",
  strategy_name: "演示多因子",
  total_candidates: 4,
  candidates: [
    { symbol: "600519", name: "贵州茅台", score: 88.2, rank: 1, reason: "景气与资金共振", expected_return_pct: 6.4, risk_level: "中", indicators: { pe: 28.4, mom: 1.24 } },
    { symbol: "300750", name: "宁德时代", score: 84.1, rank: 2, reason: "景气回暖", expected_return_pct: 8.1, risk_level: "中", indicators: { pe: 22.1, mom: 2.15 } },
    { symbol: "601318", name: "中国平安", score: 81.0, rank: 3, reason: "估值修复", expected_return_pct: 4.2, risk_level: "低", indicators: { pe: 8.6, mom: 0.85 } },
    { symbol: "000333", name: "美的集团", score: 79.4, rank: 4, reason: "份额稳固", expected_return_pct: 3.1, risk_level: "低", indicators: { pe: 14.2, mom: 0.31 } },
  ],
};

export const DEMO_PORTFOLIO_DETAIL = {
  id: "demo",
  name: "演示组合",
  description: "空行情时的样本持仓",
  created_at: "2026-08-01T00:00:00Z",
  total_value: 120500,
  cash: 42000,
  positions: DEMO_PORTFOLIO_POSITIONS,
  metrics: { sharpe: 1.21, volatility: 12.4, max_drawdown: -8.6, alpha: 1.3 },
};

export const DEMO_LISTINGS: MarketplaceListing[] = [
  { listing_id: "demo-l1", token_id: "mom_20", seller_id: 1, reputation_cost: 12, price_tokens: 12, signal_count: 48 },
  { listing_id: "demo-l2", token_id: "rev_5", seller_id: 2, reputation_cost: 8, price_tokens: 8, signal_count: 32 },
  { listing_id: "demo-l3", token_id: "vol_shrink", seller_id: 3, reputation_cost: 15, price_tokens: 15, signal_count: 21 },
];

export const DEMO_MANAGED_STOCKS = DEMO_STOCKS.map((s) => ({
  code: s.symbol,
  name: s.name,
  market: "CN",
  status: "active",
}));

export const DEMO_HEDGE_FUND = {
  nav: { current: 1.0418, daily_change_pct: 0.62, inception_return_pct: 4.18 },
  returns: { daily: 0.62, weekly: 1.14, monthly: 2.41, yearly: 8.6 },
  positions: [
    { symbol: "600519", market: "CN", weight_pct: 28, pnl_pct: 4.2, direction: "long" as const },
    { symbol: "601318", market: "CN", weight_pct: 16, pnl_pct: 1.1, direction: "long" as const },
    { symbol: "000333", market: "CN", weight_pct: 12, pnl_pct: 0.6, direction: "long" as const },
  ],
  metrics: { sharpe: 1.21, max_drawdown_pct: -8.6, win_rate: 0.58, total_trades: 24 },
  updated_at: "演示",
};

export const DEMO_COMMITTEE_SELECTION = {
  selected_stocks: [
    {
      symbol: "600519",
      market: "CN",
      confidence: 0.86,
      votes_for: 4,
      votes_against: 1,
      total_votes: 5,
      consensus: 0.8,
      summary: "基本面与动量共振，委员会多数赞成。",
      vote_breakdown: [
        { member: "基本面", approve: true, rationale: "估值仍可接受" },
        { member: "动量", approve: true, rationale: "趋势未破" },
        { member: "风控", approve: false, rationale: "持仓已偏白酒" },
      ],
    },
    {
      symbol: "300750",
      market: "CN",
      confidence: 0.78,
      votes_for: 3,
      votes_against: 1,
      total_votes: 4,
      consensus: 0.75,
      summary: "景气回暖，共识过线。",
      vote_breakdown: [
        { member: "行业", approve: true, rationale: "出货改善" },
        { member: "估值", approve: true, rationale: "分位不高" },
      ],
    },
  ],
  total_candidates: 12,
  threshold: 0.6,
  updated_at: "演示",
};

export const DEMO_INVESTMENT_MANAGERS = [
  {
    manager_id: "demo-mgr-1",
    name: "林衡",
    title: "权益策略",
    managed_assets: 3.2e8,
    total_return_pct: 18.4,
    annual_return_pct: 12.1,
    sharpe_ratio: 1.42,
    max_drawdown_pct: -8.6,
    strategy_count: 4,
    win_rate_pct: 58,
    description: "偏成长与景气轮动。",
    tags: ["成长", "消费"],
    strategies: [
      { strategy_id: "ma", name: "均线趋势", symbol: "600519", return_pct: 12.4, sharpe: 1.42, status: "active" },
      { strategy_id: "rsi", name: "RSI 回归", symbol: "000333", return_pct: 4.1, sharpe: 0.88, status: "active" },
    ],
    recent_performance: [
      { date: "2026-08-10", return_pct: 0.4 },
      { date: "2026-08-11", return_pct: -0.1 },
      { date: "2026-08-12", return_pct: 0.6 },
    ],
  },
  {
    manager_id: "demo-mgr-2",
    name: "周宁",
    title: "价值与红利",
    managed_assets: 2.1e8,
    total_return_pct: 9.6,
    annual_return_pct: 7.2,
    sharpe_ratio: 1.05,
    max_drawdown_pct: -5.2,
    strategy_count: 3,
    win_rate_pct: 61,
    description: "银行保险与高股息。",
    tags: ["价值", "红利"],
    strategies: [
      { strategy_id: "div", name: "高股息", symbol: "601318", return_pct: 6.8, sharpe: 1.05, status: "active" },
    ],
    recent_performance: [
      { date: "2026-08-10", return_pct: 0.2 },
      { date: "2026-08-11", return_pct: 0.1 },
      { date: "2026-08-12", return_pct: -0.05 },
    ],
  },
];

export const DEMO_EXPERT_TEAMS = [
  { team_id: "demo-team-1", name: "消费研究组", description: "白酒与家电景气跟踪", member_count: 5, specialty: ["白酒", "家电"], leader_name: "林衡", total_return_pct: 14.2, active_projects: 3, tags: ["基本面"] },
  { team_id: "demo-team-2", name: "制造研究组", description: "新能源与半导体", member_count: 6, specialty: ["新能源", "半导体"], leader_name: "周宁", total_return_pct: 11.8, active_projects: 4, tags: ["景气"] },
];

export const DEMO_MOMENTS = [
  { id: "demo-m1", type: "ai", content: "贵州茅台资金与景气共振，演示样本仅供界面预览。", created_at: "2026-08-13T09:31:00Z" },
  { id: "demo-m2", type: "system", content: "操盘台已切换演示数据模式。", created_at: "2026-08-13T09:00:00Z" },
  { id: "demo-m3", type: "post", content: "宁德时代出货回暖，关注储能对冲。", created_at: "2026-08-12T16:20:00Z" },
];

export const DEMO_MESSAGES = [
  {
    id: "demo-msg-1",
    sender_id: 0,
    sender_name: "系统",
    subject: "信号观测提醒",
    preview: "贵州茅台均线金叉已触发",
    content: "演示消息：600519 均线金叉已触发，可到信号观测页查看。",
    is_read: false,
    created_at: "2026-08-13 09:31",
    conversation_id: "demo-c1",
  },
  {
    id: "demo-msg-2",
    sender_id: 0,
    sender_name: "系统",
    subject: "回测完成",
    preview: "MA / 600519 演示回测已写入历史",
    content: "演示消息：可到回测历史页查看样本记录。",
    is_read: true,
    created_at: "2026-08-12 18:04",
    conversation_id: "demo-c2",
  },
];

export const DEMO_WAR_ROOM = {
  room_name: "演示作战室",
  last_updated: "演示",
  perspectives: [
    { label: "基本面", summary: "白酒与保险景气分化。", score: 0.72, color: "#34d399" },
    { label: "资金", summary: "主力净流入集中在龙头。", score: 0.64, color: "#60a5fa" },
    { label: "风险", summary: "波动可控，注意拥挤度。", score: 0.41, color: "#fbbf24" },
  ],
  data_grid: [
    { symbol: "600519", market: "CN", price: 1688, change_pct: 1.24, volume: 8.2e7, signal: "buy" as const, confidence: 0.78 },
    { symbol: "601318", market: "CN", price: 48.2, change_pct: 0.85, volume: 4.1e8, signal: "hold" as const, confidence: 0.61 },
    { symbol: "000858", market: "CN", price: 128.6, change_pct: -0.62, volume: 3.1e8, signal: "sell" as const, confidence: 0.54 },
  ],
};

export const DEMO_COMMITTEE_DASHBOARD = {
  consensus_meter: 0.72,
  total_members: 4,
  active_proposals: 2,
  updated_at: "演示",
  members: [
    { name: "基本面", role: "分析师", score: 86, accuracy: 0.71, total_votes: 42 },
    { name: "动量", role: "量化", score: 81, accuracy: 0.64, total_votes: 38 },
    { name: "风控", role: "风控", score: 79, accuracy: 0.82, total_votes: 40 },
    { name: "宏观", role: "宏观", score: 74, accuracy: 0.58, total_votes: 31 },
  ],
};

export const DEMO_TASKS = [
  {
    id: "demo-task-1",
    name: "MA / 600519 回测",
    description: "演示异步回测任务",
    status: "completed" as const,
    progress: 100,
    created_at: "2026-08-12 10:00",
    updated_at: "2026-08-12 10:08",
    type: "backtest",
  },
  {
    id: "demo-task-2",
    name: "选股扫描",
    description: "演示多因子选股",
    status: "running" as const,
    progress: 62,
    created_at: "2026-08-13 09:20",
    updated_at: "2026-08-13 09:31",
    type: "selection",
  },
  {
    id: "demo-task-3",
    name: "行情同步",
    description: "演示数据同步",
    status: "pending" as const,
    progress: 0,
    created_at: "2026-08-13 09:35",
    updated_at: "2026-08-13 09:35",
    type: "data",
  },
];

export const DEMO_SWARM_DASHBOARD = {
  overall_status: "healthy",
  active_agents: 3,
  total_agents: 4,
  tasks_processed: 128,
  uptime_hours: 42.5,
  agents: [
    { agent_name: "研究员", status: "running" as const, tasks_completed: 48, tasks_failed: 2, avg_response_time_ms: 1200, last_active: "2026-08-13 09:30", memory_usage_mb: 512, model: "gpt-demo" },
    { agent_name: "风控官", status: "idle" as const, tasks_completed: 36, tasks_failed: 1, avg_response_time_ms: 800, last_active: "2026-08-13 09:10", memory_usage_mb: 256, model: "gpt-demo" },
    { agent_name: "交易员", status: "running" as const, tasks_completed: 40, tasks_failed: 0, avg_response_time_ms: 950, last_active: "2026-08-13 09:31", memory_usage_mb: 384, model: "gpt-demo" },
    { agent_name: "书记员", status: "stopped" as const, tasks_completed: 4, tasks_failed: 0, avg_response_time_ms: 600, last_active: "2026-08-12 18:00", memory_usage_mb: 128, model: "gpt-demo" },
  ],
};

export const DEMO_SWARM_DESIGNER = {
  workspace: { id: "demo-ws", name: "演示工作区", description: "多智能体流程样例" },
  agents: [
    { id: "a1", name: "研究员", type: "research", model: "gpt-demo", role: "收集证据", status: "active" as const, connections: ["a2"], config: { tools: ["bars", "news"] } },
    { id: "a2", name: "风控官", type: "risk", model: "gpt-demo", role: "审查风险", status: "active" as const, connections: ["a3"], config: { max_dd: 0.1 } },
    { id: "a3", name: "交易员", type: "execution", model: "gpt-demo", role: "生成计划", status: "draft" as const, connections: [], config: {} },
  ],
};

export const DEMO_RESEARCH_PIPELINE = {
  pipeline_id: "demo-pipe",
  name: "演示研究管线",
  description: "从取数到报告的样例阶段",
  status: "running" as const,
  started_at: "2026-08-13 09:00",
  updated_at: "2026-08-13 09:31",
  stages: [
    { id: "s1", name: "取数", description: "拉取行情与基本面", status: "completed" as const, progress: 100, started_at: "09:00", completed_at: "09:05", output: "bars=240" },
    { id: "s2", name: "因子", description: "计算演示因子", status: "completed" as const, progress: 100, started_at: "09:05", completed_at: "09:12" },
    { id: "s3", name: "回测", description: "快速预览回测", status: "running" as const, progress: 55, started_at: "09:12" },
    { id: "s4", name: "报告", description: "生成研究摘要", status: "pending" as const, progress: 0 },
  ],
};

export const DEMO_RESEARCH_CANVAS = [
  { id: "c1", type: "note" as const, title: "白酒景气", content: "渠道库存健康，批价稳中有升。", tags: ["消费"], created_at: "2026-08-12", updated_at: "2026-08-13" },
  { id: "c2", type: "chart" as const, title: "600519 净值预览", content: "演示曲线占位", tags: ["回测"], created_at: "2026-08-12", updated_at: "2026-08-12", preview_url: "/app/backtest" },
  { id: "c3", type: "link" as const, title: "研报 Hub", content: "跳转演示研报列表", tags: ["研报"], created_at: "2026-08-11", updated_at: "2026-08-11", preview_url: "/app/yanbao-hub" },
];

export const DEMO_AGENTS = [
  { agent_id: "demo-agent-1", name: "诊股 Agent", description: "个股多维分析", status: "idle" as const, type: "analysis", last_run_at: "2026-08-12T18:00:00Z", last_run_summary: "完成 600519 演示诊股", run_count: 12, success_rate_pct: 92, tags: ["诊股"] },
  { agent_id: "demo-agent-2", name: "选股 Agent", description: "多因子扫描", status: "running" as const, type: "selection", last_run_at: "2026-08-13T09:20:00Z", last_run_summary: "扫描进行中", run_count: 8, success_rate_pct: 88, tags: ["选股"] },
  { agent_id: "demo-agent-3", name: "风控 Agent", description: "持仓与回撤检查", status: "completed" as const, type: "risk", last_run_at: "2026-08-13T08:50:00Z", last_run_summary: "无硬阻断", run_count: 20, success_rate_pct: 97, tags: ["风控"] },
];

export const DEMO_CAPABILITIES = {
  qlib: true,
  celery: true,
  rd_agent: false,
  websocket: true,
  capabilities: [
    { name: "市场行情", enabled: true, description: "K 线与报价", category: "data" },
    { name: "回测引擎", enabled: true, description: "策略历史回测", category: "strategy" },
    { name: "Agent Swarm", enabled: true, description: "多智能体编排", category: "ai" },
    { name: "RD-Agent", enabled: false, description: "可选研究代理", category: "ai" },
  ],
};

export const DEMO_VOICE_BRIEFING = {
  last_generated: "2026-08-13 08:30",
  schedule: "工作日 08:30",
  items: [
    { id: "vb1", title: "早盘要点", summary: "白酒走强，半导体分化；演示语音条目。", duration_seconds: 45, category: "早报", created_at: "2026-08-13 08:30", is_played: false },
    { id: "vb2", title: "持仓风险", summary: "组合回撤可控，注意拥挤度。", duration_seconds: 32, category: "风控", created_at: "2026-08-12 18:00", is_played: true },
  ],
};

export const DEMO_ALPHA_FACTORY = {
  status: {
    total_factors: 4,
    avg_sharpe: 0.99,
    active_count: 3,
    failed_count: 1,
    is_weekly_enabled: true,
  },
  knowledge: {
    alphas: [
      { name: "Alpha#001", formula: "rank(Ts_ArgMax(SUMS(returns_0_1, 20), 2))", description: "动量峰值演示因子" },
      { name: "Alpha#006", formula: "rank(correlation(close, volume, 15))", description: "价量相关演示因子" },
    ],
    operators: {
      rank: { description: "截面排序" },
      Ts_Mean: { description: "时序均值" },
      Std: { description: "标准差" },
    },
  },
  factors: DEMO_FACTORS,
};

export const DEMO_DECISION_REPLAYS = [
  {
    replay_id: "demo-replay-1",
    title: "茅台研报 → 调仓建议",
    description: "从研报证据到仓位建议的演示回放。",
    session_id: "sess-demo-600519",
    started_at: "2026-08-13T09:15:00+08:00",
    completed_at: "2026-08-13T09:18:22+08:00",
    total_steps: 3,
    summary: "维持超配，止损 -6%。",
    steps: [
      {
        step_id: "s1",
        sequence: 1,
        description: "拉取 600519 行情与研报证据",
        timestamp: "2026-08-13T09:15:05+08:00",
        duration_ms: 820,
        status: "success" as const,
        input_summary: "symbol=600519",
        output_summary: "3 条证据",
      },
      {
        step_id: "s2",
        sequence: 2,
        description: "多智能体辩论",
        timestamp: "2026-08-13T09:16:10+08:00",
        duration_ms: 4100,
        status: "success" as const,
        output_summary: "看多 2 / 中性 1",
      },
      {
        step_id: "s3",
        sequence: 3,
        description: "生成仓位建议",
        timestamp: "2026-08-13T09:18:00+08:00",
        duration_ms: 650,
        status: "success" as const,
        output_summary: "目标仓位 8%",
      },
    ],
  },
];

export const DEMO_COLLABORATION = {
  team_members: [
    { user_id: 1, username: "alice", role: "投研负责人", last_active: "2026-08-13 14:20" },
    { user_id: 2, username: "bob", role: "量化研究员", last_active: "2026-08-13 13:55" },
    { user_id: 3, username: "carol", role: "风控", last_active: "2026-08-12 18:40" },
  ],
  shared_notes: [
    {
      id: "note-1",
      title: "白酒拥挤度观察",
      content: "演示笔记：关注渠道库存与批价背离。",
      author: "alice",
      updated_at: "2026-08-13 10:00",
    },
    {
      id: "note-2",
      title: "半导体事件驱动清单",
      content: "演示笔记：财报窗口与出口管制跟踪。",
      author: "bob",
      updated_at: "2026-08-12 16:30",
    },
  ],
  activity_feed: [
    {
      id: "act-1",
      type: "note",
      description: "更新了共享笔记「白酒拥挤度观察」",
      actor: "alice",
      timestamp: "2026-08-13 10:00",
    },
    {
      id: "act-2",
      type: "decision",
      description: "提交决策回放「茅台研报 → 调仓建议」",
      actor: "bob",
      timestamp: "2026-08-13 09:18",
    },
  ],
};

export const DEMO_OBSERVABILITY = {
  overall_status: "healthy",
  health_banner: { message: "演示观测快照 · 服务可用", level: "info" },
  sla: { uptime_target_pct: 99.5, api_p95_ms: 180, decision_review_sla_hours: 24 },
  critical_services: { ok: true, critical_missing: [], required_missing: [] },
  task_messages: [
    { ts: "2026-08-13 14:00", label: "quotes_dump", detail: "演示全量 dump 完成", event: "ok", task_name: "quotes_full_dump" },
    { ts: "2026-08-13 13:55", label: "alert_dispatch", detail: "演示预警分发", event: "ok", task_name: "alert_dispatch" },
  ],
  timeseries_beat_runs: [{ recorded_at: "2026-08-13 14:00", ok: true, mode: "demo", questdb_rows_written: 1280 }],
  quotes_api: {
    full_dump_count: 2,
    symbol_batch_count: 12,
    last_full_dump_at: "2026-08-13T14:00:00+08:00",
    last_full_dump_rows: 4200,
    backend: "demo",
    recent_dumps: [{ at: "2026-08-13 14:00", market: "CN", rows: 4200 }],
    trend_rows: [3800, 4000, 4100, 4200],
  },
  alert_ops: {
    alert_dispatch_beat: true,
    alert_dispatch_beat_minutes: 5,
    quotes_dump_monitor_beat: true,
    quotes_dump_monitor_beat_minutes: 15,
    quotes_dump_auto_dispatch: true,
    quotes_full_dump_warn: false,
    quotes_full_dump_count: 2,
    quotes_full_dump_threshold: 10,
    preferred_endpoint: "/api/v1/system/observability/snapshot",
  },
};

export const DEMO_INVESTMENT_COMMITTEE = {
  active_members: 4,
  updated_at: "2026-08-13T10:30:00+08:00",
  debates: [
    {
      topic: "是否加仓 600519",
      moderator: "主席 Agent",
      started_at: "2026-08-13T10:00:00+08:00",
      turns: [
        { speaker: "多头研究员", role: "bull", argument: "批价稳、渠道健康，演示看多论点。", sentiment: "bullish" as const },
        { speaker: "空头研究员", role: "bear", argument: "估值偏贵，演示谨慎论点。", sentiment: "bearish" as const },
        { speaker: "风控官", role: "risk", argument: "单票仓位上限 8%。", sentiment: "neutral" as const },
      ],
    },
  ],
  proposals: [
    {
      id: "prop-demo-1",
      title: "白酒板块超配提案",
      description: "演示提案：目标行业权重 +3%。",
      proposed_by: "策略 Agent",
      status: "open" as const,
      votes_for: 2,
      votes_against: 1,
      total_votes: 3,
      deadline: "2026-08-14T18:00:00+08:00",
    },
  ],
};

export const DEMO_ARCHITECTURE_ROADMAP = {
  phases: [
    {
      phase: "阶段 E · 体验与数据",
      items: [
        { name: "SPA 局部刷新", status: "completed", description: "KeepAliveOutlet + SWR keepPreviousData" },
        { name: "演示数据兜底", status: "in_progress", description: "空列表页 DemoBanner + catalog" },
        { name: "DIF 门禁闭环", status: "planned", description: "Bias / Risk Guard 验收" },
      ],
    },
    {
      phase: "阶段 F · 观测与协作",
      items: [
        { name: "观测台快照", status: "in_progress", description: "SLA / Beat / 适配器探针" },
        { name: "协作工作区", status: "planned", description: "笔记与活动流" },
      ],
    },
  ],
};

export const DEMO_RETAIL_ASSISTANT = {
  health_score: 78,
  tips: [
    { title: "先定仓位再选股", description: "演示技巧：单票风险预算不超过总资金 2%。" },
    { title: "避免追涨杀跌", description: "演示技巧：用计划价位分批，而不是盘中冲动。" },
  ],
  resources: [
    { title: "平台手册（演示）", url: "/docs/public/" },
    { title: "风险须知（演示）", url: "/docs/public/" },
  ],
  portfolio_health: {
    diversification: 0.62,
    risk_level: "中等",
    recommendation: "演示建议：适度分散至非相关板块。",
  },
};

export const DEMO_PORTFOLIO_RESONANCE = {
  resonance_score: 72,
  alignment: 68,
  sectors: [
    { name: "白酒", weight: 0.35 },
    { name: "半导体", weight: 0.25 },
    { name: "银行", weight: 0.2 },
    { name: "现金", weight: 0.2 },
  ],
  correlations: [
    [1, 0.42, 0.18, 0.05],
    [0.42, 1, 0.11, 0.02],
    [0.18, 0.11, 1, 0.08],
    [0.05, 0.02, 0.08, 1],
  ],
};

export const DEMO_ATTRIBUTION = {
  total_return: 8.42,
  allocation_effect: 2.15,
  selection_effect: 5.61,
  interaction_effect: 0.66,
  sectors: [
    { name: "白酒", weight: 0.28, return: 12.4 },
    { name: "半导体", weight: 0.22, return: 6.1 },
    { name: "银行", weight: 0.18, return: 3.2 },
    { name: "新能源", weight: 0.15, return: -2.8 },
  ],
};

export const DEMO_EXPERIMENTS = [
  { id: "exp-demo-1", name: "动量 20D 演示实验", status: "completed", created_at: "2026-08-10T12:00:00+08:00", metrics: { total_return: 14.2, sharpe: 1.35 } },
  { id: "exp-demo-2", name: "均值回归演示实验", status: "completed", created_at: "2026-08-08T09:30:00+08:00", metrics: { total_return: 6.8, sharpe: 0.92 } },
];

export const DEMO_EXPERIMENT_DETAIL = {
  id: "exp-demo-1",
  name: "动量 20D 演示实验",
  description: "演示报告：截面动量因子在白酒与半导体上的样本回测。",
  status: "completed",
  created_at: "2026-08-10T12:00:00+08:00",
  preset_name: "momentum_20d",
  metrics: { total_return: 14.2, sharpe_ratio: 1.35, ic_mean: 0.046, max_drawdown: -9.8 },
  equity_curve: [
    { date: "2025-01", value: 1.0 },
    { date: "2025-03", value: 1.04 },
    { date: "2025-06", value: 1.09 },
    { date: "2025-09", value: 1.07 },
    { date: "2025-12", value: 1.142 },
  ],
  findings: ["IC 在趋势市更稳", "拥挤度升高时需降权", "与 DEMO_FACTORS.mom_20 同源"],
};

export const DEMO_FACTOR_DETAIL = {
  factor_id: "mom_20",
  formula: "Rank(Close / Delay(Close, 20) - 1)",
  sharpe_ratio: 1.42,
  max_drawdown: 0.12,
  ic_mean: 0.046,
  regime: "trending_up",
  source: "demo",
  data_range: "2024-01 ~ 2025-12",
  created_at: "2026-08-01",
  backtest_result: {
    annual_return: 0.168,
    sharpe_ratio: 1.42,
    win_rate: 0.56,
    profit_loss_ratio: 1.8,
    max_drawdown: 0.12,
    trade_count: 128,
  },
  ic_series: [
    { date: "2025-01", ic: 0.03 },
    { date: "2025-02", ic: 0.05 },
    { date: "2025-03", ic: 0.04 },
    { date: "2025-04", ic: 0.06 },
    { date: "2025-05", ic: 0.02 },
    { date: "2025-06", ic: 0.05 },
  ],
  correlations: [
    { factor_id: "rev_5", name: "短反转", value: -0.32 },
    { factor_id: "vol_shrink", name: "波动收缩", value: 0.18 },
  ],
};

export const DEMO_FACTOR_EVOLUTION = {
  nodes: [
    { id: "n1", factor_id: "mom_20", name: "动量20", type: "primitive", ic: 0.046, status: "active" },
    { id: "n2", factor_id: "mom_20_v2", name: "动量20·衰减", type: "derived", ic: 0.051, status: "active" },
    { id: "n3", factor_id: "mom_vol", name: "动量×波动", type: "composite", ic: 0.038, status: "candidate" },
  ],
  links: [
    { source: "n1", target: "n2" },
    { source: "n1", target: "n3" },
    { source: "n2", target: "n3" },
  ],
};

export const DEMO_INTEGRATION_HUB = {
  stack: {
    layers: {
      mysql_enabled: { ok: true, enabled: true },
      timeseries_ohlcv: { ok: true, enabled: true, detail: { data_freshness: 92, async_throughput: 88 } },
      quantml_factors: { ok: true, enabled: true },
      openbb_global: { ok: false, enabled: false, reason: "demo offline" },
      celery_tasks: { ok: true, enabled: true },
      execution_gateway: { ok: false, enabled: false },
      realtime_ws: { ok: true, enabled: true },
      kronos: { ok: true, enabled: true },
      fingpt: { ok: false, enabled: false },
      quantml_agent: { ok: true, enabled: true },
    },
    mysql_integration_row_counts: { quotes: 4200, factors: 128, experiments: 12 },
  },
  realtime: {
    socketio_enabled: true,
    quote_broadcast: true,
    tick_stream: false,
    rooms: { market: 3, alerts: 1 },
  },
  tasks: [
    { ts: "2026-08-13T14:00:00+08:00", label: "ohlcv_sync", detail: "演示同步完成" },
    { ts: "2026-08-13T13:50:00+08:00", label: "factor_ic", detail: "演示 IC 计算" },
  ],
  jobs: [
    { task_name: "demo.quotes_dump", status: "SUCCESS" },
    { task_name: "demo.alert_dispatch", status: "STARTED" },
  ],
};

export const DEMO_DECISION_SNAPSHOT = {
  snapshot_id: "snap-demo-600519",
  created_at: "2026-08-13T10:15:00+08:00",
  symbol: "600519",
  market: "CN",
  decision_type: "加仓建议",
  score: 78,
  stance: "偏多",
  evidence: [
    { source: "研报", content: "渠道库存健康，批价稳中有升（演示）。", confidence: 0.82 },
    { source: "技术面", content: "20 日均线上方运行（演示）。", confidence: 0.71 },
  ],
  alternative_views: [
    { title: "估值谨慎", content: "相对历史分位偏高，演示反向观点。" },
  ],
  signals: [
    { name: "动量", value: 0.64, impact: "positive" },
    { name: "波动", value: 0.22, impact: "neutral" },
    { name: "拥挤度", value: 0.71, impact: "negative" },
  ],
};

export const DEMO_DATA_LAKE = {
  lake: {
    engine: "sqlite",
    status: "healthy",
    migration: { status: "idle" },
    metrics: { p95_latency_ms: 42 },
    store: { type: "sqlite", status: "healthy" },
  },
  timeseries: {
    questdb: { enabled: true, connected: true },
    ohlcv_tables: { questdb_rows: 128000 },
    last_sync: {
      recorded_at: "2026-08-13T14:00:00+08:00",
      ok: true,
      source: "demo",
      mode: "incremental",
      questdb_rows_written: 1280,
    },
    sync_progress: { status: "idle", percent: 100, symbols_done: 50, symbols_total: 50 },
    celery_beat: {
      enabled: true,
      schedule_label: "*/15 * * * *",
      sync_in_progress: false,
      last_beat_run_at: "2026-08-13T14:00:00+08:00",
      last_beat_run_ok: true,
      recent_beat_runs: [{ source: "demo", ok: true, recorded_at: "2026-08-13T14:00:00+08:00" }],
    },
    execution: { qmt: { execution_mode: "paper" } },
    warnings: [],
    backfill: { target_rows: 200000, coverage_pct: 64, meets_target: false, questdb_rows: 128000 },
  },
  realtime: {
    socketio_enabled: true,
    origins_configured: true,
    quote_broadcast: true,
    tick_stream: false,
    rooms: { market: 2, alerts: 1 },
    tick: { status: "idle" },
  },
};

export const DEMO_PROFESSIONAL_WORKBENCH = {
  portfolio_optimization: {
    status: "就绪",
    allocations: [
      { symbol: "600519", target: 0.08, current: 0.05 },
      { symbol: "000858", target: 0.06, current: 0.07 },
      { symbol: "300750", target: 0.05, current: 0.04 },
    ],
  },
  brinson_attribution: {
    total_effect: 1.85,
    allocation_effect: 0.62,
    selection_effect: 1.12,
    sectors: [
      { name: "白酒", allocation: 0.4, selection: 0.8, total: 1.2 },
      { name: "半导体", allocation: 0.15, selection: 0.25, total: 0.4 },
      { name: "银行", allocation: 0.07, selection: 0.07, total: 0.25 },
    ],
  },
  compliance_check: {
    passed: true,
    violations: [{ rule: "单票上限 10%", severity: "low", detail: "演示提示：600519 目标仓位 8%，合规。" }],
  },
  execution_algorithms: {
    algorithms: [
      { name: "TWAP", status: "running", pnl: 0.12 },
      { name: "VWAP", status: "idle", pnl: -0.03 },
    ],
  },
};

export const DEMO_USER_MANAGEMENT = {
  users: [
    { username: "demo_admin", role: "admin", role_name: "管理员", protected: true },
    { username: "demo_analyst", role: "analyst", role_name: "分析师", protected: false },
    { username: "demo_viewer", role: "viewer", role_name: "只读", protected: false },
  ],
  roles: [
    { code: "admin", label: "管理员" },
    { code: "analyst", label: "分析师" },
    { code: "viewer", label: "只读" },
  ],
};

export const DEMO_USER_SPECTRUM = {
  stats: { total_users: 128, active_traders: 46, researchers: 22 },
  tiers: [
    { name: "Boutique", count: 48 },
    { name: "Investment", count: 36 },
    { name: "Fund", count: 28 },
    { name: "Institution", count: 16 },
  ],
  recent: [
    { username: "alice", action: "research: 提交实验", time: "10 分钟前" },
    { username: "bob", action: "trade: 调整仓位", time: "25 分钟前" },
    { username: "carol", action: "social: 发布动态", time: "1 小时前" },
  ],
};

export const DEMO_TIER_BOUTIQUE = {
  tier: "Boutique",
  is_active: true,
  benefits: ["演示：精选策略模板", "演示：早盘语音简报", "演示：自选股预警"],
};

export const DEMO_TIER_FUND = {
  tier: "Fund",
  is_active: true,
  benefits: ["演示：组合归因", "演示：多账户影子盘", "演示：专属研究员额度"],
};

export const DEMO_TIER_INVESTMENT = {
  tier: "Investment",
  is_active: true,
  benefits: ["演示：回测加速", "演示：因子库高级筛选", "演示：委员会投票"],
};

export const DEMO_TIER_INSTITUTION = {
  tier: "institution",
  name: "Institution",
  active: true,
  benefits: [
    "演示：更高 API 限额",
    "演示：专属支持通道",
    "演示：自定义工作流",
  ],
  api_access: true,
  dedicated_support: true,
  custom_workflows: true,
  upgrade_path: "演示：联系客户成功经理开通私有化",
  monthly_fee: 19999,
  api_limits: { daily: 100000, concurrent: 50 },
};

export const DEMO_SHADOW_ACCOUNT = {
  total_trades: 86,
  win_rate: 0.58,
  total_return: 0.124,
  summary: "演示分析：样本成交记录偏动量风格，回撤可控。",
};

export const DEMO_PROFILE = {
  prefs: { font_size: "md" },
  policy: {
    tier_label: "Investment",
    features: [
      { name: "回测", enabled: true },
      { name: "Alpha Marketplace", enabled: true },
      { name: "机构 API", enabled: false },
    ],
  },
  audit: [
    { action: "login", target_id: "session", created_at: "2026-08-13 09:00" },
    { action: "update_prefs", target_id: "font_size", created_at: "2026-08-12 18:20" },
  ],
  notifs: {
    site_message: true,
    price_alerts: true,
    risk_alerts: true,
    psychology_alerts: false,
    weekly_review: true,
    wechat: false,
    sms: false,
  },
  invest: { risk_level: "balanced", horizon: "中期" },
};

export const DEMO_TASK_DETAIL = {
  id: "task-demo-1",
  name: "演示任务 · OHLCV 同步",
  description: "接口空时展示的演示任务详情。",
  status: "completed" as const,
  progress: 100,
  created_at: "2026-08-13 13:50",
  updated_at: "2026-08-13 14:00",
  type: "timeseries",
  result: { rows_written: 1280, mode: "demo" },
  logs: ["开始同步", "写入 QuestDB", "完成"],
  source: "registry" as const,
};

export const DEMO_QUANT_LAB = {
  symbol: "600519",
  series: [
    { date: "2025-01", value: 1.0 },
    { date: "2025-03", value: 1.02 },
    { date: "2025-06", value: 0.98 },
    { date: "2025-09", value: 1.05 },
    { date: "2025-12", value: 1.08 },
  ],
  stats: { mean: 0.012, std: 0.04 },
  meta: { demo: true, disclaimer: "演示曲线，非实盘模拟" },
};

export const DEMO_AI_ANALYSIS = {
  symbol: "600519",
  market: "CN",
  summary: "演示诊股：茅台短期偏强，估值处历史中枢偏上，注意拥挤度。",
  technical: "价格位于 20 日均线上方，MACD 金叉维持（演示）。",
  fundamental: "ROE 与毛利率仍处行业前列（演示）。",
  sentiment: "研报与资金面偏多，散户情绪偏热（演示）。",
  risk: "估值回撤与政策预期差是主要风险（演示）。",
  recommendation: "谨慎超配",
  generated_at: "2026-08-13T10:00:00+08:00",
};

export const DEMO_AI_CHAT = [
  { role: "user" as const, content: "请分析当前 A 股市场整体走势" },
  { role: "assistant" as const, content: "演示回复：白酒与银行相对稳健，成长板块分化；建议关注拥挤度与风险预算。" },
];

export const DEMO_AI_RESEARCH_REPORT = {
  symbol: "600519",
  market: "CN",
  depth: "standard",
  title: "贵州茅台 · 演示研究报告",
  sections: [
    { heading: "投资要点", content: "渠道库存健康，批价稳中有升（演示）。" },
    { heading: "估值与建议", content: "目标价区间演示数据，维持超配但控制仓位。" },
  ],
  disclaimer: "演示报告，不构成投资建议。",
  generated_at: "2026-08-13T10:00:00+08:00",
};

export const DEMO_BACKTEST = {
  total_return: 0.142,
  sharpe: 1.35,
  max_drawdown: 0.098,
  win_rate: 0.56,
  equity_curve: [
    { date: "2025-01-01", value: 100000 },
    { date: "2025-04-01", value: 104500 },
    { date: "2025-07-01", value: 109200 },
    { date: "2025-10-01", value: 107800 },
    { date: "2025-12-31", value: 114200 },
  ],
  trades: [
    { date: "2025-02-10", side: "buy", price: 1650, quantity: 100 },
    { date: "2025-06-20", side: "sell", price: 1720, quantity: 100 },
  ],
  mlflow_run_id: "demo-run-ma",
};

export const DEMO_LONG_TERM_SELECT = {
  strategy: "classic",
  market: "CN",
  candidates: [
    { code: "600519", name: "贵州茅台", score: 92.4, reason: "质量+动量共振（演示）", industry: "白酒", price: 1688, change_pct: 1.2 },
    { code: "000858", name: "五粮液", score: 88.1, reason: "估值修复（演示）", industry: "白酒", price: 128.6, change_pct: -0.4 },
    { code: "300750", name: "宁德时代", score: 84.6, reason: "成长景气（演示）", industry: "电池", price: 186.2, change_pct: 0.8 },
  ],
};

export const DEMO_NL_STRATEGY = {
  status: "completed",
  symbol: "600519",
  strategy_name: "双均线演示策略",
  strategy_description: "当 5 日均线上穿 20 日均线买入，跌破卖出（演示）。",
  params: { fast: 5, slow: 20, size: 1000 },
  backtest_metrics: {
    total_return_pct: 12.4,
    annual_return_pct: 11.2,
    sharpe: 1.18,
    max_drawdown_pct: -8.6,
  },
};

export const DEMO_OPTIMIZE = {
  status: "ok",
  expected_return: 0.15,
  expected_risk: 0.12,
  sharpe_ratio: 1.05,
  weights: { "600519": 0.28, "000858": 0.22, "300750": 0.2, CASH: 0.3 },
};

export const DEMO_STOCK_DETAIL = {
  quote: {
    code: "600519",
    name: "贵州茅台",
    price: 1688,
    change_amount: 20.5,
    change_pct: 1.23,
    volume: 1280000,
    amount: 2.1e9,
    open_price: 1670,
    high_price: 1695,
    low_price: 1662,
    prev_close: 1667.5,
    industry: "白酒",
  },
  bars: [
    { date: "2025-12-01", open: 1650, high: 1668, low: 1645, close: 1660, volume: 1.1e6 },
    { date: "2025-12-08", open: 1660, high: 1675, low: 1655, close: 1672, volume: 1.2e6 },
    { date: "2025-12-15", open: 1672, high: 1688, low: 1668, close: 1680, volume: 1.3e6 },
    { date: "2025-12-22", open: 1680, high: 1695, low: 1675, close: 1688, volume: 1.28e6 },
  ],
};

export const DEMO_STRATEGY_COMPARE = {
  comparisons: [
    { strategy_name: "双均线策略", status: "ok" as const, total_return: 0.142, annual_return: 0.12, sharpe: 1.35, max_drawdown: 0.09, win_rate: 0.55, trade_count: 24 },
    { strategy_name: "MACD金叉", status: "ok" as const, total_return: 0.118, annual_return: 0.1, sharpe: 1.12, max_drawdown: 0.11, win_rate: 0.52, trade_count: 18 },
    { strategy_name: "RSI超卖反转", status: "ok" as const, total_return: 0.086, annual_return: 0.07, sharpe: 0.88, max_drawdown: 0.08, win_rate: 0.58, trade_count: 32 },
  ],
  winner: "双均线策略",
};

export const DEMO_ZEN_TERMINAL = {
  results: [
    { symbol: "600519", name: "贵州茅台", price: 1688 },
    { symbol: "000858", name: "五粮液", price: 128.6 },
    { symbol: "300750", name: "宁德时代", price: 186.2 },
  ],
  log: ["[演示] 终端就绪，可搜索标的并模拟下单"],
};
