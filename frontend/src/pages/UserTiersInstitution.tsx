import { useState, useEffect, useCallback } from "react";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { apiFetchV1 } from "../lib/api";
import { DEMO_TIER_INSTITUTION } from "../lib/demoCatalog";

type InstitutionTier = {
  tier?: string;
  name?: string;
  active?: boolean;
  benefits?: string[];
  api_access?: boolean;
  dedicated_support?: boolean;
  custom_workflows?: boolean;
  upgrade_path?: string;
  monthly_fee?: number;
  api_limits?: { daily?: number; concurrent?: number };
};

export default function UserTiersInstitution() {
  const [tier, setTier] = useState<InstitutionTier | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetchV1<InstitutionTier>("/user/tiers/institution");
      if (!data || (!data.tier && !(data.benefits ?? []).length)) {
        setTier(DEMO_TIER_INSTITUTION);
        setIsDemo(true);
      } else {
        setTier(data);
        setIsDemo(false);
      }
    } catch {
      setTier(DEMO_TIER_INSTITUTION);
      setIsDemo(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !tier) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="page-title">机构版</h1>
          <p className="text-[var(--quant-muted)] text-sm mt-1">机构级功能与权益概览</p>
        </div>
        <div className="quant-card">
          <div className="flex items-center gap-3">
            <div className="skeleton h-6 w-32" />
            <div className="skeleton h-4 w-48" />
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="skeleton h-20" />
            <div className="skeleton h-20" />
          </div>
        </div>
      </div>
    );
  }

  const view = tier ?? DEMO_TIER_INSTITUTION;
  const benefits = view.benefits ?? DEMO_TIER_INSTITUTION.benefits;

  return (
    <div className="space-y-6">
      <PageQuickNav items={QUICK_NAV_PRESETS.userTiers} />
      <div>
        <h1 className="page-title">机构版</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">机构级功能与权益概览</p>
        <DemoBanner show={isDemo} />
      </div>

      <div className="quant-card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold">{view.name ?? "Institution"}</span>
              <span className={`badge-soft ${view.active ? "bg-[var(--quant-accent)]/10 text-[var(--quant-accent)]" : "bg-[var(--quant-muted)]/10 text-[var(--quant-muted)]"}`}>
                {view.active ? "激活" : "未激活"}
              </span>
            </div>
            <div className="text-xs text-[var(--quant-muted)] mt-1">当前方案: {view.tier ?? "institution"}</div>
          </div>
          {view.monthly_fee != null && (
            <div className="text-right">
              <div className="text-2xl font-bold mono text-[var(--quant-accent)]">¥{view.monthly_fee.toLocaleString()}</div>
              <div className="text-xs text-[var(--quant-muted)]">/ 月</div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className={`p-3 rounded-xl ${view.api_access ? "bg-[var(--quant-accent)]/10 border border-[var(--quant-accent)]/20" : "bg-[var(--quant-surface)] border border-[var(--quant-surface-border)]"}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={view.api_access ? "text-[var(--quant-accent)]" : "text-[var(--quant-muted)]"}>●</span>
              <span className="font-medium">API 访问</span>
            </div>
            <div className="text-xs text-[var(--quant-muted)]">
              {view.api_access ? `每日 ${view.api_limits?.daily?.toLocaleString() ?? "无限"} 次，并发 ${view.api_limits?.concurrent ?? "无限"}` : "基础版限额"}
            </div>
          </div>
          <div className={`p-3 rounded-xl ${view.dedicated_support ? "bg-[var(--quant-accent)]/10 border border-[var(--quant-accent)]/20" : "bg-[var(--quant-surface)] border border-[var(--quant-surface-border)]"}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={view.dedicated_support ? "text-[var(--quant-accent)]" : "text-[var(--quant-muted)]"}>●</span>
              <span className="font-medium">专属支持</span>
            </div>
            <div className="text-xs text-[var(--quant-muted)]">
              {view.dedicated_support ? "SLA 响应 < 4h" : "工单支持（24h）"}
            </div>
          </div>
          <div className={`p-3 rounded-xl ${view.custom_workflows ? "bg-[var(--quant-accent)]/10 border border-[var(--quant-accent)]/20" : "bg-[var(--quant-surface)] border border-[var(--quant-surface-border)]"}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={view.custom_workflows ? "text-[var(--quant-accent)]" : "text-[var(--quant-muted)]"}>●</span>
              <span className="font-medium">自定义工作流</span>
            </div>
            <div className="text-xs text-[var(--quant-muted)]">
              {view.custom_workflows ? "完全自定义部署" : "预设模板"}
            </div>
          </div>
        </div>

        <div className="border-t border-[var(--quant-surface-border)] pt-4">
          <div className="text-sm font-bold mb-3">权益详情</div>
          <ul className="space-y-2">
            {benefits.map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[var(--quant-fg)]">
                <span className="text-[var(--quant-accent)] mt-0.5">✓</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>

        {view.upgrade_path && (
          <div className="border-t border-[var(--quant-surface-border)] pt-4 mt-4">
            <div className="text-sm font-bold mb-2 text-[var(--quant-accent)]">升级路径</div>
            <div className="text-sm text-[var(--quant-muted)]">{view.upgrade_path}</div>
          </div>
        )}
      </div>
    </div>
  );
}
