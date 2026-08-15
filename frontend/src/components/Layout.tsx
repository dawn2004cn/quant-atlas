import { Link, NavLink, useNavigate } from "react-router-dom";
import { KeepAliveOutlet } from "./KeepAliveOutlet";
import { lazy, Suspense, useCallback, useState, useRef, useEffect } from "react";
import { logoutSession } from "../lib/api";
import { useAuth } from "../hooks/useAuth";
import { usePlatformFeatures, isNavItemVisible } from "../hooks/usePlatformFeatures";
import { usePersona, isPersonaNavVisible } from "../hooks/usePersona";
import { useTheme } from "../hooks/useTheme";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { useTranslation } from "react-i18next";
import { CommandPalette, useCommandPaletteHotkey } from "./CommandPalette";

const AiAssistantDrawer = lazy(() =>
  import("./AiAssistantDrawer").then((m) => ({ default: m.AiAssistantDrawer })),
);

interface LayoutProps {
  enableBackToClassic?: boolean;
  backToClassicUrl?: string;
}

interface NavItem {
  label: string;
  to?: string;
  href?: string;
  badge?: string;
  /** strategic_sunset feature key, e.g. feature_war_room */
  feature?: string;
  /** nav_menu item id, e.g. moments → nav_show_moments */
  navId?: string;
  /** Persona feature_mask key, e.g. show_alpha_mining */
  personaFeature?: string;
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
      { label: "自选晨报", to: "/watchlist-briefing" },
      { label: "市场全景", to: "/market-panorama" },
      { label: "全球透视塔", to: "/global-radar" },
      { label: "热点板块", to: "/hot-sectors" },
      { label: "龙虎榜", to: "/longhu-bang" },
      { label: "研报中心", to: "/yanbao-hub" },
      { label: "通达信板块", to: "/tdx-blocks" },
      { label: "影子操盘", to: "/shadow-account" },
      { label: "模拟交易", to: "/paper-trading" },
      { label: "数据与市场说明", to: "/market-coverage" },
      { label: "使用偏好引导", to: "/onboarding" },
    ],
  },
  {
    label: "研究",
    icon: "🔬",
    items: [
      { label: "AI 投委会", to: "/ai-investment-committee" },
      { label: "AI 诊股", to: "/ai-analysis" },
      { label: "研究报告", to: "/ai-research-report" },
      { label: "研究闭环", to: "/research-pipeline" },
      { label: "量化实验室", to: "/quant-lab", personaFeature: "show_vectorized_backtest" },
      { label: "AI 对冲基金", to: "/ai-hedge-fund", navId: "ai_hedge_fund" },
      { label: "War Room", to: "/war-room", feature: "feature_war_room", personaFeature: "show_agent_topology" },
      { label: "语音简报", to: "/voice-briefing", navId: "voice_briefing" },
      { label: "Agent 中心", to: "/agent-center", navId: "agent_center", personaFeature: "show_agent_topology" },
      { label: "研究画布", to: "/research-canvas", navId: "research_canvas" },
    ],
  },
  {
    label: "策略",
    icon: "📈",
    items: [
      { label: "策略回测", to: "/backtest" },
      { label: "信号旗", to: "/signal-flag", personaFeature: "show_signal_flags" },
      { label: "智能选股", to: "/stock-selector" },
      { label: "模拟观察单", to: "/signal-observations", personaFeature: "show_observation_cards" },
      { label: "策略向导", to: "/strategy-wizard", personaFeature: "show_strategy_wizard" },
      { label: "Alpha Factory", to: "/alpha-factory", navId: "alpha_factory", personaFeature: "show_alpha_mining" },
      { label: "因子仓库", to: "/factor-repository", personaFeature: "show_factor_pipeline" },
      { label: "因子演化", to: "/factor-evolution", personaFeature: "show_factor_pipeline" },
      { label: "因子市场", to: "/marketplace", feature: "feature_alpha_marketplace", personaFeature: "show_alpha_mining" },
      { label: "参数优化", to: "/optimize", personaFeature: "show_vectorized_backtest" },
      { label: "数据湖健康", to: "/data-lake-health", navId: "data_lake_health" },
      { label: "归因面板", to: "/attribution-dashboard", personaFeature: "enable_brinson_attribution" },
    ],
  },
  {
    label: "我的",
    icon: "👤",
    items: [
      { label: "零售助理", to: "/retail-assistant" },
      { label: "个人中心", to: "/profile" },
      { label: "任务中心", to: "/task-center" },
      { label: "消息中心", to: "/message-center" },
      { label: "预警中心", to: "/alert-center" },
      { label: "协作空间", to: "/collaboration-workspace", navId: "collaboration_workspace" },
      { label: "等级·精品", to: "/user-tiers/boutique", navId: "user_tiers" },
      { label: "等级·投资", to: "/user-tiers/investment", navId: "user_tiers" },
      { label: "等级·基金", to: "/user-tiers/fund", navId: "user_tiers" },
      { label: "等级·机构", to: "/user-tiers/institution", navId: "user_tiers" },
      { label: "投资经理", to: "/investment-managers", navId: "investment_managers" },
      { label: "观测台", to: "/observability", navId: "observability" },
      { label: "集成中枢", to: "/integration-hub", navId: "integration_hub" },
      { label: "投资笔记", to: "/moments", navId: "moments" },
      { label: "简洁终端", to: "/zen-terminal", navId: "zen_terminal" },
    ],
  },
];

