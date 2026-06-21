Quant Atlas UI 全方位审计与优化改进报告

审计范围: 前端 React SPA（frontend/src/）+ Flask 模板层（app/presentation/web/templates/）
审计日期: 2026-06-20
审计角色: 交易员 · 前端工程师 · 产品经理 · 安全审计师

---
一、UI 现状全真相 (Raw Truth)

1. 页面结构与路由

┌────────────────┬──────────────────┬────────────────────┬──────────────────────┐
│      路由      │       页面       │      加载策略      │         文件         │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /login         │ 登录             │ 立即加载           │ Login.tsx            │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /              │ 操盘台 Dashboard │ 立即加载           │ Dashboard.tsx        │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /backtest      │ 策略回测         │ Lazy               │ Backtest.tsx         │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /runs          │ 历史运行         │ Lazy               │ RunHistory.tsx       │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /experiments   │ 实验报告         │ Lazy               │ ExperimentReport.tsx │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /marketplace   │ 因子市场         │ Lazy + FeatureGate │ Marketplace.tsx      │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /stock/:symbol │ 个股详情         │ 立即加载           │ StockDetail.tsx      │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /alpha-factory │ 因子工厂         │ Lazy               │ AlphaFactory.tsx     │
├────────────────┼──────────────────┼────────────────────┼──────────────────────┤
│ /signal-flag   │ 信号旗           │ Lazy               │ SignalFlag.tsx       │
└────────────────┴──────────────────┴────────────────────┴──────────────────────┘

正面的: 6/9 的页面做了懒加载（React.lazy），代码分割正确。

致命的缺陷:

① 无 Error Boundary (App.tsx 第 18-20 行只包了 Suspense，没有 ErrorBoundary)
function Lazy({ children }) {
  return <Suspense fallback={<div>加载中…</div>}>{children}</Suspense>;
}
如果任何一个懒加载页面抛出异常（如 API 返回非法 JSON 导致渲染崩溃），整个 SPA 白屏。用户必须手动刷新，且刷新后大概率再次崩溃。

② StockDetail 未做懒加载 (App.tsx 第 41 行)
StockDetailPage 是直接 import 的，而 Backtest 等低频页面却是懒加载的。个股详情页是用户高频访问的页面，但它的 PriceHistoryChart 依赖的 LightweightCharts (~120 KB) 在首屏就加载了，没有按需加载。

③ 导航使用 <a> 跳转到经典版 (Layout.tsx 第 41 行)
<a href="/daily-workbench">经典版</a>
此链接会触发完整页面重载，退出 React SPA 上下文。用户在 SPA 和 Flask 模板之间切换时，所有 React 状态丢失。

---
2. K 线图：有骨架无实质

PriceHistoryChart.tsx 使用的是 TradingView LightweightCharts（第 63 行从 window.LightweightCharts 加载，通过 CDN script 注入），而非 Recharts。

存在但不足的是:

// PriceHistoryChart.tsx 第 32-42 行
const series = chart.addLineSeries({
  color: "#7c3aed",
  lineWidth: 2,
});
series.setData(
  data.map((p) => ({
    time: p.date.slice(0, 10) as any,
    value: p.close,  // 只有收盘价，没有 OHLC
  }))
);

这是折线图（LineSeries），不是蜡烛图（CandlestickSeries）！TradingView LightweightCharts 原生支持 addCandlestickSeries()，但当前实现只画了一条紫色收盘价折线。

成交量柱缺失 — LightweightCharts 支持 addHistogramSeries() 做成交量叠加，当前完全没有。

数量级的潜在问题: 当前加载 120 根数据点没有问题，但 LightweightCharts 通过 CDN 注入的方式（第 63 行 (window as any).LightweightCharts）不是工程化引入，如果 CDN 挂了整个图表不显示；此外第 65-66 行在 CDN 加载失败时用了一个 {remove() {}, addLineSeries() ...} 的空对象静默降级——用户将看到空白容器，没有任何错误提示页面的视觉反馈。

