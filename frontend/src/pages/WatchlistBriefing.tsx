import useSWR from "swr";
import { Link } from "react-router-dom";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_STOCKS } from "../lib/demoCatalog";
import type { WatchlistStock } from "../types/watchlist";

type BriefingPayload = {
  ok?: boolean;
  market?: string;
  generated_at?: string;
  market_environment?: { regime_description?: string; sentiment_score?: number };
  narrative?: { headline?: string; summary?: string; bullets?: string[] };
  top_picks?: Array<{ symbol?: string; name?: string; reason?: string; score?: number }>;
  watchlist_notes?: Array<{ symbol?: string; name?: string; note?: string }>;
  message?: string;
};

type ExperiencePayload = {
  items?: Array<WatchlistStock & { code?: string; note?: string; risk_level?: string }>;
  summary?: { text?: string; avg_score?: number; total?: number };
};

const DEMO_BRIEFING: BriefingPayload = {
  ok: true,
  market: "CN",
  generated_at: "演示",
  market_environment: { regime_description: "震荡市 · 结构性分化", sentiment_score: 52 },
  narrative: {
    headline: "自选晨报（演示）",
    summary: "行情源未就绪时展示样本摘要。建议先核对自选与仓位风险，再决定是否加仓热门方向。",
    bullets: ["白酒龙头波动收敛，关注量能确认", "金融权重分化，银行相对稳健", "避免追高情绪股，优先等待回踩"],
  },
  top_picks: DEMO_STOCKS.slice(0, 3).map((s) => ({
    symbol: s.symbol,
    name: s.name,
    reason: "演示样本：自选关联热度",
    score: s.health_score,
  })),
  watchlist_notes: DEMO_STOCKS.map((s) => ({
    symbol: s.symbol,
    name: s.name,
    note: s.change_pct >= 0 ? "偏强 · 注意回撤" : "偏弱 · 观察支撑",
  })),
};

function fmtPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function notesFromWatchlist(exp?: ExperiencePayload | null): BriefingPayload["watchlist_notes"] {
  const items = exp?.items ?? [];
  if (!items.length) return [];
  return items.slice(0, 12).map((row) => {
    const symbol = row.symbol || row.code || "";
    const pct = fmtPct(row.change_pct);
    const health = row.health_score != null ? `健康度 ${Math.round(row.health_score)}` : null;
    const risk = row.risk_level ? `风险 ${row.risk_level}` : null;
    const custom = row.note?.trim();
    const bits = [custom, health, `涨跌 ${pct}`, risk].filter(Boolean);
    return {
      symbol,
      name: row.name,
      note: bits.join(" · ") || "自选关注",
    };
  });
}

export function WatchlistBriefingPage() {
  const { data, error, isLoading, mutate } = useSWR(
    "watchlist-briefing",
    () => apiFetchV1<BriefingPayload>("/briefing/smart-daily?market=CN&top_n=5&narrative=1"),
    { revalidateOnFocus: false },
  );

  const { data: wlExp } = useSWR(
    "watchlist-briefing-experience",
    () =>
      apiFetchV1<ExperiencePayload>(
        "/watchlist/experience?sort_by=priority&include_news=false&market=CN",
      ),
    { revalidateOnFocus: false },
  );

  if (isLoading && !data) return <PageSkeleton rows={4} />;

  const isDemo =
    Boolean(error) ||
    !data ||
    data.ok === false ||
    (!(data.top_picks ?? []).length && !(data.narrative?.summary));
  const view = isDemo ? DEMO_BRIEFING : data;
  const picks = view.top_picks ?? [];
  const liveNotes = notesFromWatchlist(wlExp);
  const notes = liveNotes.length > 0 ? liveNotes : (view.watchlist_notes ?? []);
  const bullets = view.narrative?.bullets ?? [];
  const notesSource = liveNotes.length > 0 ? "自选实时" : isDemo ? "演示" : "晨报接口";

  return (
    <div className="mx-auto max-w-[960px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.dashboard} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Watchlist Morning Brief</div>
          <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">自选晨报</h1>
          <p className="mt-1 text-sm text-zinc-500">按自选与市场环境生成的一页摘要（非投资建议）</p>
          <DemoBanner show={isDemo} />
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void mutate()}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-300 ring-1 ring-zinc-700/60 hover:bg-zinc-800"
          >
            刷新
          </button>
          <Link
            to="/self-stocks"
            className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30"
          >
            打开自选
          </Link>
        </div>
      </div>

      <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
        <h2 className="text-lg font-semibold text-zinc-100">{view.narrative?.headline || "今日摘要"}</h2>
        <p className="mt-2 text-sm leading-relaxed text-zinc-300">{view.narrative?.summary || view.message || "暂无摘要"}</p>
        <div className="mt-3 flex flex-wrap gap-3 text-[11px] font-mono text-zinc-500">
          <span>市场 {view.market || "CN"}</span>
          {view.market_environment?.regime_description ? <span>{view.market_environment.regime_description}</span> : null}
          {view.market_environment?.sentiment_score != null ? <span>情绪 {view.market_environment.sentiment_score}</span> : null}
          {view.generated_at ? <span>{view.generated_at}</span> : null}
        </div>
      </section>

      {bullets.length > 0 ? (
        <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
          <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">要点</h3>
          <ul className="mt-3 space-y-2">
            {bullets.map((b) => (
              <li key={b} className="flex gap-2 text-sm text-zinc-200">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400/80" />
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
        <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">关注标的</h3>
        <div className="mt-3 divide-y divide-zinc-800/80">
          {picks.map((p) => (
            <Link
              key={`${p.symbol}-${p.name}`}
              to={`/stock/${encodeURIComponent(p.symbol || "")}?m=CN`}
              className="flex items-start justify-between gap-3 py-3 hover:bg-zinc-800/30"
            >
              <div>
                <div className="font-mono text-sm text-emerald-300">{p.symbol}</div>
                <div className="text-sm text-zinc-200">{p.name || "—"}</div>
                <div className="mt-1 text-xs text-zinc-500">{p.reason || "—"}</div>
              </div>
              {p.score != null ? <div className="font-mono text-xs text-zinc-400">{p.score}</div> : null}
            </Link>
          ))}
        </div>
      </section>

      {notes.length > 0 ? (
        <section className="rounded-xl bg-zinc-900/50 p-5 ring-1 ring-zinc-800/50">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-400">自选备注</h3>
            <span className="font-mono text-[10px] text-zinc-600">{notesSource}</span>
          </div>
          <ul className="mt-3 space-y-2">
            {notes.map((n) => (
              <li key={`${n.symbol}-${n.note}`} className="flex flex-wrap items-baseline gap-2 text-sm">
                <Link className="font-mono text-emerald-400" to={`/stock/${encodeURIComponent(n.symbol || "")}?m=CN`}>
                  {n.symbol}
                </Link>
                <span className="text-zinc-300">{n.name}</span>
                <span className="text-zinc-500">{n.note}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className="text-xs text-zinc-600">
        数据可能延迟或为演示样本。详见{" "}
        <Link className="text-emerald-400/90 hover:underline" to="/market-coverage">
          数据与市场说明
        </Link>
        。
      </p>
    </div>
  );
}
