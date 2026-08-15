import { Link } from "react-router-dom";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";

const SECTIONS = [
  {
    title: "行情与延迟",
    body: "A 股主路径依赖 TDX / 本地缓存；港美与加密可能走 yfinance 等外源。免费或公共源常有延迟，盘中数字不等于交易所实盘。",
  },
  {
    title: "演示数据 (data_mode)",
    body: "当行情源为空或接口失败时，SPA 会展示带「演示」标注的样本行，便于浏览流程。演示不是 SLA，也不是实盘报价。",
  },
  {
    title: "图表与个股页",
    body: "SPA 个股页使用平台自有 K 线组件。外部嵌入图表（如部分全球源）可能对部分交易所有免费档限制，不作为 A 股主图方案。",
  },
  {
    title: "预警与晨报",
    body: "自选晨报 / 语音简报依赖后台任务与模型可用性。服务降级时会回退到演示摘要，请以页面标注为准。",
  },
  {
    title: "非投资建议",
    body: "Quant Atlas 是研究与监控工具，不提供证券经纪服务，也不构成投资建议。交易决策请自行负责。",
  },
];

export function MarketCoveragePage() {
  return (
    <div className="mx-auto max-w-[800px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.dashboard} />
      <div>
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Market Coverage</div>
        <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">数据与市场说明</h1>
        <p className="mt-1 text-sm text-zinc-500">说清能力边界，避免把延迟或演示当成实盘故障。</p>
      </div>

      <div className="space-y-3">
        {SECTIONS.map((s) => (
          <section key={s.title} className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
            <h2 className="text-sm font-semibold text-zinc-100">{s.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-zinc-400">{s.body}</p>
          </section>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        <Link className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-emerald-400 ring-1 ring-emerald-500/30" to="/watchlist-briefing">
          自选晨报
        </Link>
        <Link className="rounded-lg px-3 py-1.5 text-zinc-300 ring-1 ring-zinc-700/60" to="/self-stocks">
          自选股
        </Link>
        <Link className="rounded-lg px-3 py-1.5 text-zinc-300 ring-1 ring-zinc-700/60" to="/">
          操盘台
        </Link>
      </div>
    </div>
  );
}
