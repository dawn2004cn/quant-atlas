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
