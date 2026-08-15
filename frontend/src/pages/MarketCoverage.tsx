import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { fetchDataSources, fetchTimeseriesHealth } from "../lib/api";

const SECTIONS = [
  {
    title: "行情与延迟",
    body: "A 股主路径优先本地 TDX / 缓存；港美与加密可能走外源。公共源常有延迟，盘中数字不等于交易所实盘。",
  },
  {
    title: "复权与批量查询",
    body: "个股 K 线支持前复权 / 后复权 / 不复权参数；批量接口 POST /api/v1/data/bars/batch 适合自选与板块成分扫描（借鉴本地量化引擎的批量读法，不嵌入外部 C++ 引擎）。",
  },
  {
    title: "演示数据 (data_mode)",
    body: "当行情源为空或接口失败时，SPA 会展示带「演示」标注的样本行，便于浏览流程。演示不是 SLA，也不是实盘报价。",
  },
  {
    title: "非投资建议",
    body: "Quant Atlas 是研究与监控工具，不提供证券经纪服务，也不构成投资建议。",
  },
];

type SourceRow = {
  name?: string;
  type?: string;
  scope?: string;
  market?: string;
  description?: string;
  priority?: number;
};

export function MarketCoveragePage() {
  const { data: health, error: healthErr } = useSWR("coverage-ts-health", () => fetchTimeseriesHealth(), {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });
  const { data: sources, error: sourcesErr } = useSWR("coverage-data-sources", () => fetchDataSources(), {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  const sourceItems = (sources?.items ?? []) as SourceRow[];
  const isDemo = Boolean(healthErr || sourcesErr) || (!health && !sourceItems.length);

  return (
    <div className="mx-auto max-w-[900px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.dashboard} />
      <div>
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Local Data Engine</div>
        <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">数据与市场说明</h1>
        <p className="mt-1 text-sm text-zinc-500">
          说清能力边界；下方为实时数据源注册表与时序健康（借鉴 free-stockdb「本地数据底座」思路）。
        </p>
        <DemoBanner show={isDemo} />
      </div>

      <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
        <h2 className="text-sm font-semibold text-zinc-100">时序健康</h2>
        {health ? (
          <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-zinc-950/60 p-3 font-mono text-[11px] text-zinc-400">
            {JSON.stringify(health, null, 2)}
          </pre>
        ) : (
          <p className="mt-2 text-sm text-zinc-500">{healthErr ? healthErr.message : "加载中或暂不可用"}</p>
        )}
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <Link className="rounded-lg px-3 py-1.5 text-zinc-300 ring-1 ring-zinc-700/60" to="/data-lake-health">
            数据湖健康
          </Link>
          <Link className="rounded-lg px-3 py-1.5 text-zinc-300 ring-1 ring-zinc-700/60" to="/integration-hub">
            集成中枢 / 同步
          </Link>
        </div>
      </section>

      <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold text-zinc-100">已注册数据源</h2>
          <span className="font-mono text-[10px] text-zinc-600">
            {sources?.count ?? sourceItems.length} · GET /data/sources
          </span>
        </div>
        {sourceItems.length ? (
          <ul className="mt-3 divide-y divide-zinc-800/80">
            {sourceItems.map((s) => (
              <li key={`${s.name}-${s.type}-${s.scope}`} className="flex flex-wrap items-baseline justify-between gap-2 py-2 text-sm">
                <div>
                  <span className="font-mono text-emerald-400/90">{s.name}</span>
                  <span className="ml-2 text-zinc-500">
                    {s.type}/{s.scope}/{s.market}
                  </span>
                  {s.description ? <p className="mt-0.5 text-xs text-zinc-500">{s.description}</p> : null}
                </div>
                <span className="font-mono text-[11px] text-zinc-600">p{s.priority ?? 0}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-zinc-500">注册表为空或接口未就绪（演示环境常见）。</p>
        )}
      </section>

      <div className="space-y-3">
        {SECTIONS.map((s) => (
          <section key={s.title} className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
            <h2 className="text-sm font-semibold text-zinc-100">{s.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-zinc-400">{s.body}</p>
          </section>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        <Link className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-emerald-400 ring-1 ring-emerald-500/30" to="/tdx-blocks">
          通达信板块
        </Link>
        <Link className="rounded-lg px-3 py-1.5 text-zinc-300 ring-1 ring-zinc-700/60" to="/watchlist-briefing">
          自选晨报
        </Link>
        <Link className="rounded-lg px-3 py-1.5 text-zinc-300 ring-1 ring-zinc-700/60" to="/">
          操盘台
        </Link>
      </div>
    </div>
  );
}
