from __future__ import annotations

from app.agents.research.debate_bus import clear_debate_buffer, publish_debate_round
from app.modules.ai_agent.services.evidence_replay_service import EvidenceReplayService
from app.core.event_bus import EventBus


def test_build_timeline_includes_debate_rounds() -> None:
    EventBus().clear()
    clear_debate_buffer()
    publish_debate_round(
        ticker="600519",
        agent_role="bull",
        chunk="业绩稳健，估值合理，趋势向上。" * 5,
        round_num=1,
    )
    svc = EvidenceReplayService()
    timeline = svc.build_timeline("600519", market="CN", minutes_back=120)
    assert timeline["node_count"] >= 1
    assert any(n.get("event_type") == "DebateRoundEvent" for n in timeline["nodes"])
