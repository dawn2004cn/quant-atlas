import type { WorkbenchSnapshot } from "../types/workbench";

/** Last-resort SPA snapshot when the workbench API itself errors. */
export const DEMO_WORKBENCH: WorkbenchSnapshot = {
  generated_at: "",
  market: "CN",
  data_mode: "demo",
  demo_parts: ["client"],
  health_banner: {
    level: "warning",
    headline: "演示数据",
    summary: "接口暂不可用，以下为展示样本",
    message: "接口暂不可用，以下为展示样本",
  },
  decision: {
    score: 56,
    stance: "中性偏多",
    action: "控制仓位，等待确认",
    reasons: ["行情源未就绪，使用演示盘面"],
    confidence: 0.4,
  },
  market_sentiment: {
    score: 56,
    level: "中性偏多",
    description: "演示市场宽度",
    emoji: "📊",
    stats: { gainers: 1842, losers: 1260, neutral: 418, total: 3520 },
  },
  market_panorama: { up: 1842, down: 1260, flat: 418, total: 3520 },
  macro_indices: [
    { label: "上证指数", code: "SH000001", price: 3278.4, change_pct: 0.46 },
    { label: "深证成指", code: "SZ399001", price: 10412.0, change_pct: 0.31 },
    { label: "沪深300", code: "SH000300", price: 3890.2, change_pct: 0.52 },
  ],
  watchlist_health: {
    items: [
      { code: "600519", name: "贵州茅台", price: 1688, change_pct: 1.24, health_score: 72 },
      { code: "000858", name: "五粮液", price: 128.6, change_pct: -0.62, health_score: 48 },
      { code: "601318", name: "中国平安", price: 48.2, change_pct: 0.85, health_score: 64 },
    ],
    summary: "演示自选",
  },
  recommendations_preview: {
    items: [{ code: "600519", name: "贵州茅台", reason: "演示推荐", score: 82 }],
    note: "演示",
  },
  headlines: [{ title: "演示资讯：权重股修复", source: "演示" }],
};
