"""Tests for navigation menu visibility gates."""

from __future__ import annotations

import pytest

from app.core.nav_menu import api_nav_flags, jinja_nav_flags, nav_visible


@pytest.mark.parametrize(
    "item_id",
    [
        "spa_shell",
        "ai_hedge_fund",
        "agent_center",
        "voice_briefing",
        "research_canvas",
        "alpha_factory",
        "data_lake_health",
        "user_tiers",
        "zen_terminal",
        "integration_hub",
        "observability",
        "moments",
        "collaboration_workspace",
        "investment_managers",
    ],
)
def test_experimental_nav_hidden_by_default(item_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NAV_SHOW_EXPERIMENTAL", raising=False)
    monkeypatch.delenv(f"NAV_SHOW_{item_id.upper()}", raising=False)
    assert nav_visible(item_id) is False


def test_nav_show_experimental_reveals_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NAV_SHOW_EXPERIMENTAL", "1")
    for key in api_nav_flags():
        assert api_nav_flags()[key] is True


def test_nav_show_single_item(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NAV_SHOW_EXPERIMENTAL", raising=False)
    monkeypatch.setenv("NAV_SHOW_MOMENTS", "1")
    assert nav_visible("moments") is True
    assert nav_visible("observability") is False


def test_core_nav_always_visible() -> None:
    assert nav_visible("unknown_item") is True


def test_jinja_nav_flags_prefix() -> None:
    flags = jinja_nav_flags()
    assert "nav_moments" in flags
    assert flags["nav_moments"] is False
