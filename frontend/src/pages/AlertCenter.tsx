import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types (aligned with AlertEventDTO /system/alerts) ── */
type AlertSeverity = "info" | "warning" | "critical";

type AlertApiItem = {
  id: string;
  level?: AlertSeverity;
  category?: string;
  title: string;
  message: string;
  source: string;
  occurred_at?: string;
  meta?: Record<string, unknown>;
};

type AlertFeed = {
  items: AlertApiItem[];
  total: number;
  counts_by_level?: Record<string, number>;
  counts_by_category?: Record<string, number>;
};

type Alert = {
  id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  source: string;
  category?: string;
  symbol?: string;
  created_at: string;
  action_url?: string;
};

function mapAlert(item: AlertApiItem): Alert {
  const meta = item.meta || {};
  const level = item.level;
  const severity: AlertSeverity =
    level === "critical" || level === "warning" || level === "info" ? level : "info";
  const actionRaw = meta.action_url;
  const symbolRaw = meta.symbol;
  return {
    id: item.id,
    title: item.title,
    message: item.message,
    severity,
    source: item.source,
    category: item.category,
    symbol: typeof symbolRaw === "string" ? symbolRaw : undefined,
    created_at: item.occurred_at || "",
    action_url: typeof actionRaw === "string" ? actionRaw : undefined,
  };
}

type AlertDispatchResult = {
  sent?: number;
  failed?: number;
  skipped?: boolean;
  deduplicated?: boolean;
  alert_count?: number;
  message?: string;
};

function fetchAlerts(): Promise<AlertFeed> {
  return apiFetchV1<AlertFeed>("/system/alerts?limit=50&include_probes=1");
}

type DispatchChannel = "webhook" | "dingtalk" | "email" | "wechat";

type ChannelStatusRow = {
  channel: string;
  configured: boolean;
  label: string;
};

type ChannelsPayload = {
  channels: ChannelStatusRow[];
  configured_count: number;
  total: number;
};

const DISPATCH_CHANNELS: { id: DispatchChannel; label: string }[] = [
  { id: "webhook", label: "Webhook" },
  { id: "dingtalk", label: "钉钉" },
  { id: "email", label: "邮件" },
  { id: "wechat", label: "微信" },
];

function fetchChannelStatus(): Promise<ChannelsPayload> {
  return apiFetchV1<ChannelsPayload>("/system/alerts/channels");
}

async function dispatchAlerts(opts: {
  minLevel: AlertSeverity;
  channels: DispatchChannel[];
  respectDedup: boolean;
}): Promise<AlertDispatchResult> {
  const level = opts.minLevel === "info" ? "warning" : opts.minLevel;
  return apiFetchV1<AlertDispatchResult>("/system/alerts/dispatch", {
    method: "POST",
    body: JSON.stringify({
      min_level: level,
      limit: 20,
      include_probes: true,
      respect_dedup: opts.respectDedup,
      channels: opts.channels.length ? opts.channels : undefined,
    }),
  });
}

function fmtDate(iso?: string): string {
  if (!iso) return "--";
  try {
    return new Date(iso).toLocaleString("zh-CN");
  } catch {
    return iso;
  }
}

function severityBadge(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "badge-error";
    case "warning":
      return "badge-warning";
    case "info":
    default:
      return "badge-info";
  }
}

function severityLabel(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "严重";
    case "warning":
      return "预警";
    case "info":
    default:
      return "提示";
  }
}

