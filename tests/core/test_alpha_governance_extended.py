"""Regression tests for AlphaGovernanceDAO (Phase 12.2) and FactorAdmissionService."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.mesh.alpha_governance import (
    AlphaGovernanceDAO,
    FactorStatus,
    GovernanceVote,
    ZeroKnowledgePerformanceProof,
)


@pytest.fixture
def governance(tmp_path: Path) -> AlphaGovernanceDAO:
    """Create a DAO with isolated file paths."""
    vote_path = tmp_path / "votes.jsonl"
    proposal_path = tmp_path / "proposals.json"
    dao = AlphaGovernanceDAO(vote_history_path=vote_path, proposal_store_path=proposal_path)
    return dao


class TestAlphaGovernanceCore:
    """Factor proposal and voting flow."""

    def test_submit_proposal(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal(
            strategy_id="strat_001",
            manager_id="manager_a",
            expression="close > ma(close, 20)",
            zk_proof="0xabc123",
            metrics={"sharpe": 1.5, "returns": 0.12},
        )
        assert pid.startswith("prop-")
        assert governance._proposals[pid].status == FactorStatus.CANDIDATE

    def test_vote_approve(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s1", "m1", "expr", "proof", {"sharpe": 1.2})
        result = governance.vote(pid, "team_a", True, "Good factor")
        assert result is True
        assert governance._proposals[pid].votes_for == 1

    def test_vote_reject(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s1", "m1", "expr", "proof", {"sharpe": 0.5})
        governance.vote(pid, "team_a", False, "Low sharpe")
        assert governance._proposals[pid].votes_against == 1

    def test_tally_votes_pending(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s1", "m1", "expr", "proof", {"sharpe": 1.0})
        tally = governance.tally_votes(pid)
        assert tally["status"] == "pending"

    def test_tally_votes_approved(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s1", "m1", "expr", "proof", {"sharpe": 1.5})
        governance.vote(pid, "team_a", True)
        governance.vote(pid, "team_b", True)
        governance.vote(pid, "team_c", True)
        tally = governance.tally_votes(pid)
        assert tally["status"] == "approved"
        assert tally["approval_rate"] >= 0.6

    def test_tally_votes_rejected(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s1", "m1", "expr", "proof", {"sharpe": 0.3})
        governance.vote(pid, "team_a", False)
        governance.vote(pid, "team_b", False)
        tally = governance.tally_votes(pid)
        assert tally["status"] == "rejected"

    def test_vote_nonexistent_proposal(self, governance: AlphaGovernanceDAO):
        result = governance.vote("nonexistent", "team_a", True)
        assert result is False

    def test_get_proposal_with_tally(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s1", "m1", "expr", "proof", {"sharpe": 1.5})
        governance.vote(pid, "team_a", True)
        result = governance.get_proposal(pid)
        assert result is not None
        assert "tally" in result
        assert "vote_history" in result
        assert "timeline" in result

    def test_get_proposal_nonexistent(self, governance: AlphaGovernanceDAO):
        assert governance.get_proposal("nonexistent") is None

    def test_active_factors_after_tally(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s_active", "m1", "expr", "proof", {"sharpe": 2.0})
        governance.vote(pid, "team_a", True)
        governance.vote(pid, "team_b", True)
        governance.vote(pid, "team_c", True)
        governance.tally_votes(pid)
        active = governance.get_active_factors()
        assert len(active) >= 1
        assert any(f["strategy_id"] == "s_active" for f in active)

    def test_stats(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s1", "m1", "expr", "proof", {"sharpe": 1.0})
        governance.vote(pid, "team_a", True)
        governance.vote(pid, "team_b", False)
        stats = governance.stats()
        assert stats["proposals"] >= 1
        assert stats["votes"] == 2


class TestZeroKnowledgeProof:
    """Zero-knowledge performance proof generation and verification."""

    def test_generate_proof(self):
        proof = ZeroKnowledgePerformanceProof.generate_proof({"sharpe": 1.5, "returns": 0.12})
        assert len(proof) == 32
        assert isinstance(proof, str)

    def test_verify_proof(self):
        proof = ZeroKnowledgePerformanceProof.generate_proof({"sharpe": 1.5})
        result = ZeroKnowledgePerformanceProof.verify_proof(proof, {"sharpe": (1.0, 2.0)})
        assert result is True

    def test_proof_deterministic(self):
        p1 = ZeroKnowledgePerformanceProof.generate_proof({"sharpe": 1.5, "returns": 0.12})
        p2 = ZeroKnowledgePerformanceProof.generate_proof({"sharpe": 1.5, "returns": 0.12})
        assert p1 == p2


class TestFactorProposalSerialization:
    """FactorProposal dataclass behavior."""

    def test_status_enum_values(self):
        assert FactorStatus.CANDIDATE.value == "candidate"
        assert FactorStatus.TRIAL.value == "trial"
        assert FactorStatus.ACTIVE.value == "active"
        assert FactorStatus.DEGRADED.value == "degraded"
        assert FactorStatus.RETIRED.value == "retired"

    def test_governance_vote_dataclass(self):
        vote = GovernanceVote(voter_team="team_x", proposal_id="prop_001", approve=True, rationale="good")
        assert vote.approve is True
        assert vote.voter_team == "team_x"
        assert vote.rationale == "good"


class TestGovernanceDAOThresholds:
    """Quorum and majority thresholds."""

    def test_default_thresholds(self, governance: AlphaGovernanceDAO):
        assert governance.MAJORITY_THRESHOLD == 0.6
        assert governance.QUORUM_THRESHOLD == 0.5

    def test_proposal_timeline(self, governance: AlphaGovernanceDAO):
        pid = governance.submit_proposal("s1", "m1", "expr", "proof", {"sharpe": 1.0})
        timeline = governance.build_proposal_timeline(pid)
        assert len(timeline) >= 1
        assert timeline[0]["type"] == "submitted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