组件无 memo 化 (PriceHistoryChart.tsx 第 8 行)
export function PriceHistoryChart({ data }: Props) {    // 无 React.memo
没有 React.memo 包裹意味着但父组件 StockDetail 因任何原因重渲染（SWR 轮询返回、useState 变更），整个图表 DOM 会被 React reconciliation 扫描。

---
3. 组件级渲染性能问题

SignalFlag 大列表无虚拟化 (SignalFlag.tsx 第 46-48 行)
const items = data?.items ?? [];               // 最多 800 条
const pageItems = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);  // 伪分页
看起来有分页按钮，但 react-window 在 package.json 里躺着没用。800 行 <table> DOM + 复杂的 JSX（条件类名、截断格式化、条件 badge）——在低端设备上滚动和点击会有明显卡顿。

逐行点击使用 window.location.href (SignalFlag.tsx 第 124 行)
onClick={() => { window.location.href = `/stock/${encodeURIComponent(it.code)}`; }}
致命问题：完整浏览器导航。跳转后用户无法用浏览器"返回"回到原来翻到的页面页码。每次导航都重新加载所有页面资源。

Backtest 页面每次渲染重新计算数据 (Backtest.tsx 第 105-107 行)
const equityCurve = result ? extractEquityCurve(result) : [];  // 每次渲染执行
const trades = result ? extractTrades(result) : [];
const metricCards = result ? extractMetricCards(result) : [];
这三个函数每次组件更新都执行（包括 hover、输入框输入等），没有 useMemo 包装。对 result 这个引用不变的对象来说完全浪费。

