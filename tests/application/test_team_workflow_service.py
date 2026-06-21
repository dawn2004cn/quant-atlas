from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.modules.collaboration.services.team_workflow_service import TeamWorkflowService
from app.infrastructure.collaboration.team_workflow_store import TeamWorkflowStore


def _svc(tmp_path: Path) -> TeamWorkflowService:
    repo = MagicMock()
    repo.list_user_teams.return_value = [{"team_id": 1, "role": "owner"}]
    blackboard = MagicMock()
    blackboard.submit_note.return_value = {"ok": True, "entry": {"id": 1}}
    blackboard.synthesize_consensus.return_value = {
        "ok": True,
        "verdict": "bullish",
        "confidence": 0.7,
    }
    research = MagicMock()
    research.publish_research.return_value = {"ok": True, "post_id": 9}
    topology = MagicMock()
    topology.get_preset.return_value = {"ok": True, "topology": {"name": "测试拓扑"}}
    return TeamWorkflowService(
        collaboration_repository=repo,
        store=TeamWorkflowStore(base_dir=tmp_path),
        team_blackboard_service=blackboard,
        team_research_channel_service=research,
        swarm_topology_service=topology,
        swarm_arbiter_service=None,
    )


def test_fast_agent_loop_completes_without_pause(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    out = svc.start_run(
        10,
        1,
        "fast_agent_loop",
        context={"symbol": "sz000001", "market": "CN", "topic": "test"},
        author_name="Lead",
    )
    assert out["ok"] is True
    run = out["run"]
    assert run["status"] == "completed"
    assert len(run.get("steps") or []) >= 3


def test_lead_pipeline_pauses_at_human_task(tmp_path: Path) -> None:
    svc = _svc(tmp_path)
    out = svc.start_run(
        10,
        1,
        "lead_review_pipeline",
        context={"symbol": "sz000001"},
    )
    assert out["ok"] is True
    run = out["run"]
    assert run["status"] == "paused"
    assert run.get("pause_reason") == "human_task"

    advanced = svc.advance_run(10, 1, run["run_id"], action="complete", note="证据已提交")
    assert advanced["ok"] is True
    assert advanced["run"]["status"] in {"paused", "running", "completed"}


def test_save_workflow_requires_lead(tmp_path: Path) -> None:
    repo = MagicMock()
    repo.list_user_teams.return_value = [{"team_id": 1, "role": "member"}]
    svc = TeamWorkflowService(collaboration_repository=repo, store=TeamWorkflowStore(base_dir=tmp_path))
    out = svc.save_team_workflow(5, 1, {"id": "custom-wf", "name": "Test", "nodes": [], "edges": []})
    assert out["ok"] is False
    assert out["error"] == "lead_required"
