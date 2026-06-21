from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.user.services.user.behavior_topology import analyze_behavior_topology


def test_detects_confirmation_bias() -> None:
    events = [
        {"stance": "bullish", "symbols": ["600519"], "recorded_at": "2026-06-06T10:00:00Z", "action": "view"}
        for _ in range(8)
    ]
    profile = {
        "user_id": "1",
        "sector_attention": {},
        "symbol_attention": {},
        "factor_attention": {},
        "decision_patterns": [],
        "interaction_events": events,
    }
    topo = analyze_behavior_topology(profile)
    bias_types = {b["type"] for b in topo["cognitive_biases"]}
    assert "confirmation_bias" in bias_types


def test_high_fatigue_alert() -> None:
    now = datetime.now(timezone.utc)
    events = [
        {
            "stance": "view",
            "symbols": ["600519"],
            "recorded_at": (now - timedelta(minutes=i)).isoformat().replace("+00:00", "Z"),
            "action": "view",
        }
        for i in range(16)
    ]
    profile = {"user_id": "1", "interaction_events": events, "decision_patterns": []}
    topo = analyze_behavior_topology(profile)
    assert topo["fatigue_level"] == "high"
    assert any(a["code"] == "research_fatigue" for a in topo["alerts"])