/* ── Component ── */
export function AlertCenterPage() {
  const [filterSeverity, setFilterSeverity] = useState<AlertSeverity | "all">("all");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [dispatchChannels, setDispatchChannels] = useState<DispatchChannel[]>([]);
  const [channelsHydrated, setChannelsHydrated] = useState(false);
  const [respectDedup, setRespectDedup] = useState(true);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchNote, setDispatchNote] = useState<string | null>(null);

  const { data, error, isLoading, mutate } = useSWR("system/alerts", () => fetchAlerts(), {
    refreshInterval: 60_000,
  });
  const { data: channelsData } = useSWR("system/alerts/channels", () => fetchChannelStatus());

  const channelConfigured = useMemo(() => {
    const map = new Map<DispatchChannel, boolean>();
    for (const row of channelsData?.channels ?? []) {
      if (row.channel === "webhook" || row.channel === "dingtalk" || row.channel === "email" || row.channel === "wechat") {
        map.set(row.channel, Boolean(row.configured));
      }
    }
    return map;
  }, [channelsData]);

  useEffect(() => {
    if (!channelsData?.channels || channelsHydrated) return;
    const configured = channelsData.channels
      .filter((c) => c.configured)
      .map((c) => c.channel)
      .filter((c): c is DispatchChannel =>
        c === "webhook" || c === "dingtalk" || c === "email" || c === "wechat",
      );
    setDispatchChannels(
      configured.length ? configured : (["webhook", "dingtalk", "email"] as DispatchChannel[]),
    );
    setChannelsHydrated(true);
  }, [channelsData, channelsHydrated]);

  const alerts = useMemo(() => (data?.items ?? []).map(mapAlert), [data?.items]);
  const warningCount = data?.counts_by_level?.warning ?? 0;
  const criticalCount = data?.counts_by_level?.critical ?? 0;
  const dumpCount = alerts.filter((a) => a.id === "data:quotes:full_dump").length;
  const configuredCount = channelsData?.configured_count ?? 0;

  const filtered = alerts.filter((a: Alert) => {
    if (filterSeverity !== "all" && a.severity !== filterSeverity) return false;
    if (filterCategory !== "all" && a.category !== filterCategory) return false;
    return true;
  });

  function toggleChannel(id: DispatchChannel) {
    setDispatchChannels((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  }

  async function onDispatch() {
    if (!dispatchChannels.length) {
      setDispatchNote("请至少选择一个推送渠道");
      return;
    }
    const channelLabels = dispatchChannels
      .map((id) => DISPATCH_CHANNELS.find((c) => c.id === id)?.label ?? id)
      .join(" / ");
    if (
      !window.confirm(
        `将 Warning+ 告警推送到：${channelLabels}？（含 quotes dump；dedup=${respectDedup ? "开" : "关"}）`,
      )
    ) {
      return;
    }
    setDispatching(true);
    setDispatchNote(null);
    try {
      const minLevel =
        filterSeverity === "critical" || filterSeverity === "warning" ? filterSeverity : "warning";
      const result = await dispatchAlerts({
        minLevel,
        channels: dispatchChannels,
        respectDedup,
      });
      if (result.deduplicated) {
        setDispatchNote("冷却期内已推送过相同指纹，已跳过（respect_dedup）");
      } else if (result.skipped) {
        setDispatchNote(result.message || "已跳过推送");
      } else {
        setDispatchNote(
          `推送完成：成功 ${result.sent ?? 0} 渠道，失败 ${result.failed ?? 0}（告警 ${result.alert_count ?? 0} 条）`,
        );
      }
      await mutate();
    } catch (e) {
      setDispatchNote(`推送失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setDispatching(false);
    }
  }

  if (isLoading && !alerts.length) return <PageSkeleton rows={5} showProgress />;

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.alertCenter} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">预警中心</h1>
          <p className="text-sm text-[var(--quant-muted)]">
            任务失败、数据新鲜度、quotes dump 与系统探针统一聚合（/api/v1/system/alerts）
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="btn btn-ghost btn-sm">
            严重 <span className="badge badge-error ml-1">{criticalCount}</span>
          </span>
          <span className="btn btn-ghost btn-sm">
            预警 <span className="badge badge-warning ml-1">{warningCount}</span>
          </span>
          {dumpCount > 0 ? (
            <span className="btn btn-ghost btn-sm text-amber-500">
              dump <span className="badge badge-warning ml-1">{dumpCount}</span>
            </span>
          ) : null}
          <span className="btn btn-ghost btn-sm">
            已配置渠道 <span className="badge badge-info ml-1">{configuredCount}</span>
          </span>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={dispatching}
            onClick={() => void onDispatch()}
          >
            {dispatching ? "推送中…" : "推送渠道"}
          </button>
        </div>
      </div>

      {dispatchNote ? <div className="alert alert-info text-sm">{dispatchNote}</div> : null}

      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <select
          className="select select-bordered select-sm"
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value as AlertSeverity | "all")}
        >
          <option value="all">全部级别</option>
          <option value="critical">严重</option>
          <option value="warning">预警</option>
          <option value="info">提示</option>
        </select>
        <select
          className="select select-bordered select-sm"
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
        >
          <option value="all">全部分类</option>
          <option value="data">数据</option>
          <option value="task">任务</option>
          <option value="system">系统</option>
          <option value="factor">因子</option>
          <option value="consensus">共识</option>
          <option value="execution">执行</option>
        </select>
        <span className="mx-1 h-4 w-px bg-zinc-700/60" aria-hidden />
        {DISPATCH_CHANNELS.map((ch) => (
          <label key={ch.id} className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-400">
            <input
              type="checkbox"
              className="checkbox checkbox-xs"
              checked={dispatchChannels.includes(ch.id)}
              onChange={() => toggleChannel(ch.id)}
            />
            {ch.label}
            <span
              className={
                channelConfigured.get(ch.id)
                  ? "text-emerald-500/80"
                  : "text-zinc-600"
              }
            >
              {channelConfigured.get(ch.id) ? "·已配置" : "·未配置"}
            </span>
          </label>
        ))}
        <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-400">
          <input
            type="checkbox"
            className="checkbox checkbox-xs"
            checked={respectDedup}
            onChange={(e) => setRespectDedup(e.target.checked)}
          />
          冷却去重
        </label>
      </div>

      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      <section className="glass-card overflow-x-auto">
        <table className="table w-full">
          <thead>
            <tr>
              <th>级别</th>
              <th>标题</th>
              <th>分类</th>
              <th>来源</th>
              <th>标的</th>
              <th>时间</th>
              <th className="w-24">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a: Alert) => (
              <tr key={a.id}>
                <td>
                  <span className={`badge ${severityBadge(a.severity)}`}>
                    {severityLabel(a.severity)}
                  </span>
                </td>
                <td className="max-w-xs truncate">
                  <div className="font-medium">{a.title}</div>
                  <div className="text-xs text-slate-500 truncate">{a.message}</div>
                </td>
                <td className="text-xs text-slate-500">{a.category || "--"}</td>
                <td className="text-xs text-slate-500">{a.source}</td>
                <td>
                  {a.symbol ? <code>{a.symbol}</code> : <span className="text-slate-400">--</span>}
                </td>
                <td className="text-xs text-slate-500 whitespace-nowrap">
                  {fmtDate(a.created_at)}
                </td>
                <td>
                  {a.action_url ? (
                    a.action_url.startsWith("/") ? (
                      <Link to={a.action_url} className="btn btn-ghost btn-xs">
                        详情
                      </Link>
                    ) : (
                      <a
                        href={a.action_url}
                        className="btn btn-ghost btn-xs"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        详情
                      </a>
                    )
                  ) : (
                    <span className="text-slate-400 text-xs">--</span>
                  )}
                </td>
              </tr>
            ))}
            {!filtered.length && (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-500">
                  暂无预警
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
