import { Link, Outlet, useNavigate } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import { logoutSession } from "../lib/api";
import { useAuth } from "../hooks/useAuth";
import { usePlatformFeatures } from "../hooks/usePlatformFeatures";
import { useTheme } from "../hooks/useTheme";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { useTranslation } from "react-i18next";

interface LayoutProps {
  enableBackToClassic?: boolean;
  backToClassicUrl?: string;
}

interface NavItem {
  label: string;
  to?: string;
  href?: string;
  badge?: string;
  feature?: string;
}

interface NavGroup {
  label: string;
  icon: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "操盘台",
    icon: "🏠",
    items: [
      { label: "今日操盘台", to: "/" },
      { label: "自选股", to: "/self-stocks" },
      { label: "市场全景", to: "/market-panorama" },
      { label: "全球透视塔", to: "/global-radar" },
      { label: "热点板块", to: "/hot-sectors" },
      { label: "龙虎榜", to: "/longhu-bang" },
      { label: "研报中心", to: "/yanbao-hub" },
      { label: "通达信板块", to: "/tdx-blocks" },
    ],
  },
  {
    label: "研究",
    icon: "🔬",
    items: [
      { label: "AI 投委会", to: "/ai-investment-committee" },
      { label: "AI 诊股", to: "/ai-analysis" },
      { label: "研究报告", to: "/ai-research-report" },
      { label: "AI 对冲基金", to: "/ai-hedge-fund" },
      { label: "量化实验室", href: "/quant-lab" },
      { label: "War Room", to: "/war-room" },
      { label: "语音简报", to: "/voice-briefing" },
      { label: "Agent 中心", to: "/agent-center" },
    ],
  },
  {
    label: "策略",
    icon: "📈",
    items: [
      { label: "策略回测", to: "/backtest" },
      { label: "信号旗", to: "/signal-flag" },
      { label: "智能选股", to: "/stock-selector" },
      { label: "模拟观察单", to: "/signal-observations" },
      { label: "策略向导", to: "/strategy-wizard" },
      { label: "Alpha Factory", to: "/alpha-factory" },
      { label: "因子市场", to: "/marketplace", feature: "feature_alpha_marketplace" },
      { label: "实验报告", to: "/experiments" },
    ],
  },
  {
    label: "我的",
    icon: "👤",
    items: [
      { label: "任务中心", to: "/task-center" },
      { label: "消息中心", to: "/message-center" },
      { label: "预警中心", to: "/alert-center" },
      { label: "协作空间", to: "/collaboration-workspace" },
      { label: "研究画布", to: "/research-canvas" },
      { label: "研究闭环", to: "/research-pipeline" },
    ],
  },
];

function DropdownGroup({
  group,
  features,
  onClose,
}: {
  group: NavGroup;
  features: Record<string, boolean>;
  onClose: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const visibleItems = group.items.filter(
    (item) => !item.feature || features[item.feature]
  );

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 px-3 py-2 rounded-xl text-sm font-medium
                   transition-all duration-200
                   hover:bg-[var(--quant-surface)] hover:text-[var(--quant-accent)]
                   data-[active=true]:bg-[var(--quant-surface)] data-[active=true]:text-[var(--quant-accent)]"
        data-active={open}
      >
        <span>{group.icon}</span>
        <span>{group.label}</span>
        <svg className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 w-56 py-2 rounded-xl z-50
                        bg-[var(--quant-surface-strong)] border border-[var(--quant-surface-border)]
                        shadow-[var(--quant-shadow)] backdrop-blur-xl">
          {visibleItems.map((item) => (
            <Link
              key={item.label}
              to={item.to ?? item.href!}
              onClick={onClose}
              className="block px-4 py-2 text-sm text-[var(--quant-fg)] hover:bg-[var(--quant-surface)] hover:text-[var(--quant-accent)] transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function Layout({ enableBackToClassic, backToClassicUrl }: LayoutProps) {
  const { t } = useTranslation();
  const { theme, toggle: toggleTheme } = useTheme();
  const { isAuthenticated, loading, mode, username, refresh } = useAuth();
  const { features } = usePlatformFeatures();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  async function onLogout() {
    await logoutSession();
    await refresh();
    navigate("/login", { replace: true });
  }

  const featureMap: Record<string, boolean> = features as Record<string, boolean>;

  return (
    <div className="min-h-screen">
      {/* ── Top Nav ──────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-[var(--quant-nav-border)] bg-[var(--quant-nav-bg)]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-2">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-2 text-lg font-bold text-[var(--quant-accent)] shrink-0">
            <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--quant-accent)]/15 text-sm">Q</span>
            <span className="hidden sm:inline">Quant Atlas</span>
          </Link>

          {/* Desktop Nav Groups */}
          <nav className="hidden lg:flex items-center gap-1">
            {NAV_GROUPS.map((group) => (
              <DropdownGroup
                key={group.label}
                group={group}
                features={featureMap}
                onClose={() => {}}
              />
            ))}
          </nav>

          {/* Right Side */}
          <div className="flex items-center gap-2">
            {loading ? (
              <span className="text-[var(--quant-muted)]">…</span>
            ) : isAuthenticated ? (
              <span className="hidden sm:flex items-center gap-2 text-sm text-[var(--quant-muted)]">
                <span>{username ?? (mode === "session" ? "已登录" : "用户")}</span>
                <button type="button" className="btn btn-ghost btn-xs" onClick={() => void onLogout()}>
                  退出
                </button>
              </span>
            ) : (
              <Link to="/login" className="btn-brand !px-3 !py-1.5 !text-xs !rounded-lg">
                {t("login", "登录")}
              </Link>
            )}
            <LanguageSwitcher />
            <button
              type="button"
              className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-[var(--quant-surface)] transition-colors"
              onClick={toggleTheme}
              aria-label="切换主题"
            >
              {theme === "light" ? "🌙" : "☀️"}
            </button>
            {/* Mobile hamburger */}
            <button
              type="button"
              className="lg:hidden w-8 h-8 rounded-lg flex items-center justify-center hover:bg-[var(--quant-surface)] transition-colors"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="菜单"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {mobileOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* ── Mobile Nav ────────────────────────────────────────── */}
        {mobileOpen && (
          <div className="lg:hidden border-t border-[var(--quant-nav-border)] bg-[var(--quant-nav-bg)] px-4 py-4 space-y-4">
            {NAV_GROUPS.map((group) => (
              <div key={group.label}>
                <div className="text-xs font-bold text-[var(--quant-muted)] uppercase tracking-wider mb-2">
                  {group.icon} {group.label}
                </div>
                <div className="grid grid-cols-2 gap-1">
                  {group.items
                    .filter((item) => !item.feature || featureMap[item.feature])
                    .map((item) => (
                      <Link
                        key={item.label}
                        to={item.to ?? item.href!}
                        onClick={() => setMobileOpen(false)}
                        className="block px-3 py-2 rounded-lg text-sm text-[var(--quant-fg)] hover:bg-[var(--quant-surface)] transition-colors"
                      >
                        {item.label}
                      </Link>
                    ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </header>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>

      {/* ── Back to Classic ──────────────────────────────────────── */}
      {enableBackToClassic && (
        <a
          href={backToClassicUrl || "/daily-workbench"}
          className="fixed bottom-4 right-4 text-xs text-[var(--quant-muted)] hover:text-[var(--quant-accent)] transition-colors z-50
                     px-3 py-1.5 rounded-full bg-[var(--quant-surface-strong)] border border-[var(--quant-surface-border)] backdrop-blur"
        >
          ← 回到经典版
        </a>
      )}
    </div>
  );
}