数组索引作 key 多处:
- Backtest.tsx 第 380 行: key={\${t.date}-${t.side}-${i}`}` — 包含索引
- AlphaFactory.tsx 第 196, 231 行: <tr key={i}> — 裸索引
- Marketplace.tsx 第 981 行: key={\${id}-${idx}`}` — 含索引

---
4. API 响应格式不一致导致前端兼容层臃肿

api.ts 第 24-29 行定义的 ApiEnvelope 需要同时兼容两套格式：
export type ApiEnvelope<T> = {
  ok?: boolean;     // v2 格式
  success?: boolean; // 旧的 success/error 格式
  data?: T;
  meta?: Record<string, unknown>;
  error?: { message?: string; code?: string };
};
unwrap() 函数（第 46 行）需要判断 "data" in json 来区分 v1 和 v2 响应。这意味着前端必须维护这套兼容逻辑，而每一端新加的路由如果不符合任何一种格式，前端将静默返回 undefined。

---
5. 布局与导航

Layout 整体质量尚可 (Layout.tsx):
- 响应式 flex-wrap 导航 — ✅
- 暗色/亮色切换 — ✅
- i18n 多语言 — ✅
- Feature Flag 条件渲染 — ✅

问题:

max-w-6xl（第 25, 74 行）宽度约 1152px。对于一个量化交易看盘页面来说太窄。交易员习惯在宽屏（1440px+ 甚至 1920px）上工作，1152px 的内容区会导致行情表格的列被截断、K 线图横向空间不足。

Header 固定/浮动缺失 — 布局是普通流式（第 23 行 min-h-screen），没有 sticky header。在 SignalFlag 这类长列表页面，用户需要回到顶部才能操作导航。

---
6. 个股详情页 UI 问题

StockDetail (StockDetail.tsx):

- 技术指标以 <pre> JSON 形式展示（第 103-105 行）：
<pre className="max-h-48 overflow-auto text-xs">
  {JSON.stringify(data.indicators, null, 2)}
</pre>
这对 Quant 可用，但对普通用户和技术交易员都不可用。没有任何可视化（表格、指标值卡片、叠加到 K 线）。

- AI 分析流使用 unbounded array — useAnalysisStream 中的 steps 数组在分析过程中无限累积（useAnalysisStream.ts 第 29 行 setSteps((prev) => [...prev, chunk])），没有 500 行的上限截断。
- "打开经典版详情"使用 <a> 导航（第 109 行）— 又是一个完整页面跳转。

---
7. 登录页面 UX

Login (Login.tsx):

- Session/JWT 模式切换对普通用户过于复杂。"Session（推荐）"和"API JWT"两个选项对非技术用户没有意义。产品经理应当默认使用 Session，把 JWT 选项放在高级设置或 API 文档中。
- 登录成功后直接 navigate(redirectTo)（第 28 行），没有过渡动画或确认反馈。
- 第 58-60 行的 JWT 说明文字提到了 API_JWT_SECRET 配置项——这是后端运维细节，不应暴露给终端用户。

---
8. 经典版 (Flask 模板) vs SPA 的割裂

代码库中存在 ~100 个 Flask Jinja2 模板（app/presentation/web/templates/）和 18 个 React TSX 组件。两者通过 <a href> 相互链接，形成两个平行 UI 世界：

┌──────────┬───────────────────────────────┬────────────────────────┐
│   维度   │          Flask 模板           │       React SPA        │
├──────────┼───────────────────────────────┼────────────────────────┤
│ 渲染     │ 服务端 Jinja2                 │ 客户端 React 19        │
├──────────┼───────────────────────────────┼────────────────────────┤
│ 状态     │ 每次请求全量                  │ SPA 内存状态           │
├──────────┼───────────────────────────────┼────────────────────────┤
│ 前端库   │ Bootstrap 4 + jQuery (vendor) │ Tailwind + DaisyUI     │
├──────────┼───────────────────────────────┼────────────────────────┤
│ K 线     │ 可能没有或不同实现            │ LightweightCharts 折线 │
├──────────┼───────────────────────────────┼────────────────────────┤
│ CSS 体积 │ ~300 KB Bootstrap             │ 98 KB Tailwind         │
├──────────┼───────────────────────────────┼────────────────────────┤
│ 路由     │ 服务端 URL                    │ React Router /app/     │
└──────────┴───────────────────────────────┴────────────────────────┘

用户在两个世界之间切换时：
1. 所有状态丢失（筛选条件、翻页位置、数据缓存）
2. 每次切换全量加载（~400 KB JS + ~300 KB CSS + 全部后端数据）
3. 视觉风格不一致（Bootstrap 的蓝色主题 vs DaisyUI 的紫色 brand）

---
9. 前端安全风险

- JWT 存在 localStorage (api.ts 第 32-44 行) — XSS 攻击点。虽然 api.ts 第 59-66 行的 request() 函数同时支持 Authorization: Bearer 头和 Cookie，但 JWT 存 localStorage 意味着任何 XSS 注入可窃取全局令牌。
- TradePlanPanel esc() 未覆盖全部字段 — TradePlanPanel.tsx 第 15-22 行有自定义 esc() 函数对 buy_reason 等字段手动转义，但第 233 行的 scenario_analysis[i].name 和第 207 行的 card.title 没有调用 esc()。
- LightweightCharts 从 CDN 加载 — PriceHistoryChart.tsx 第 63 行 (window as any).LightweightCharts 依赖外部 CDN。CDN 被篡改或不可用时，图表功能静默降级（第 65-67 行返回空对象，用户无感知）。

---
二、UI 痛点矩阵

┌───────┬─────────────┬───────────────────────────────────────────┬──────────────────────────────────────────────────────────┬─────────────────────────────────────┬────────┐
│   #   │    角色     │                   现象                    │                           根源                           │              商业风险               │ 优先级 │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-01 │ 交易员      │ 走势图是紫色折线，没有 K 线蜡烛图         │ PriceHistoryChart.tsx:32 用了 addLineSeries() 而非       │ 核心功能缺失，用户无法做技术分析    │ P0     │
│       │             │                                           │ addCandlestickSeries()                                   │                                     │        │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-02 │ 前端/PM     │ 无 Error Boundary，任一页面崩溃导致 SPA   │ App.tsx 只有 Suspense，无 ErrorBoundary                  │ 用户流失、品牌信任破产              │ P0     │
│       │             │ 白屏                                      │                                                          │                                     │        │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-03 │ 前端/交易员 │ 信号旗 800 行 DOM 裸渲染，翻页卡顿        │ SignalFlag.tsx:46-48 未用 react-window                   │ 低端设备不可用                      │ P1     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-04 │ 前端/PM     │ SignalFlag 行点击触发全页面导航           │ SignalFlag.tsx:124 用 window.location.href               │ 糟糕的用户旅程，翻页状态丢失        │ P1     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-05 │ 前端        │ K 线图依赖 CDN 加载，CDN 不可用时静默降级 │ PriceHistoryChart.tsx:63                                 │ 图表功能不可预测                    │ P1     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-06 │ 前端        │ 成交量柱缺失，技术指标仅 JSON 文本展示    │ PriceHistoryChart.tsx:32-42 只画了收盘价线               │ 信息密度不足，量化分析受限          │ P1     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-07 │ 前端        │ 所有图表组件无 React.memo                 │ PriceHistoryChart.tsx:8, EquityCurveChart.tsx:9          │ 父组件重渲染触发图表重建            │ P1     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-08 │ 交易员/PM   │ 1140px 内容区太窄，宽屏浪费               │ Layout.tsx:25 使用 max-w-6xl（72rem）                    │ 宽屏显示器信息密度不足              │ P1     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-09 │ 前端        │ Backtest 频繁无意义重计算                 │ Backtest.tsx:105-107 无 useMemo                          │ 回测页面交互响应延迟                │ P2     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-10 │ 产品        │ 登录页给普通用户展示 Session/JWT 技术选择 │ Login.tsx:42-56                                          │ 用户困惑，增加流失                  │ P2     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-11 │ 前端        │ K 线图未懒加载，高频访问页面反而加载全部  │ App.tsx:41 StockDetail 直接 import                       │ 首屏加载体积增加 120 KB             │ P2     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-12 │ 前端        │ API 两层响应格式在前端兼容                │ api.ts:24-29 的 ApiEnvelope                              │ 新 API 不匹配格式时前端静默         │ P2     │
│       │             │                                           │                                                          │ undefined                           │        │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-13 │ 前端        │ 爬虫很多处用数组索引做 React key          │ Backtest.tsx:380, AlphaFactory.tsx:196                   │ 列表重新排序时 DOM 错误复用         │ P2     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-14 │ 安全        │ JWT 存 localStorage                       │ api.ts:32                                                │ XSS 可窃取令牌                      │ P2     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-15 │ 前端/PM     │ 个股技术指标以 JSON 展示                  │ StockDetail.tsx:101-107 JSON.stringify                   │ 用户无法理解，功能形同虚设          │ P2     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-16 │ 前端        │ Header 不固定，长页面要滚回顶部           │ Layout.tsx:23 无 sticky                                  │ 操作效率降低                        │ P3     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-17 │ 前端/PM     │ AI 分析 steps 数组无限增长                │ useAnalysisStream.ts:29 无截断                           │ 长分析会话内存泄露                  │ P3     │
├───────┼─────────────┼───────────────────────────────────────────┼──────────────────────────────────────────────────────────┼─────────────────────────────────────┼────────┤
│ UI-18 │ 前端        │ 两个 UI 世界（Flask+SPA）风格与状态割裂   │ Layout.tsx:41 + StockDetail.tsx:109 的 <a> 跳            │ 体验断裂、开发维护成本双倍          │ P0*    │
└───────┴─────────────┴───────────────────────────────────────────┴──────────────────────────────────────────────────────────┴─────────────────────────────────────┴────────┘

▎ * P0*（UI-18）: 这是战略级问题，不是在 Sprint 内能用前端重构解决的，需要产品决策——但用户体验影响是 P0 级别。

---
三、UI 重构路线图

短期（Sprint 1-2 · 安全+修复）

┌──────────────────────────────────────────────────────────┬──────────┬───────────────────────────┐
│                           任务                           │ 预期工时 │         影响页面          │
├──────────────────────────────────────────────────────────┼──────────┼───────────────────────────┤
│ ✅ 添加 <ErrorBoundary> 到 App 根路由                    │ 0.5 天   │ 全局                      │
├──────────────────────────────────────────────────────────┼──────────┼───────────────────────────┤
│ ✅ SignalFlag window.location.href → useNavigate()       │ 0.5 天   │ SignalFlag                │
├──────────────────────────────────────────────────────────┼──────────┼───────────────────────────┤
│ ✅ K 线图将 LineSeries 改为 CandlestickSeries + 成交量图 │ 1 天     │ StockDetail               │
├──────────────────────────────────────────────────────────┼──────────┼───────────────────────────┤
│ ✅ 两个图表组件添加 React.memo                           │ 0.5 天   │ PriceHistory, EquityCurve │
├──────────────────────────────────────────────────────────┼──────────┼───────────────────────────┤
│ ✅ Backtest 添加 useMemo                                 │ 0.5 天   │ Backtest                  │
├──────────────────────────────────────────────────────────┼──────────┼───────────────────────────┤
│ ✅ 数组索引 key 替换为唯一标识                           │ 0.5 天   │ 全局                      │
└──────────────────────────────────────────────────────────┴──────────┴───────────────────────────┘

中期（Sprint 3-4 · 性能+体验）

┌────────────────────────────────────────────┬──────────┬─────────────┐
│                    任务                    │ 预期工时 │  影响页面   │
├────────────────────────────────────────────┼──────────┼─────────────┤
│ ⬜ SignalFlag 接入 react-window            │ 1 天     │ SignalFlag  │
├────────────────────────────────────────────┼──────────┼─────────────┤
│ ⬜ LightweightCharts 从 CDN 迁移到 npm 包  │ 0.5 天   │ StockDetail │
├────────────────────────────────────────────┼──────────┼─────────────┤
│ ⬜ StockDetail 添加懒加载                  │ 0.5 天   │ 路由/App    │
├────────────────────────────────────────────┼──────────┼─────────────┤
│ ⬜ AI 分析 steps 添加 500 行上限截断       │ 0.5 天   │ StockDetail │
├────────────────────────────────────────────┼──────────┼─────────────┤
│ ⬜ max-w-6xl → max-w-7xl（1280px）         │ 0.5 天   │ Layout      │
├────────────────────────────────────────────┼──────────┼─────────────┤
│ ⬜ 技术指标从 JSON 文本改为可视化表格/卡片 │ 1 天     │ StockDetail │
├────────────────────────────────────────────┼──────────┼─────────────┤
│ ⬜ Login 页简化，JWT 选项移至高级设置      │ 0.5 天   │ Login       │
└────────────────────────────────────────────┴──────────┴─────────────┘

长期（Sprint 5-6 · 架构收敛）

┌───────────────────────────────────────────────┬──────────┬──────────┐
│                     任务                      │ 预期工时 │ 影响页面 │
├───────────────────────────────────────────────┼──────────┼──────────┤
│ 🔲 API 统一响应格式，前端删除兼容层           │ 2 天     │ 全栈     │
├───────────────────────────────────────────────┼──────────┼──────────┤
│ 🔲 JWT 从 localStorage 迁移到 httpOnly cookie │ 1 天     │ 全栈     │
├───────────────────────────────────────────────┼──────────┼──────────┤
│ 🔲 Header 添加 sticky 定位                    │ 0.5 天   │ Layout   │
├───────────────────────────────────────────────┼──────────┼──────────┤
│ 🔲 评估 Flask 模板 → SPA 迁移策略             │ PM 决策  │ 整体     │
├───────────────────────────────────────────────┼──────────┼──────────┤
│ 🔲 添加端到端性能测试（Lighthouse CI）        │ 1 天     │ CI       │
└───────────────────────────────────────────────┴──────────┴──────────┘

---
四、各痛点详细技术方案

UI-01: K 线重构

现状: PriceHistoryChart.tsx 第 32 行 addLineSeries() — 纯折线
目标: TradingView LightweightCharts 原生蜡烛图

// 改后代码: PriceHistoryChart.tsx 核心更改
import { createChart, IChartApi, CandlestickData, HistogramData } from 'lightweight-charts';
// （从 npm 导入，非 CDN）

useEffect(() => {
  if (!containerRef.current || !data.length) return;

  const chart = createChart(containerRef.current, { /* options 保持不变 */ });
  chartRef.current = chart;

  // 蜡烛图系列
  const candleSeries = chart.addCandlestickSeries({
    upColor: '#22c55e', downColor: '#ef4444',
    borderUpColor: '#22c55e', borderDownColor: '#ef4444',
    wickUpColor: '#22c55e', wickDownColor: '#ef4444',
  });
  candleSeries.setData(
    data.map((p) => ({
      time: p.date.slice(0, 10),
      open: p.open, high: p.high, low: p.low, close: p.close,
    }))
  );

  // 成交量柱 (叠加在最下面)
  const volSeries = chart.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
  });
  chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
  volSeries.setData(
    data.map((p) => ({
      time: p.date.slice(0, 10),
      value: p.volume,
      color: p.close >= p.open ? '#22c55e44' : '#ef444444',
    }))
  );

  chart.timeScale().fitContent();
}, [data]);

