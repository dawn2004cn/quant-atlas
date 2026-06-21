import { Link, Outlet, useNavigate } from "react-router-dom";
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

export function Layout({ enableBackToClassic, backToClassicUrl }: LayoutProps) {
  const { t } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const { isAuthenticated, loading, mode, username, refresh } = useAuth();
  const { features } = usePlatformFeatures();
  const navigate = useNavigate();

  async function onLogout() {
    await logoutSession();
    await refresh();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="text-lg font-semibold text-brand">
            Quant Atlas
          </Link>
          <nav className="flex flex-wrap items-center gap-4 text-sm">
            <Link to="/" className="hover:text-brand">{t("nav.workspace", "操盘台")}</Link>
            <Link to="/backtest" className="hover:text-brand">{t("nav.backtest", "回测")}</Link>
            <Link to="/runs" className="hover:text-brand">{t("nav.runs", "历史")}</Link>
            <Link to="/experiments" className="hover:text-brand">{t("nav.experiments", "实验")}</Link>
            <Link to="/alpha-factory" className="hover:text-brand">{t("nav.alpha_factory", "因子工厂")}</Link>
            <Link to="/signal-flag" className="hover:text-brand">{t("nav.signal_flag", "信号旗")}</Link>
            {features.feature_alpha_marketplace ? (
              <Link to="/marketplace" className="hover:text-brand">
                因子市场
              </Link>
            ) : null}
            <a href="/daily-workbench" className="hover:text-brand">{t("nav.classic", "经典版")}</a>
            {loading ? (
              <span className="text-slate-400">…</span>
            ) : isAuthenticated ? (
              <span className="flex items-center gap-2 text-slate-500">
                <span>
                  {username ?? (mode === "session" ? t("logged_in", "已登录") : t("user", "用户"))}
                </span>
                <button
                  type="button"
                  className="btn btn-ghost btn-xs"
                  onClick={() => void onLogout()}
                >
                  {t("logout", "退出")}
                </button>
              </span>
            ) : (
              <Link to="/login" className="btn btn-primary btn-xs">
{t("login", "登录")}
              </Link>
            )}
            <LanguageSwitcher />
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={toggleTheme}
              aria-label={t("theme_toggle", "切换主题")}
            >
              {theme === "light" ? t("dark_mode", "暗色") : t("light_mode", "亮色")}
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
      {enableBackToClassic && (
        <a href={backToClassicUrl || "/"} className="fixed bottom-4 right-4 text-xs text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition-colors">
          ← 回到经典版
        </a>
      )}
    </div>
  );
}
