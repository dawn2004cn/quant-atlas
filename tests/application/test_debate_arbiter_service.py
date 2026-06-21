from __future__ import annotations

from app.agents.research.debate_bus import publish_debate_round
from app.application.services.orchestration.debate_arbiter_service import DebateArbiterService
from app.core.event_bus import EventBus


def _seed_rounds(symbol: str = "600519") -> None:
    publish_debate_round(
        ticker=symbol,
        agent_role="bull",
        chunk="盈利改善，估值合理，趋势向上。" * 6,
        round_num=1,
    )
    publish_debate_round(
        ticker=symbol,
        agent_role="bear",
        chunk="宏观承压，估值偏高需谨慎。" * 4,
        round_num=2,
    )
    publish_debate_round(
        ticker=symbol,
        agent_role="bull",
        chunk="订单饱满，回购彰显信心。" * 6,
        round_num=3,
    )


def test_synthesize_bullish_consensus() -> None:
    EventBus().clear()
    _seed_rounds()
    svc = DebateArbiterService()
    result = svc.synthesize("600519", "CN", min_rounds=2)
    assert result["ok"] is True
    assert result["verdict"] in ("bullish", "neutral", "bearish")
    assert result["rounds_used"] >= 2
