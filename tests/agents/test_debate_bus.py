from __future__ import annotations

from app.agents.research.debate_bus import (
    clear_debate_buffer,
    estimate_debate_confidence,
    get_recent_debate_rounds,
    publish_debate_round,
)
from app.core.event_bus import DebateRoundEvent, EventBus


def test_publish_debate_round_buffers_and_emits() -> None:
    bus = EventBus()
    bus.clear()
    clear_debate_buffer()
    received: list[str] = []
    bus.subscribe(DebateRoundEvent, lambda _e: received.append("hit"))

    publish_debate_round(
        ticker="600519",
        agent_role="bull",
        chunk="宏观向好，盈利增速稳健，技术面突破均线。" * 5,
        round_num=1,
    )
    assert received == ["hit"]
    rounds = get_recent_debate_rounds("600519", "CN")
    assert len(rounds) == 1
    assert rounds[0]["agent_role"] == "bull"
    assert rounds[0]["stance"] == "bullish"


def test_estimate_debate_confidence_penalizes_uncertainty() -> None:
    high = estimate_debate_confidence("业绩超预期，量价齐升，资金持续流入。" * 8)
    low = estimate_debate_confidence("不确定，数据不足。")
    assert high > low
