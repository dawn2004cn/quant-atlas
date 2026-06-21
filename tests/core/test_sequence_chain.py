from __future__ import annotations

from pathlib import Path

from app.agents.research.debate_bus import clear_debate_buffer, publish_debate_round
from app.application.services.orchestration.correction_intent_service import (
    CorrectionIntentService,
)
from app.application.services.orchestration.debate_arbiter_service import DebateArbiterService
from app.application.services.orchestration.sequence_chain_service import SequenceChainService
from app.core.event_bus import (
    EventBus,
    TradeExecutedEvent,
    emit_trade_executed,
    get_event_bus,
)
from app.infrastructure.replay.sequence_chain_store import SequenceChainStore


def _seed_debate(symbol: str = "600519") -> None:
    for i, role in enumerate(["bull", "bear", "bull"], start=1):
        publish_debate_round(
            ticker=symbol,
            agent_role=role,
            chunk="业绩与估值讨论材料。" * 6,
            round_num=i,
        )


def test_sequence_chain_links_debate_consensus_trade(tmp_path: Path) -> None:
    EventBus().clear()
    clear_debate_buffer()
    store = SequenceChainStore(tmp_path)
    chain_svc = SequenceChainService(store=store)
    chain_svc.start()
    correction = CorrectionIntentService(trade_plan_service=None)
    arbiter = DebateArbiterService(
        correction_intent_service=correction,
        sequence_chain_service=chain_svc,
    )

    _seed_debate()
    result = arbiter.synthesize("600519", "CN")
    assert result.get("ok") is True
    provenance_id = result["provenance_id"]
    assert provenance_id

    emit_trade_executed(
        user_id="u1",
        symbol="sh600519",
        action="buy",
        quantity=100,
        price=10.5,
        provenance_id=provenance_id,
    )

    chain = chain_svc.get_chain(provenance_id)
    assert chain is not None
    event_types = [s.event_type for s in chain.steps]
    assert "DebateRoundEvent" in event_types
    assert "ArbiterConsensusEvent" in event_types
    assert "TradeExecutedEvent" in event_types


def test_emit_trade_requires_provenance() -> None:
    try:
        emit_trade_executed(
            user_id="u1",
            symbol="sh600519",
            action="buy",
            quantity=1,
            price=1.0,
            provenance_id="",
        )
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_correction_intent_on_verdict_shift() -> None:
    svc = CorrectionIntentService()
    first = svc.maybe_emit_correction(
        provenance_id="prov-a",
        symbol="600519",
        market="CN",
        verdict="bullish",
        confidence=0.8,
    )
    assert first is None  # no prior verdict
    second = svc.maybe_emit_correction(
        provenance_id="prov-b",
        symbol="600519",
        market="CN",
        verdict="bearish",
        confidence=0.85,
    )
    assert second is not None
    assert second.change_type == "regime_shift"
    assert second.parameter_patch.get("risk_per_trade_pct") == 0.5
