"""Phase 4 tests: decision feedback and health-aware routing."""

from __future__ import annotations

from app.modules.ai_agent.services.ai.decision_feedback_service import DecisionFeedbackService
from app.core.middleware.degraded_context import clear_degraded_state, mark_system_degraded
from app.core.middleware.health_aware import append_health_notice, build_degraded_user_message
from app.domain.dto.decision_context_dto import DecisionContextDTO


def test_build_degraded_user_message():
    mark_system_degraded("tencent_quotes")
    msg = build_degraded_user_message()
    assert "降级" in msg
    clear_degraded_state()


def test_append_health_notice_adds_system_notice():
    mark_system_degraded("openbb")
    dto = DecisionContextDTO(
        decision_id="dec_test",
        subject="CN:600519",
        reasoning_trace=["step1"],
    )
    updated = append_health_notice(dto)
    assert updated.input_snapshot.get("system_notice")
    assert any("降级" in line for line in updated.reasoning_trace)
    clear_degraded_state()


def test_decision_feedback_service_persists_and_forwards():
    recorded: list[dict] = []

    class _Knowledge:
        def record_interaction(self, user_id, **kwargs):
            recorded.append({"user_id": user_id, **kwargs})

    svc = DecisionFeedbackService(user_knowledge_service=_Knowledge())
    dto = svc.submit(user_id=1, decision_id="dec_abc", rating="up", comment="good")
    assert dto.rating == "up"
    assert recorded and recorded[0]["outcome"] == "positive"
