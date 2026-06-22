import useSWR from "swr";
import { apiFetchV1 } from "../lib/api";

type TierData = {
  tier?: string;
  benefits?: string[];
  is_active?: boolean;
};

export default function UserTiersBoutique() {
  const { data, error, isLoading, mutate } = useSWR<TierData>("/user/tiers/boutique", apiFetchV1);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">精品层级</h1>
          <p className="text-[var(--quant-muted)] text-sm">Boutique 会员权益</p>
        </div>
        <button type="button" className="btn-brand btn-sm" onClick={() => mutate()}>刷新</button>
      </div>

      {isLoading && !data ? <div className="quant-card p-6 text-center text-[var(--quant-muted)]">加载中...</div> : null}
      {error ? <div className="quant-card p-6 text-red-500">加载失败: {error.message}</div> : null}

      {data ? (
        <div className="quant-card p-6 max-w-xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="text-xs text-[var(--quant-muted)] mb-1">当前层级</div>
              <div className="text-2xl font-bold">{data.tier || "未激活"}</div>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${data.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>{data.is_active ? "已激活" : "未激活"}</span>
          </div>
          <h3 className="text-sm font-semibold text-[var(--quant-muted)] uppercase tracking-wider mb-3">权益清单</h3>
          {data.benefits && data.benefits.length > 0 ? (
            <ul className="space-y-2">
              {data.benefits.map((b, i) => (
                <li key={i} className="flex items-center gap-2 text-sm"><span className="text-green-500">&#10003;</span>{b}</li>
              ))}
            </ul>
          ) : <p className="text-[var(--quant-muted)] text-sm">暂无权益</p>}
          <div className="mt-6 pt-4 border-t border-[var(--quant-border)]">
            <button type="button" className="btn-brand w-full text-center">升级方案</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
