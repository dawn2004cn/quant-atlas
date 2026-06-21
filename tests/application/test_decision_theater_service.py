from __future__ import annotations

from app.modules.system.services.ui.decision_theater_service import DecisionTheaterService


def test_decision_theater_builds_scene() -> None:
    svc = DecisionTheaterService(enable_qlib=False, enable_rd_agent=False)
    out = svc.build_theater(user_id=1)
    assert out["ok"] is True
    scene = out["scene"]
    assert len(scene["nodes"]) >= 6
    assert scene["schema_version"] == "v2_theater"
    assert out["confidence"] > 0.5
    assert "pipeline_summary" in out
