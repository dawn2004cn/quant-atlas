"""SPA shell contracts: local navigation, keep-alive, login path, strip restored."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"


def test_core_workflow_strip_is_spa_links() -> None:
    text = (FE / "components" / "CoreWorkflowStrip.tsx").read_text(encoding="utf-8")
    assert len(text.strip()) > 200
    assert "react-router-dom" in text
    assert "export function CoreWorkflowStrip" in text
    assert "export function PageQuickNav" in text
    assert "export const QUICK_NAV_PRESETS" in text
    assert "export function CoreNextSteps" in text
    assert "<Link" in text
    assert "window.location" not in text


def test_layout_keeps_shell_and_partial_refresh() -> None:
    text = (FE / "components" / "Layout.tsx").read_text(encoding="utf-8")
    assert "KeepAliveOutlet" in text
    assert 'to: "/"' in text or 'to: "/"' in text
    assert "window.location.href" not in text


def test_login_navigates_inside_spa_basename() -> None:
    text = (FE / "pages" / "Login.tsx").read_text(encoding="utf-8")
    assert "toSpaPath" in text
    assert 'from ?? "/app"' not in text


def test_swr_provider_keeps_previous_page_data() -> None:
    text = (FE / "main.tsx").read_text(encoding="utf-8")
    assert "SWRConfig" in text
    assert "keepPreviousData" in text
    assert "revalidateOnFocus" in text


def test_portfolio_page_falls_back_when_live_positions_unusable() -> None:
    text = (FE / "pages" / "Portfolio.tsx").read_text(encoding="utf-8")
    assert "liveUsable" in text
    assert "DEMO_PORTFOLIO" in text
    assert "DemoBanner" in text


def test_dashboard_shows_demo_while_workbench_loads() -> None:
    text = (FE / "pages" / "Dashboard.tsx").read_text(encoding="utf-8")
    assert "DEMO_WORKBENCH" in text
    assert "awaitingLive" in text
    assert "演示占位" in text


def test_command_palette_wired_in_layout() -> None:
    layout = (FE / "components" / "Layout.tsx").read_text(encoding="utf-8")
    palette = (FE / "components" / "CommandPalette.tsx").read_text(encoding="utf-8")
    assert "CommandPalette" in layout
    assert "useCommandPaletteHotkey" in layout
    assert "⌘K" in palette or "Cmd" in palette or "metaKey" in palette
    assert "/stocks/search" in palette
    assert "/watchlist-briefing" in palette


def test_openstock_inspired_pages_registered() -> None:
    app = (FE / "App.tsx").read_text(encoding="utf-8")
    assert 'path="watchlist-briefing"' in app
    assert 'path="market-coverage"' in app
    assert 'path="onboarding"' in app
    assert 'path="paper-trading"' in app
    assert "OnboardingGate" in app
    detail = (FE / "pages" / "StockDetail.tsx").read_text(encoding="utf-8")
    assert "近 120 日走势" in detail
    assert "AI 诊股" in detail
    # Chart hero before AI insight panel render
    assert detail.index("近 120 日走势") < detail.index("<AiInsightPanel")


def test_onboarding_persona_flow_wired() -> None:
    onboard = (FE / "pages" / "Onboarding.tsx").read_text(encoding="utf-8")
    assert "/user/persona" in onboard
    assert "markOnboardingCompleted" in onboard
    login = (FE / "pages" / "Login.tsx").read_text(encoding="utf-8")
    assert "hasCompletedOnboarding" in login
    brief = (FE / "pages" / "WatchlistBriefing.tsx").read_text(encoding="utf-8")
    assert "/watchlist/experience" in brief
    assert "notesFromWatchlist" in brief


def test_paper_trading_page_and_profile_persona() -> None:
    paper = (FE / "pages" / "PaperTrading.tsx").read_text(encoding="utf-8")
    assert "applyPaperOrder" in paper
    assert "模拟买入" in paper
    book = (FE / "lib" / "paperBook.ts").read_text(encoding="utf-8")
    assert "qa_paper_book_v1" in book
    profile = (FE / "pages" / "Profile.tsx").read_text(encoding="utf-8")
    assert "/user/persona" in profile
    assert "daily_briefing" in profile
    assert "resetOnboardingFlag" in profile
    palette = (FE / "components" / "CommandPalette.tsx").read_text(encoding="utf-8")
    assert "/paper-trading" in palette