效果: 红绿色蜡烛图 + 底部半透明成交量柱，天勤标准的看盘界面。

UI-02: Error Boundary

现状: App.tsx 只有 Suspense，崩溃 = 白屏

方案: 新建 ErrorBoundary.tsx

// frontend/src/components/ErrorBoundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props { children: ReactNode; }
interface State { error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error) { return { error }; }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI 崩溃:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-[50vh] items-center justify-center">
          <div className="glass-card p-8 text-center space-y-4">
            <h2 className="text-xl font-bold text-rose-600">页面遇到了问题</h2>
            <p className="text-sm text-slate-500">{this.state.error.message}</p>
            <button className="btn btn-primary" onClick={() => {
              this.setState({ error: null });
              window.location.href = '/app';
            }}>
              返回首页
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

接入: App.tsx 包裹所有路由:
<ErrorBoundary>
  <Routes>...</Routes>
</ErrorBoundary>

UI-03: SignalFlag 虚拟化

现状: 800 行 DOM + 伪分页
方案: 接入 react-window

import { FixedSizeList } from 'react-window';

// 替换:
// <tbody>{pageItems.map(...)}</tbody>
// 为:
<tbody>
  <FixedSizeList
    height={Math.min(items.length * 40, 600)}
    itemCount={items.length}
    itemSize={40}
    width="100%"
  >
    {({ index, style }) => {
      const it = items[index];
      return (
        <tr style={style} className="..." onClick={() => navigate(`/stock/${it.code}`)}>
          ...
        </tr>
      );
    }}
  </FixedSizeList>
