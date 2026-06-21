"""Retail assistant hub service tests."""

from __future__ import annotations

from app.modules.user.services.user.retail_assistant_hub_service import (
    RetailAssistantHubService,
)


def test_quick_actions_returns_links():
    actions = RetailAssistantHubService().quick_actions()["actions"]
    hrefs = {a["href"] for a in actions}
    assert "/daily-workbench" in hrefs
    assert "/integration-hub" in hrefs


def test_overview_modules_include_infrastructure():
    modules = RetailAssistantHubService().overview()["modules"]
    ids = {m["id"] for m in modules}
    assert "daily_top_picks" in ids
    assert "infrastructure" in ids


def test_refactor_status_has_pillars_and_probes():
    svc = RetailAssistantHubService()
    data = svc.refactor_status()

    assert data["available"] is True
    assert data["source_doc"] == "docs/refacter.md"
    assert len(data["pillars"]) == 4
    assert "websocket" in data["probes"]
    assert "timeseries" in data["probes"]
    assert "beat" in data["probes"]["timeseries"]
    infra_items = data["pillars"][2]["items"]
    names = [it["name"] for it in infra_items]
    assert any("WebSocket" in n for n in names)
    assert any("QuestDB" in n for n in names)