function DropdownGroup({
  group,
  features,
  personaMask,
  onClose,
}: {
  group: NavGroup;
  features: Record<string, boolean>;
  personaMask: Record<string, boolean>;
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
    (item) =>
      isNavItemVisible(features, item.navId, item.feature) &&
      isPersonaNavVisible(personaMask, item.personaFeature),
  );

  if (visibleItems.length === 0) {
    return null;
  }

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
            <NavLink
              key={item.label}
              to={item.to ?? item.href!}
              onClick={onClose}
              className={({ isActive }) =>
                `block px-4 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-[var(--quant-accent)]/12 text-[var(--quant-accent)]"
                    : "text-[var(--quant-fg)] hover:bg-[var(--quant-surface)] hover:text-[var(--quant-accent)]"
                }`
              }
            >
              {item.label}
            </NavLink>
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
  const { featureMask } = usePersona();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const openCmd = useCallback(() => setCmdOpen(true), []);
  useCommandPaletteHotkey(openCmd);

  async function onLogout() {
    await logoutSession();
    await refresh();
    navigate("/login", { replace: true });
  }

  const featureMap: Record<string, boolean> = features as Record<string, boolean>;
  const personaMask: Record<string, boolean> = featureMask;

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
                personaMask={personaMask}
                onClose={() => {}}
              />
            )).filter(Boolean)}
          </nav>

          {/* Right Side */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCmdOpen(true)}
              className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-[var(--quant-surface-border)] bg-[var(--quant-surface)]/60 px-2.5 py-1.5 text-xs text-[var(--quant-muted)] hover:border-[var(--quant-accent)]/40 hover:text-[var(--quant-fg)]"
              aria-label="打开命令面板"
            >
              <span>搜索</span>
              <kbd className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">⌘K</kbd>
            </button>
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
              className="hidden sm:inline-flex h-8 items-center rounded-lg px-2 text-xs font-medium text-[var(--quant-fg)] hover:bg-[var(--quant-surface)]"
              onClick={() => setAiOpen(true)}
              title="AI 助手"
            >
              AI
            </button>
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
            {NAV_GROUPS.map((group) => {
              const items = group.items.filter(
                (item) =>
                  isNavItemVisible(featureMap, item.navId, item.feature) &&
                  isPersonaNavVisible(personaMask, item.personaFeature),
              );
              if (items.length === 0) return null;
              return (
              <div key={group.label}>
                <div className="text-xs font-bold text-[var(--quant-muted)] uppercase tracking-wider mb-2">
                  {group.icon} {group.label}
                </div>
                <div className="grid grid-cols-2 gap-1">
                  {items.map((item) => (
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
            );
            })}
          </div>
        )}
      </header>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <main className="mx-auto max-w-[1400px] px-4 py-6">
        <KeepAliveOutlet />
      </main>

      {aiOpen ? (
        <Suspense fallback={null}>
          <AiAssistantDrawer open={aiOpen} onClose={() => setAiOpen(false)} />
        </Suspense>
      ) : null}
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
      {!aiOpen && (
        <button
          type="button"
          onClick={() => setAiOpen(true)}
          className="fixed bottom-4 right-4 z-50 rounded-full border border-[var(--quant-surface-border)] bg-[var(--quant-surface-strong)] px-4 py-2 text-sm font-medium text-[var(--quant-fg)] shadow-lg backdrop-blur hover:border-[var(--quant-accent)] hover:text-[var(--quant-accent)]"
          aria-label="打开 AI 助手"
        >
          AI 助手
        </button>
      )}

      {/* ── Back to Classic ──────────────────────────────────────── */}
      {enableBackToClassic && (
        <a
          href={backToClassicUrl || "/daily-workbench"}
          className="fixed bottom-4 left-4 text-xs text-[var(--quant-muted)] hover:text-[var(--quant-accent)] transition-colors z-50
                     px-3 py-1.5 rounded-full bg-[var(--quant-surface-strong)] border border-[var(--quant-surface-border)] backdrop-blur"
        >
          ← 回到经典版
        </a>
      )}
    </div>
  );
}
