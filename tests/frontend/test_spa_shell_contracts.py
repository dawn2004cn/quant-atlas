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
