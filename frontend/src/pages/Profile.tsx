import { useState, useEffect, useCallback } from "react";
import { apiFetchV1 } from "../lib/api";

type PagePrefs = { font_size?: string };
type AccessPolicy = { tier_label?: string; features?: Array<{ name: string; enabled: boolean }> };
type AuditEntry = { action?: string; target_id?: string; created_at?: string };
type NotificationPrefs = {
  site_message?: boolean;
  price_alerts?: boolean;
  risk_alerts?: boolean;
  psychology_alerts?: boolean;
  weekly_review?: boolean;
  wechat?: boolean;
  sms?: boolean;
};
type InvestmentProfile = { risk_level?: string; horizon?: string };

const TABS = [
  { key: "basic", label: "基本设置" },
  { key: "invest", label: "投资偏好" },
  { key: "tier", label: "等级与权限" },
  { key: "security", label: "安全审计" },
];

const NOTIF_LABELS: Record<string, string> = {
  site_message: "站内消息",
  price_alerts: "价格提醒",
  risk_alerts: "风险提醒",
  psychology_alerts: "心理提醒",
  weekly_review: "周度回顾",
  wechat: "微信推送",
  sms: "短信通知",
};

export default function Profile() {
  const [tab, setTab] = useState("basic");
  const [prefs, setPrefs] = useState<PagePrefs>({});
  const [policy, setPolicy] = useState<AccessPolicy>({});
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [notifs, setNotifs] = useState<NotificationPrefs>({});
  const [invest, setInvest] = useState<InvestmentProfile>({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [p, a, au, n, i] = await Promise.all([
        apiFetchV1<PagePrefs>("/user/page-preferences"),
        apiFetchV1<AccessPolicy>("/user/access-policy"),
        apiFetchV1<{ items?: AuditEntry[] }>("/user/audit-trail?limit=10"),
        apiFetchV1<NotificationPrefs>("/user/lifecycle"),
        apiFetchV1<InvestmentProfile>("/user/investment-profile"),
      ]);
      setPrefs(p);
      setPolicy(a);
      setAudit(au.items ?? []);
      setNotifs(n);
      setInvest(i);
    } catch { /* keep defaults */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function savePrefs() {
    setSaving(true);
    try {
      await apiFetchV1("/user/page-preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
      });
    } finally { setSaving(false); }
  }

  async function saveNotifs() {
    setSaving(true);
    try {
      await apiFetchV1("/user/notification-preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(notifs),
      });
    } finally { setSaving(false); }
  }

  async function saveInvest() {
    setSaving(true);
    try {
      await apiFetchV1("/user/investment-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(invest),
      });
    } finally { setSaving(false); }
  }

  return (
    <div className="space-y-6">
      <h1 className="page-title">个人中心</h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--quant-line-soft)] pb-0">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors -mb-px ${
              tab === t.key
                ? "text-[var(--quant-accent)] border-b-2 border-[var(--quant-accent)] bg-[var(--quant-surface)]"
                : "text-[var(--quant-muted)] hover:text-[var(--quant-fg)]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Basic Settings */}
      {tab === "basic" && (
        <div className="space-y-4">
          <div className="quant-card">
            <div className="text-sm font-bold mb-3">界面设置</div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-[var(--quant-muted)]">字体大小</span>
              <select
                value={prefs.font_size ?? "normal"}
                onChange={(e) => setPrefs({ ...prefs, font_size: e.target.value })}
                className="select select-bordered select-sm bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
              >
                <option value="small">小</option>
                <option value="normal">标准</option>
                <option value="large">大</option>
              </select>
            </div>
          </div>
          <div className="quant-card">
            <div className="text-sm font-bold mb-3">通知偏好</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {Object.entries(NOTIF_LABELS).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={!!(notifs as Record<string, boolean>)[key]}
                    onChange={(e) => setNotifs({ ...notifs, [key]: e.target.checked })}
                    className="checkbox checkbox-sm"
                  />
                  {label}
                </label>
              ))}
            </div>
            <button type="button" className="btn-brand !text-xs mt-4" onClick={saveNotifs} disabled={saving}>
              保存通知设置
            </button>
          </div>
          <button type="button" className="btn-brand" onClick={savePrefs} disabled={saving}>
            保存界面设置
          </button>
        </div>
      )}

      {/* Investment Profile */}
      {tab === "invest" && (
        <div className="quant-card space-y-4">
          <div>
            <div className="text-sm font-bold mb-2">风险偏好</div>
            <div className="flex gap-2">
              {[
                { key: "conservative", label: "保守型" },
                { key: "balanced", label: "平衡型" },
                { key: "aggressive", label: "激进型" },
              ].map((r) => (
                <button
                  key={r.key}
                  type="button"
                  onClick={() => setInvest({ ...invest, risk_level: r.key })}
                  className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                    invest.risk_level === r.key
                      ? "bg-[var(--quant-accent)]/15 text-[var(--quant-accent)] border border-[var(--quant-accent)]/30"
                      : "bg-[var(--quant-surface)] text-[var(--quant-muted)]"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-sm font-bold mb-2">投资周期</div>
            <div className="flex gap-2">
              {[
                { key: "short", label: "短线" },
                { key: "swing", label: "波段" },
                { key: "mid", label: "中线" },
                { key: "long", label: "长线" },
              ].map((h) => (
                <button
                  key={h.key}
                  type="button"
                  onClick={() => setInvest({ ...invest, horizon: h.key })}
                  className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                    invest.horizon === h.key
                      ? "bg-[var(--quant-accent)]/15 text-[var(--quant-accent)] border border-[var(--quant-accent)]/30"
                      : "bg-[var(--quant-surface)] text-[var(--quant-muted)]"
                  }`}
                >
                  {h.label}
                </button>
              ))}
            </div>
          </div>
          <button type="button" className="btn-brand" onClick={saveInvest} disabled={saving}>
            保存投资偏好
          </button>
        </div>
      )}

      {/* Tier & Permissions */}
      {tab === "tier" && (
        <div className="quant-card space-y-4">
          <div className="text-sm font-bold">当前等级</div>
          <div className="badge-soft text-base">{policy.tier_label ?? "标准用户"}</div>
          <div className="text-sm font-bold mt-4">已解锁功能</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {(policy.features ?? []).map((f) => (
              <div key={f.name} className={`flex items-center gap-2 text-sm ${f.enabled ? "" : "opacity-40"}`}>
                <span className={f.enabled ? "text-[var(--quant-accent)]" : "text-[var(--quant-muted)]"}>
                  {f.enabled ? "✓" : "🔒"}
                </span>
                {f.name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security Audit */}
      {tab === "security" && (
        <div className="quant-card space-y-4">
          <div className="text-sm font-bold">最近操作</div>
          {audit.length === 0 ? (
            <div className="text-sm text-[var(--quant-muted)]">暂无审计记录</div>
          ) : (
            <div className="space-y-2">
              {audit.map((a, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-[var(--quant-line-soft)] last:border-0 text-sm">
                  <span>{a.action}</span>
                  <span className="text-xs text-[var(--quant-muted)]">
                    {a.created_at ? new Date(a.created_at).toLocaleString() : "—"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
