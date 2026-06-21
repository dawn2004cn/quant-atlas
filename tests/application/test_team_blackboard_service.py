from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.collaboration.services.team_blackboard_service import TeamBlackboardService


def test_submit_note_persists_entry() -> None:
    repo = MagicMock()
    repo.add_blackboard_entry.return_value = {
        "id": 1,
        "team_id": 3,
        "evidence_key": "macd",
        "evidence_value": "bullish",
    }
    svc = TeamBlackboardService(collaboration_repository=repo)
    out = svc.submit_note(
        team_id=3,
        user_id=9,
        evidence_key="macd",
        evidence_value="bullish",
        symbol="sz000001",
    )
    assert out["ok"] is True
    assert out["entry"]["id"] == 1
    repo.add_blackboard_entry.assert_called_once()


def test_synthesize_consensus_bullish() -> None:
    repo = MagicMock()
    repo.list_blackboard_entries.return_value = [
        {"evidence_key": "trend", "evidence_value": "bullish breakout", "strength": "strong"},
        {"evidence_key": "volume", "evidence_value": "buy surge", "strength": "moderate"},
    ]
    svc = TeamBlackboardService(collaboration_repository=repo)
    out = svc.synthesize_consensus(2, symbol="sz000001")
    assert out["ok"] is True
    assert out["verdict"] == "bullish"
    assert out["entries_used"] == 2


def test_synthesize_consensus_empty() -> None:
    repo = MagicMock()
    repo.list_blackboard_entries.return_value = []
    svc = TeamBlackboardService(collaboration_repository=repo)
    out = svc.synthesize_consensus(2)
    assert out["ok"] is False
    assert out["status"] == "no_entries"
