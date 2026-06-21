from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.collaboration.services.team_blackboard_service import TeamBlackboardService


def test_submit_note_pushes_socketio() -> None:
    repo = MagicMock()
    repo.add_blackboard_entry.return_value = {
        "id": 1,
        "team_id": 9,
        "evidence_key": "stance",
        "evidence_value": "bullish",
    }
    realtime = MagicMock()
    realtime.push_team_blackboard_entry.return_value = {
        "ok": True,
        "room": "team_blackboard:9",
        "receivers": 2,
    }
    svc = TeamBlackboardService(
        collaboration_repository=repo,
        realtime_gateway_service=realtime,
    )
    out = svc.submit_note(
        team_id=9,
        user_id=1,
        evidence_key="stance",
        evidence_value="bullish",
    )
    assert out["ok"] is True
    realtime.push_team_blackboard_entry.assert_called_once_with(9, out["entry"])
    assert out["realtime"]["receivers"] == 2
