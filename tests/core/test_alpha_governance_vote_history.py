from __future__ import annotations

from pathlib import Path

from app.core.mesh.alpha_governance import AlphaGovernanceDAO


def test_proposal_persists_and_reloads(tmp_path: Path) -> None:
    history_path = tmp_path / "alpha_vote_history.jsonl"
    proposal_path = tmp_path / "alpha_proposals.json"
    dao = AlphaGovernanceDAO(
        vote_history_path=history_path,
        proposal_store_path=proposal_path,
    )
    proposal_id = dao.submit_proposal(
        strategy_id="alpha_rev",
        manager_id="team-a",
        expression="rank(close)",
        zk_proof="deadbeef",
        metrics={"sharpe": 0.9},
    )

    assert proposal_path.is_file()

    reloaded = AlphaGovernanceDAO(
        vote_history_path=history_path,
        proposal_store_path=proposal_path,
    )
    rows = reloaded.list_proposals()
    assert len(rows) == 1
    assert rows[0]["proposal_id"] == proposal_id
    assert rows[0]["strategy_id"] == "alpha_rev"


def test_vote_history_persists_and_reloads(tmp_path: Path) -> None:
    history_path = tmp_path / "alpha_vote_history.jsonl"
    proposal_path = tmp_path / "alpha_proposals.json"
    dao = AlphaGovernanceDAO(
        vote_history_path=history_path,
        proposal_store_path=proposal_path,
    )
    proposal_id = dao.submit_proposal(
        strategy_id="alpha_mom",
        manager_id="team-a",
        expression="close / open - 1",
        zk_proof="abc123",
        metrics={"sharpe": 1.2},
    )

    assert dao.vote(proposal_id, "team-b", approve=True, rationale="looks good")
    assert history_path.is_file()

    reloaded = AlphaGovernanceDAO(
        vote_history_path=history_path,
        proposal_store_path=proposal_path,
    )
    rows = reloaded.list_vote_history(proposal_id)
    assert len(rows) == 1
    assert rows[0]["voter_team"] == "team-b"
    assert rows[0]["approve"] is True
