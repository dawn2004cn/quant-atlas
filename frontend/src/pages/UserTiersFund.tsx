import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_TIER_FUND } from "../lib/demoCatalog";

type TierData = {
  tier?: string;
  benefits?: string[];
  is_active?: boolean;
};

export default function UserTiersFund() {
  const { data, error, isLoading, mutate } = useSWR<TierData>("/user/tiers/fund", apiFetchV1);

  const isDemo = Boolean(error) || !data || (!(data.benefits ?? []).length && !data.tier);
  const view = isDemo ? DEMO_TIER_FUND : data!;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.userTiers} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">基金层级</h1>
          <p className="text-[var(--quant-muted)] text-sm">Fund 会员权益</p>
          <DemoBanner show={isDemo} />
        </div>
        <button type="button" className="btn-brand btn-sm" onClick={() => mutate()}>刷新</button>
      </div>

      {isLoading && !data && !error ? <div className="quant-card p-6 text-center text-[var(--quant-muted)]">加载中...</div> : null}

      <div className="quant-card p-6 max-w-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="text-xs text-[var(--quant-muted)] mb-1">当前层级</div>
            <div className="text-2xl font-bold">{view.tier || "未激活"}</div>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${view.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>{view.is_active ? "已激活" : "未激活"}</span>
        </div>
        <h3 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider mb-3">权益清单</h3>
        {view.benefits && view.benefits.length > 0 ? (
          <ul className="space-y-2">
            {view.benefits.map((b, i) => (
              <li key={i} className="flex items-center gap-2 text-sm"><span className="text-green-500">&#10003;</span>{b}</li>
            ))}
          </ul>
        ) : <p className="text-[var(--quant-muted)] text-sm">暂无权益</p>}
        <div className="mt-6 pt-4 border-t border-[var(--quant-border)]">
          <button type="button" className="btn-brand w-full text-center">升级方案</button>
        </div>
      </div>
    </div>
  );
}
