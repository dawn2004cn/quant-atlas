from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.agents.research.debate_bus import clear_debate_buffer, publish_debate_round
from app.application.services.orchestration.debate_arbiter_service import DebateArbiterService
from app.core.event_bus import EventBus


def _seed() -> None:
    for i, role in enumerate(["bull", "bear", "bull"], start=1):
        publish_debate_round(
            ticker="600519",
            agent_role=role,
            chunk="业绩与趋势分析材料。" * 8,
            round_num=i,
        )


def test_llm_mode_falls_back_without_llm() -> None:
    EventBus().clear()
    clear_debate_buffer()
    _seed()
    svc = DebateArbiterService()
    with patch("app.core.llm_config.get_llm", side_effect=RuntimeError("no llm")):
        result = svc.synthesize("600519", "CN", use_llm=True)
    assert result.get("mode") == "heuristic"
    assert result.get("ok") is True


def test_parse_llm_verdict_json() -> None:
    text = '分析如下 {"verdict": "bearish", "confidence": 0.72, "rationale": "风险偏高"}'
    parsed = DebateArbiterService._parse_llm_verdict(text)
    assert parsed is not None
    assert parsed["verdict"] == "bearish"
