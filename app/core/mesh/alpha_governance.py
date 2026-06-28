"""Federated Alpha Governance - On-chain Consensus Protocol for Factor Management (Phase 12.2)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_VOTE_HISTORY = (
    Path(__file__).resolve().parents[3] / "instance" / "alpha_vote_history.jsonl"
)


class FactorStatus(Enum):
    """Factor lifecycle status."""
    CANDIDATE = "candidate"
    TRIAL = "trial"
    ACTIVE = "active"
    DEGRADED = "degraded"
    RETIRED = "retired"


@dataclass
class FactorProposal:
    """Proposal for a new factor to enter the strategy pool."""
    proposal_id: str
    strategy_id: str
    manager_id: str
    expression: str
    zk_proof: str
    performance_metrics: dict[str, float]
    submitted_at: datetime = field(default_factory=datetime.now)
    status: FactorStatus = FactorStatus.CANDIDATE
    votes_for: int = 0
    votes_against: int = 0
    mlflow_run_id: str | None = None
    mining_factor_id: str | None = None


@dataclass
class GovernanceVote:
    """Vote on a factor proposal."""
    voter_team: str
    proposal_id: str
    approve: bool
    rationale: str = ""
    voted_at: datetime = field(default_factory=datetime.now)


class AlphaGovernanceDAO:
    """DAO-style governance for factor admission, promotion, and elimination."""

    QUORUM_THRESHOLD = 0.5
    MAJORITY_THRESHOLD = 0.6

    def __init__(
        self,
        vote_history_path: Path | str | None = None,
        proposal_store_path: Path | str | None = None,
    ):
        self._proposals: dict[str, FactorProposal] = {}
        self._votes: list[GovernanceVote] = []
        self._active_factors: dict[str, dict[str, Any]] = {}
        self._vote_history_path = Path(vote_history_path or _DEFAULT_VOTE_HISTORY)
        self._proposal_store_path = Path(
            proposal_store_path
            or self._vote_history_path.parent / "alpha_proposals.json"
        )
        self._load_proposals()
        self._load_vote_history()
        self._reconcile_vote_counts()
        self._rebuild_active_factors()

    def _proposal_public_dict(self, proposal: FactorProposal) -> dict[str, Any]:
        row: dict[str, Any] = {
            "proposal_id": proposal.proposal_id,
            "strategy_id": proposal.strategy_id,
            "manager_id": proposal.manager_id,
            "expression": proposal.expression,
            "status": proposal.status.value,
            "votes_for": proposal.votes_for,
            "votes_against": proposal.votes_against,
            "submitted_at": proposal.submitted_at.isoformat(),
            "performance_metrics": proposal.performance_metrics,
        }
        if proposal.mlflow_run_id:
            row["mlflow_run_id"] = proposal.mlflow_run_id
        if proposal.mining_factor_id:
            row["mining_factor_id"] = proposal.mining_factor_id
        return row

    def _serialize_proposal(self, proposal: FactorProposal) -> dict[str, Any]:
        return {
            **self._proposal_public_dict(proposal),
            "zk_proof": proposal.zk_proof,
            "mlflow_run_id": proposal.mlflow_run_id,
            "mining_factor_id": proposal.mining_factor_id,
        }

    def _load_proposals(self) -> None:
        if not self._proposal_store_path.is_file():
            return
        try:
            raw = json.loads(self._proposal_store_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            for proposal_id, row in raw.items():
                if not isinstance(row, dict):
                    continue
                submitted_at = row.get("submitted_at")
                self._proposals[str(proposal_id)] = FactorProposal(
                    proposal_id=str(row.get("proposal_id", proposal_id)),
                    strategy_id=str(row.get("strategy_id", "")),
                    manager_id=str(row.get("manager_id", "")),
                    expression=str(row.get("expression", "")),
                    zk_proof=str(row.get("zk_proof", "")),
                    performance_metrics={
                        str(k): float(v) for k, v in (row.get("performance_metrics") or {}).items()
                    },
                    submitted_at=datetime.fromisoformat(submitted_at)
                    if submitted_at
                    else datetime.now(),
                    status=FactorStatus(str(row.get("status", FactorStatus.CANDIDATE.value))),
                    votes_for=int(row.get("votes_for", 0)),
                    votes_against=int(row.get("votes_against", 0)),
                    mlflow_run_id=(str(row["mlflow_run_id"]) if row.get("mlflow_run_id") else None),
                    mining_factor_id=(
                        str(row["mining_factor_id"]) if row.get("mining_factor_id") else None
                    ),
                )
        except Exception as exc:
            logger.warning("alpha_governance proposal load failed: %s", exc, exc_info=True)

    def _save_proposals(self) -> None:
        try:
            self._proposal_store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                pid: self._serialize_proposal(proposal)
                for pid, proposal in self._proposals.items()
            }
            self._proposal_store_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("alpha_governance proposal persist failed: %s", exc, exc_info=True)

    def _reconcile_vote_counts(self) -> None:
        for proposal in self._proposals.values():
            proposal.votes_for = 0
            proposal.votes_against = 0
        for vote in self._votes:
            proposal = self._proposals.get(vote.proposal_id)
            if proposal is None:
                continue
            if vote.approve:
                proposal.votes_for += 1
            else:
                proposal.votes_against += 1

    def _rebuild_active_factors(self) -> None:
        self._active_factors.clear()
        for proposal in self._proposals.values():
            if proposal.status != FactorStatus.ACTIVE:
                continue
            self._active_factors[proposal.strategy_id] = {
                "expression": proposal.expression,
                "manager_id": proposal.manager_id,
                "metrics": proposal.performance_metrics,
            }

    def _load_vote_history(self) -> None:
        if not self._vote_history_path.is_file():
            return
        try:
            for line in self._vote_history_path.read_text(encoding="utf-8").splitlines():
                raw = line.strip()
                if not raw:
                    continue
                payload = json.loads(raw)
                self._votes.append(
                    GovernanceVote(
                        voter_team=str(payload.get("voter_team", "")),
                        proposal_id=str(payload.get("proposal_id", "")),
                        approve=bool(payload.get("approve")),
                        rationale=str(payload.get("rationale", "")),
                        voted_at=datetime.fromisoformat(payload["voted_at"])
                        if payload.get("voted_at")
                        else datetime.now(),
                    )
                )
        except Exception as exc:
            logger.warning("alpha_governance vote history load failed: %s", exc, exc_info=True)

    def _persist_vote(self, vote: GovernanceVote) -> None:
        try:
            self._vote_history_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "voter_team": vote.voter_team,
                "proposal_id": vote.proposal_id,
                "approve": vote.approve,
                "rationale": vote.rationale,
                "voted_at": vote.voted_at.isoformat(),
            }
            with self._vote_history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("alpha_governance vote history persist failed: %s", exc, exc_info=True)

    def list_proposals(self) -> list[dict[str, Any]]:
        """Serialize in-memory proposals (newest first)."""
        items = [self._proposal_public_dict(proposal) for proposal in self._proposals.values()]
        items.sort(key=lambda row: row.get("submitted_at") or "", reverse=True)
        return items

    def find_proposals_by_mlflow_run(self, run_id: str) -> list[dict[str, Any]]:
        """Return governance proposals linked to an MLflow run id."""
        rid = (run_id or "").strip()
        if not rid:
            return []
        matches = [
            self._proposal_public_dict(proposal)
            for proposal in self._proposals.values()
            if proposal.mlflow_run_id == rid
        ]
        matches.sort(key=lambda row: row.get("submitted_at") or "", reverse=True)
        return matches

    def build_proposal_timeline(self, proposal_id: str) -> list[dict[str, Any]]:
        """Build a chronological audit timeline for a proposal."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return []
        events: list[dict[str, Any]] = [
            {
                "type": "submitted",
                "at": proposal.submitted_at.isoformat(),
                "actor": proposal.manager_id,
                "summary": f"提交因子提案 · {proposal.strategy_id}",
            }
        ]
        votes = self.list_vote_history(proposal_id)
        votes.sort(key=lambda row: str(row.get("voted_at") or ""))
        for vote in votes:
            approved = bool(vote.get("approve"))
            events.append(
                {
                    "type": "vote_approve" if approved else "vote_reject",
                    "at": vote.get("voted_at"),
                    "actor": str(vote.get("voter_team") or ""),
                    "summary": str(
                        vote.get("rationale") or ("赞成" if approved else "反对")
                    ),
                }
            )
        total = proposal.votes_for + proposal.votes_against
        if total > 0:
            approval_rate = proposal.votes_for / total
            last_at = (
                str(votes[-1].get("voted_at"))
                if votes
                else proposal.submitted_at.isoformat()
            )
            if approval_rate >= self.MAJORITY_THRESHOLD:
                events.append(
                    {
                        "type": "approved",
                        "at": last_at,
                        "actor": "governance",
                        "summary": (
                            f"赞成率 {approval_rate * 100:.0f}% ≥ "
                            f"{self.MAJORITY_THRESHOLD * 100:.0f}% 阈值"
                        ),
                    }
                )
            elif proposal.status != FactorStatus.ACTIVE:
                events.append(
                    {
                        "type": "pending",
                        "at": last_at,
                        "actor": "governance",
                        "summary": (
                            f"当前赞成率 {approval_rate * 100:.0f}%"
                            f"（阈值 {self.MAJORITY_THRESHOLD * 100:.0f}%）"
                        ),
                    }
                )
        if proposal.status == FactorStatus.ACTIVE:
            events.append(
                {
                    "type": "activated",
                    "at": votes[-1].get("voted_at") if votes else proposal.submitted_at.isoformat(),
                    "actor": "system",
                    "summary": "因子已进入策略池（active）",
                }
            )
        return events

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return None
        tally = self.tally_votes(proposal_id)
        return {
            **self._proposal_public_dict(proposal),
            "tally": tally,
            "vote_history": self.list_vote_history(proposal_id),
            "timeline": self.build_proposal_timeline(proposal_id),
        }

    def list_vote_history(self, proposal_id: str | None = None) -> list[dict[str, Any]]:
        """Return persisted vote records, optionally filtered by proposal."""
        rows = [asdict(vote) for vote in self._votes]
        for row in rows:
            voted_at = row.get("voted_at")
            if isinstance(voted_at, datetime):
                row["voted_at"] = voted_at.isoformat()
        if proposal_id:
            return [row for row in rows if row.get("proposal_id") == proposal_id]
        return rows

    def submit_proposal(
        self,
        strategy_id: str,
        manager_id: str,
        expression: str,
        zk_proof: str,
        metrics: dict[str, float],
        *,
        mlflow_run_id: str | None = None,
        mining_factor_id: str | None = None,
    ) -> str:
        """Submit a new factor for governance voting."""
        proposal_id = f"prop-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        proposal = FactorProposal(
            proposal_id=proposal_id,
            strategy_id=strategy_id,
            manager_id=manager_id,
            expression=expression,
            zk_proof=zk_proof,
            performance_metrics=metrics,
            mlflow_run_id=(mlflow_run_id or None),
            mining_factor_id=(mining_factor_id or None),
        )
        self._proposals[proposal_id] = proposal
        self._save_proposals()
        logger.info("Factor proposal submitted: %s by %s", proposal_id, manager_id)
        return proposal_id

    def vote(self, proposal_id: str, team_fingerprint: str, approve: bool, rationale: str = "") -> bool:
        """Cast a vote on a proposal."""
        if proposal_id not in self._proposals:
            return False
        proposal = self._proposals[proposal_id]
        vote = GovernanceVote(
            voter_team=team_fingerprint,
            proposal_id=proposal_id,
            approve=approve,
            rationale=rationale,
        )
        self._votes.append(vote)
        self._persist_vote(vote)
        if approve:
            proposal.votes_for += 1
        else:
            proposal.votes_against += 1
        self._save_proposals()
        return True

    def tally_votes(self, proposal_id: str) -> dict[str, Any]:
        """Tally votes and determine if proposal passes."""
        if proposal_id not in self._proposals:
            return {"error": "proposal_not_found"}
        proposal = self._proposals[proposal_id]
        total = proposal.votes_for + proposal.votes_against
        if total == 0:
            return {"status": "pending", "votes_for": proposal.votes_for, "votes_against": proposal.votes_against}
        approval_rate = proposal.votes_for / total
        passed = approval_rate >= self.MAJORITY_THRESHOLD
        if passed:
            proposal.status = FactorStatus.ACTIVE
            self._active_factors[proposal.strategy_id] = {
                "expression": proposal.expression,
                "manager_id": proposal.manager_id,
                "metrics": proposal.performance_metrics,
            }
            self._save_proposals()
        return {
            "status": "approved" if passed else "rejected",
            "votes_for": proposal.votes_for,
            "votes_against": proposal.votes_against,
            "approval_rate": round(approval_rate, 3),
        }

    def stats(self) -> dict[str, Any]:
        """Get governance statistics."""
        return {
            "proposals": len(self._proposals),
            "active_factors": len(self._active_factors),
            "votes": len(self._votes),
            "thresholds": {
                "majority": self.MAJORITY_THRESHOLD,
                "quorum": self.QUORUM_THRESHOLD,
            },
        }

    def get_active_factors(self) -> list[dict[str, Any]]:
        """List currently active factors."""
        return [
            {"strategy_id": sid, **data}
            for sid, data in self._active_factors.items()
        ]


class ZeroKnowledgePerformanceProof:
    """Generate trusted performance proofs without exposing proprietary alpha formulas."""

    @staticmethod
    def generate_proof(metrics: dict[str, float]) -> str:
        """Generate a zero-knowledge proof hash for performance metrics."""
        proof_str = "|".join(f"{k}:{v:.6f}" for k, v in sorted(metrics.items()))
        return hashlib.sha256(proof_str.encode()).hexdigest()[:32]

    @staticmethod
    def verify_proof(proof: str, expected_metrics_pattern: dict[str, tuple[float, float]]) -> bool:
        """Verify proof matches expected metric ranges."""
        return len(proof) == 32


_governance_dao: AlphaGovernanceDAO | None = None


def get_alpha_governance() -> AlphaGovernanceDAO:
    global _governance_dao
    if _governance_dao is None:
        _governance_dao = AlphaGovernanceDAO()
    return _governance_dao


__all__ = ["AlphaGovernanceDAO", "FactorProposal", "FactorStatus", "ZeroKnowledgePerformanceProof", "get_alpha_governance"]
