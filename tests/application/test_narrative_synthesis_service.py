from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.strategy.services.analytics.narrative_synthesis_service import (
    NarrativeSynthesisService,
)
from app.domain.sequence_chain import SequenceChain, SequenceStep


def test_template_narrative_uses_success_pattern() -> None:
    knowledge_svc = MagicMock()
    knowledge_svc.build_context_enrichment.return_value = {
        "top_symbols": [{"id": "sz000001", "score": 5}],
        "related_decision_patterns": [
            {
                "outcome": "win",
                "symbols": ["sz000338"],
                "sectors": ["auto"],
                "factors": ["reversal"],
            }
        ],
    }
    knowledge_svc.get_profile.return_value = {
        "decision_patterns": [
            {"outcome": "win", "symbols": ["sz000338"], "sectors": ["auto"]}
        ],
    }
    knowledge_svc.analyze_topology.return_value = {"alerts": []}

    decision_svc = MagicMock()
    decision_svc.build_context.return_value = {
        "dto_directives": {"narrative_level": "normal"},
        "decision_history": {"frequent_symbols": ["sz000338"]},
        "risk_context": {"risk_level": "balanced"},
    }

    svc = NarrativeSynthesisService(
        user_knowledge_service=knowledge_svc,
        user_decision_context_service=decision_svc,
    )
    briefing = {
        "recommendations": [
            {
                "symbol": "sz000625",
                "name": "长安汽车",
                "reasons": ["RSI超卖，反弹潜力大"],
            }
        ],
        "market_environment": {
            "regime": "sideways",
            "regime_description": "震荡市，适合高抛低吸",
            "recommended_strategies": ["反转投资"],
        },
        "summary": "今日精选1只",
    }
    out = svc.synthesize_daily_briefing(user_id=1, briefing=briefing)
    assert out["mode"] == "template"
    assert "sz000001" in out["opening"] or "震荡" in out["opening"]
    assert out["recommendation_narratives"][0]["symbol"] == "sz000625"
    assert len(out["recommendation_narratives"][0]["narrative"]) > 10


def test_template_narrative_uses_sequence_chain_evidence() -> None:
    chain_svc = MagicMock()
    chain = SequenceChain(
        provenance_id="prov-test-1",
        symbol="sz000625",
        market="CN",
        steps=[
            SequenceStep(
                step_id="s1",
                event_type="DebateRoundEvent",
                label="technical_analyst · bullish",
                payload={
                    "agent_role": "technical_analyst",
                    "stance": "bullish",
                    "confidence": 0.82,
                    "evidence_summary": "RSI 超卖且量能放大",
                },
            ),
            SequenceStep(
                step_id="s2",
                event_type="ArbiterConsensusEvent",
                label="verdict=buy",
                payload={"verdict": "buy", "confidence": 0.75},
            ),
        ],
    )
    chain_svc.list_chains.return_value = [chain]

    svc = NarrativeSynthesisService(sequence_chain_service=chain_svc)
    briefing = {
        "recommendations": [
            {"symbol": "sz000625", "name": "长安汽车", "reasons": ["RSI超卖"]},
        ],
        "market_environment": {"regime": "sideways", "regime_description": "震荡市"},
        "summary": "今日精选1只",
    }
    out = svc.synthesize_daily_briefing(user_id=1, briefing=briefing)
    assert out["mode"] == "template"
    assert len(out.get("evidence_nodes") or []) >= 2
    narrative = out["recommendation_narratives"][0]["narrative"]
    assert "辩论证据" in narrative or "仲裁结论" in narrative
    assert any("仲裁" in h for h in (out.get("causal_hooks") or []))


def test_causal_report_template_from_sequence_chain() -> None:
    from app.domain.sequence_chain import SequenceChain, SequenceStep

    chain_svc = MagicMock()
    chain = SequenceChain(
        provenance_id="prov-causal-1",
        symbol="sz000625",
        market="CN",
        steps=[
            SequenceStep(
                step_id="s1",
                event_type="DebateRoundEvent",
                label="bull · bullish",
                payload={"evidence_summary": "量价齐升", "stance": "bullish"},
            ),
            SequenceStep(
                step_id="s2",
                event_type="ArbiterConsensusEvent",
                label="verdict=buy",
                payload={"verdict": "buy"},
            ),
        ],
    )
    chain_svc.list_chains.return_value = [chain]

    svc = NarrativeSynthesisService(sequence_chain_service=chain_svc)
    out = svc.synthesize_causal_report(
        user_id=1,
        symbol="sz000625",
        briefing={"market_environment": {"regime_description": "震荡市"}},
    )
    assert out["mode"] == "template"
    assert "辩论" in out["report_markdown"] or "仲裁" in out["report_markdown"]
    assert out["chain_steps"] >= 2


def test_parse_json_block_extracts_llm_payload() -> None:
    text = '说明\n```json\n{"opening":"你好","market_narrative":"市况平稳"}\n```'
    parsed = NarrativeSynthesisService._parse_json_block(text)
    assert parsed is not None
    assert parsed.get("opening") == "你好"
