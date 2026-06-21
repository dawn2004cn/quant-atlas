from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.user.services.user.behavior_topology_guardian import (
    enrich_psychology_with_topology,
)


def test_enrich_merges_topology_alerts() -> None:
    knowledge = MagicMock()
    knowledge.analyze_topology.return_value = {
        "fatigue_level": "high",
        "alerts": [{"code": "research_fatigue", "level": "warning", "message": "休息"}],
        "cognitive_biases": [
            {"type": "confirmation_bias", "severity": "warning", "suggestion": "看风险"},
        ],
    }
    out = enrich_psychology_with_topology(
        {"alerts": []},
        user_knowledge_service=knowledge,
        user_id=1,
    )
    assert len(out["alerts"]) >= 2
    assert out.get("risk_level") == "elevated"
    assert "behavior_topology" in out
