import useSWR from "swr";
import { Link } from "react-router-dom";
import { apiFetchV1 } from "../lib/api";
import { DEMO_STOCKS } from "../lib/demoCatalog";

type BriefingPayload = {
  ok?: boolean;
  narrative?: { headline?: string; summary?: string };
  top_picks?: Array<{ symbol?: string; name?: string }>;
  market_environment?: { regime_description?: string };
  message?: string;
};

type LifecyclePayload = {
  daily_briefing?: boolean;
  notifications?: { daily_briefing?: boolean };
};

const DEMO_DIGEST: BriefingPayload = {
  ok: true,
  narrative: {
    headline: "自选晨报（演示）",
    summary: "先扫自选与仓位风险，再决定是否追热门方向。",
  },
  top_picks: DEMO_STOCKS.slice(0, 3).map((s) => ({ symbol: s.symbol, name: s.name })),
  market_environment: { regime_description: "震荡分化" },
};

/** Compact morning digest teaser for the trading desk (in-app, not email). */
export function MorningDigestCard() {
  const { data: lifecycle } = useSWR(
    "desk-lifecycle-prefs",
    () => apiFetchV1<LifecyclePayload>("/user/lifecycle"),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  const briefingEnabled =
    lifecycle?.daily_briefing !== false && lifecycle?.notifications?.daily_briefing !== false;

  const { data, error, isLoading } = useSWR(
    briefingEnabled ? "desk-morning-digest" : null,
    () => apiFetchV1<BriefingPayload>("/briefing/smart-daily?market=CN&top_n=3&narrative=1"),
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  if (!briefingEnabled) {
    return (
      <div className="rounded-xl bg-zinc-900/40 px-4 py-3 text-sm text-zinc-500 ring-1 ring-zinc-800/50">
        自选晨报摘要已关闭。可在{" "}
        <Link className="text-emerald-400/90 hover:underline" to="/profile">
          个人中心
        </Link>{" "}
        重新打开。
      </div>
    );
  }

  const isDemo =
    Boolean(error) ||
    !data ||
    data.ok === false ||
    (!(data.narrative?.summary) && !(data.top_picks ?? []).length);
  const view = isDemo ? DEMO_DIGEST : data;
  const picks = (view.top_picks ?? []).slice(0, 3);

  return (
    <section className="rounded-xl bg-zinc-900/50 p-4 ring-1 ring-zinc-800/50">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono uppercase tracking-[0.16em] text-zinc-500">Morning Digest</span>
            {isDemo || isLoading ? (
              <span className="font-mono text-[10px] text-amber-400/80">{isLoading ? "加载中" : "演示"}</span>
            ) : null}
          </div>
          <h2 className="mt-1 text-base font-semibold text-zinc-100">
            {view.narrative?.headline || "自选晨报"}
          </h2>
          <p className="mt-1 line-clamp-2 text-sm text-zinc-400">
            {view.narrative?.summary || view.message || "今日摘要准备中"}
          </p>
          {view.market_environment?.regime_description ? (
            <p className="mt-1 font-mono text-[11px] text-zinc-600">
              {view.market_environment.regime_description}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Link
            to="/watchlist-briefing"
            className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30"
          >
            打开晨报
          </Link>
          <Link
            to="/paper-trading"
            className="rounded-lg px-3 py-1.5 text-xs text-zinc-400 ring-1 ring-zinc-700/60 hover:bg-zinc-800"
          >
            模拟交易
          </Link>
        </div>
      </div>
      {picks.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {picks.map((p) => (
            <Link
              key={`${p.symbol}-${p.name}`}
              to={`/stock/${encodeURIComponent(p.symbol || "")}?m=CN`}
              className="rounded-lg bg-zinc-800/50 px-2.5 py-1 font-mono text-[11px] text-zinc-300 ring-1 ring-zinc-700/40 hover:text-emerald-300"
            >
              {p.symbol}
              {p.name ? <span className="ml-1 font-sans text-zinc-500">{p.name}</span> : null}
            </Link>
          ))}
        </div>
      ) : null}
    </section>
  );
}
