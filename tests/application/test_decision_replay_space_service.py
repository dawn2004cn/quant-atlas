from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.system.services.ui.decision_replay_space_service import DecisionReplaySpaceService


def test_build_space_from_behavior_topology() -> None:
    knowledge = MagicMock()
    knowledge.get_profile.return_value = {
        "user_id": "1",
        "sector_attention": {"科技": 3, "消费": 1},
        "symbol_attention": {"sz000001": 5},
        "decision_patterns": [
            {"outcome": "win", "symbols": ["sz000001"], "sectors": ["科技"]},
            {"outcome": "loss", "symbols": ["sz000002"], "sectors": ["消费"]},
        ],
        "interaction_events": [
            {
                "symbols": ["sz000001"],
                "action": "view",
                "recorded_at": "2026-06-01T00:00:00Z",
            }
        ],
    }
    knowledge.analyze_topology.return_value = {
        "fatigue_level": "low",
        "alerts": [],
        "cognitive_biases": [{"type": "confirmation_bias", "severity": "warning"}],
        "topology": {
            "nodes": [
                {"id": "user:1", "type": "user", "label": "投资者"},
                {"id": "sector:科技", "type": "sector", "label": "科技"},
                {"id": "symbol:sz000001", "type": "symbol", "label": "sz000001"},
            ],
            "edges": [
                {"from": "user:1", "to": "sector:科技", "relation": "researched"},
                {"from": "user:1", "to": "symbol:sz000001", "relation": "view"},
            ],
        },
    }
    svc = DecisionReplaySpaceService(user_knowledge_service=knowledge)
    out = svc.build_space(1)
    assert out["ok"] is True
    scene = out["scene"]
    assert len(scene["nodes"]) >= 5
    assert any(n["type"] == "user" for n in scene["nodes"])
    assert any(n["type"] == "decision_win" for n in scene["nodes"])
    assert any(n["type"] == "bias" for n in scene["nodes"])


def test_build_space_with_symbol_timeline() -> None:
    knowledge = MagicMock()
    knowledge.get_profile.return_value = {"user_id": "2", "decision_patterns": [], "interaction_events": []}
    knowledge.analyze_topology.return_value = {
        "fatigue_level": "medium",
        "alerts": [],
        "cognitive_biases": [],
        "topology": {"nodes": [{"id": "user:2", "type": "user", "label": "投资者"}], "edges": []},
    }
    svc = DecisionReplaySpaceService(user_knowledge_service=knowledge, ai_evidence_service=MagicMock())
    out = svc.build_space(2, symbol="SZ000001", minutes_back=60)
    assert out["ok"] is True
    assert out["timeline_summary"]["symbol"] == "SZ000001"
