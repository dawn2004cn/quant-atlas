import { Link, NavLink, useLocation } from "react-router-dom";

export type QuickNavItem = { to: string; label: string };

const CORE: QuickNavItem[] = [
  { to: "/", label: "操盘台" },
  { to: "/self-stocks", label: "自选" },
  { to: "/watchlist-briefing", label: "晨报" },
  { to: "/paper-trading", label: "模拟" },
  { to: "/hot-sectors", label: "热点" },
  { to: "/stock-selector", label: "选股" },
  { to: "/backtest", label: "回测" },
  { to: "/ai-analysis", label: "诊股" },
  { to: "/portfolio", label: "组合" },
];

function preset(...extra: QuickNavItem[]): QuickNavItem[] {
  const seen = new Set<string>();
  const out: QuickNavItem[] = [];
  for (const item of [...CORE, ...extra]) {
    if (seen.has(item.to)) continue;
    seen.add(item.to);
    out.push(item);
  }
  return out;
}

const SPECIFIC: Record<string, QuickNavItem[]> = {
  dashboard: preset(),
  backtest: preset({ to: "/strategy-wizard", label: "向导" }, { to: "/strategy-compare", label: "对比" }),
  aiAnalysis: preset({ to: "/stock-selector", label: "选股" }),
  stockDetail: preset({ to: "/ai-analysis", label: "诊股" }),
  marketplace: preset({ to: "/factor-repository", label: "因子" }),
  selfStocks: preset({ to: "/signal-flag", label: "信号旗" }),
};

export const QUICK_NAV_PRESETS: Record<string, QuickNavItem[]> = new Proxy(SPECIFIC, {
  get(target, key: string) {
    return target[key] ?? CORE;
  },
});

export function CoreWorkflowStrip() {
  const { pathname } = useLocation();
  return (
    <nav
      aria-label="核心工作流"
      className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      {CORE.map((item) => {
        const active = pathname === item.to || (item.to !== "/" && pathname.startsWith(item.to));
        return (
          <NavLink
            key={item.to}
            to={item.to}
            className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ring-1 transition-colors ${
              active
                ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30"
                : "bg-zinc-900/40 text-zinc-400 ring-zinc-800/80 hover:text-zinc-200 hover:ring-zinc-700"
            }`}
          >
            {item.label}
          </NavLink>
        );
      })}
    </nav>
  );
}

export function PageQuickNav({ items }: { items: QuickNavItem[] }) {
  const { pathname } = useLocation();
  const links = items?.length ? items : CORE;
  return (
    <nav aria-label="页面快捷跳转" className="flex flex-wrap gap-1.5">
      {links.map((item) => {
        const active = pathname === item.to;
        return (
          <Link
            key={`${item.to}-${item.label}`}
            to={item.to}
            className={`rounded-md px-2 py-1 text-[11px] transition-colors ${
              active
                ? "bg-zinc-800 text-zinc-100"
                : "text-zinc-500 hover:bg-zinc-800/70 hover:text-zinc-300"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function CoreNextSteps({ symbol }: { symbol?: string }) {
  const encoded = symbol ? encodeURIComponent(symbol) : "";
  return (
    <div className="flex flex-wrap gap-2">
      {symbol ? (
        <Link
          to={`/stock/${encoded}`}
          className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-xs font-medium text-emerald-300 ring-1 ring-emerald-500/25"
        >
          标的详情
        </Link>
      ) : null}
      <Link
        to="/backtest"
        className="rounded-lg bg-zinc-800/80 px-3 py-1.5 text-xs font-medium text-zinc-300 ring-1 ring-zinc-700/80 hover:text-zinc-100"
      >
        回测验证
      </Link>
      <Link
        to="/ai-analysis"
        className="rounded-lg bg-zinc-800/80 px-3 py-1.5 text-xs font-medium text-zinc-300 ring-1 ring-zinc-700/80 hover:text-zinc-100"
      >
        AI 诊股
      </Link>
      <Link
        to="/signal-observations"
        className="rounded-lg bg-zinc-800/80 px-3 py-1.5 text-xs font-medium text-zinc-300 ring-1 ring-zinc-700/80 hover:text-zinc-100"
      >
        加入观察
      </Link>
    </div>
  );
}
