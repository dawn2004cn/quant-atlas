from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.modules.ai_agent.services.command_plan_service import CommandPlanService
from app.modules.system.services.system.realtime_gateway_service import RealtimeGatewayService
from app.modules.user.services.user.user_knowledge_service import UserKnowledgeService
from app.core.event_bus import ServiceStartedEvent, get_event_bus
from app.core.modules import module_manifest


def test_microkernel_manifest_exposes_journey_modules():
    payload = module_manifest()

    names = [item["name"] for item in payload["modules"]]
    assert payload["schema_version"] == "v1"
    assert "discovery" in names
    assert "research" in names
    assert "execution" in names


def test_event_bus_records_recent_events_for_replay():
    bus = get_event_bus()
    bus.clear()

    bus.publish(ServiceStartedEvent(service_name="demo_service", scope="singleton"))
    items = RealtimeGatewayService().recent_events(limit=5)["items"]

    assert items[0]["event"] == "ServiceStartedEvent"
    assert items[0]["data"]["service_name"] == "demo_service"


def test_user_knowledge_context_enrichment(tmp_path: Path):
    svc = UserKnowledgeService(store_path=tmp_path / "knowledge.json")

    svc.record_interaction(
        "u1",
        symbols=["600519"],
        sectors=["白酒"],
        factors=["低波动", "ROE"],
        outcome="accepted",
        evidence_refs=["eg_1"],
    )
    enrichment = svc.build_context_enrichment("u1", symbol="600519", sector="白酒")

    assert enrichment["top_symbols"][0]["id"] == "600519"
    assert enrichment["related_decision_patterns"][0]["outcome"] == "accepted"
    assert enrichment["prompt_hints"]


def test_command_plan_parses_compound_instruction():
    command = "如果 600519 跌破 20日线且 RSI 小于 30，请通过邮件提醒我，并生成一份技术面分析报告"

    plan = CommandPlanService().build_plan(command)

    assert plan["intent"] == "conditional_automation"
    assert plan["symbol"] == "600519"
    assert any(item["type"] == "moving_average" for item in plan["triggers"])
    assert any(item["type"] == "generate_report" for item in plan["actions"])


def test_realtime_gateway_manifest_has_core_channels():
    payload = RealtimeGatewayService().build_manifest(SimpleNamespace())

    assert payload["schema_version"] == "v1"
    assert [item["id"] for item in payload["channels"]] == [
        "market",
        "agent",
        "tasks",
        "system",
    ]
