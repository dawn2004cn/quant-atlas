"""Tests for decision trace and context-module wiring."""

from __future__ import annotations

from app.modules.system.services.ui.decision_trace_service import DecisionTraceService
from app.bootstrap_components.module_wiring import wire_context_modules
from app.domain.dto.decision_context_dto import DecisionContextDTO


class _Services:
    collaboration_repository = None
    collaboration_service = None
    team_blackboard_service = None
    team_research_channel_service = None


def test_decision_trace_service_record_and_get():
    svc = DecisionTraceService(max_entries=10)
    dto = DecisionContextDTO(decision_id="decision_abc123", subject="CN:600519")
    svc.record(dto)
    loaded = svc.get("decision_abc123")
    assert loaded is not None
    assert loaded.subject == "CN:600519"
    payload = svc.trace_payload("decision_abc123")
    assert payload is not None
    assert payload["decision_id"] == "decision_abc123"


def test_wire_context_modules_skips_when_collaboration_disabled():
    services = _Services()
    wired = wire_context_modules(
        services,
        session_factory=None,
        config={"ENABLE_COLLABORATION": False},
    )
    assert wired == []
    assert services.collaboration_service is None