</tbody>

翻页控件改为分页状态由 FixedSizeList 自身滚动管理。

UI-05: LightweightCharts 从 CDN 迁移到 npm

npm install lightweight-charts

删除 PriceHistoryChart.tsx 第 62-68 行的 createChart() 包装函数和所有 (window as any).LightweightCharts 引用。直接从 npm 导入:

import { createChart, ColorType } from 'lightweight-charts';

效果: 去掉 CDN 依赖，TypeScript 类型支持，Tree-shaking 减小体积（约 120 KB → 按需 50 KB）。

UI-07: 图表组件添加 React.memo

export const PriceHistoryChart = React.memo(function PriceHistoryChart({ data }: Props) {
  // ... 现有代码不变
});
export const EquityCurveChart = React.memo(function EquityCurveChart({ data, trades }: Props) {
  // ... 现有代码不变
});

UI-09: Backtest 添加 useMemo

const equityCurve = useMemo(() => result ? extractEquityCurve(result) : [], [result]);
const trades = useMemo(() => result ? extractTrades(result) : [], [result]);
const metricCards = useMemo(() => result ? extractMetricCards(result) : [], [result]);

UI-12: 统一 API 响应

短期：在 unwrap() 中增加更严格的格式校验和 fallback:
function unwrap<T>(json: ApiEnvelope<T> | T): T {
  if (json && typeof json === 'object' && 'data' in json) {
    return (json as any).data ?? (json as any).ok;
  }
  return json as T;
}

长期: app/core/api_envelope.py 统一后端格式为 {ok: bool, data: T, meta: {}}，所有 v1 路由通过 v1_deprecation.py 中间件做格式转换。前端删除 success/error 兼容。

---
五、总结

UI 层整体评价: 代码组织结构是合理的（React 19 + TypeScript strict + Vite + Tailwind），懒加载策略基本正确，hooks 清理逻辑大多数正确。

但交易类 App 特有的体验差距明显:

1. 最高优先: K 线图只有收盘价折线（PriceHistoryChart.tsx:32）、无 Error Boundary（全 SPA 白屏风险）
2. 中优先: SignalFlag 虚拟化缺失、技术指标 JSON 文本、API 响应格式未统一、LightweightCharts CDN 引用
3. 低优先: useMemo 缺失、数组 key、Layout 宽度、登录页 UX

建议立刻执行 Sprint 1（3 天）:

Day 1: ErrorBoundary + K 线蜡烛图（只需要改 2 个文件的 30 行代码）
Day 2: React.memo + useMemo + navigate 替换 + SignalFlag 虚拟化
Day 3: LightweightCharts npm 迁移 + 登录页简化 + Layout 宽度