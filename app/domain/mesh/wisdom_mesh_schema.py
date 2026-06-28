"""Wisdom Mesh domain models — de-identified strategy sharing and crowdfactor experiments.

Extends the existing mesh_schema.py without modifying it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StrategyShareTier(str, Enum):
    """Access level for shared strategies."""

    OBSERVE = "observe"
    VOTE_FACTOR = "vote"
    DEPLOY = "deploy"


class WisdomContributionType(str, Enum):
    """Types of contributions to the Wisdom Mesh."""

    STRATEGY_UPLOAD = "strategy_upload"
    FACTOR_TWEAK = "factor_tweak"
    PARAMETER_VOTE = "parameter_vote"
    EVIDENCE_FEEDBACK = "evidence_feedback"


# ---------------------------------------------------------------------------
# De-identified strategy
# ---------------------------------------------------------------------------


@dataclass
class DeIdentifiedStrategy:
    """A user's strategy shared without exposing positions or P&L.

    All personal identifiers (user_id, account info, trade-level P&L)
    are stripped before storage. Only the strategy logic and aggregate
    performance metrics remain.
    """

    id: str = field(default_factory=lambda: uuid4().hex[:12])
    anonymized_id: str = field(default_factory=lambda: uuid4().hex)
    strategy_name: str = ""
    strategy_spec: dict[str, Any] = field(default_factory=dict)
    performance_summary: dict[str, Any] = field(default_factory=dict)
    success_score: float = 0.0
    contributor_tier: StrategyShareTier = StrategyShareTier.OBSERVE
    contributed_at: str = ""
    factor_config: dict[str, Any] = field(default_factory=dict)
    vote_count: int = 0
    vote_for: int = 0
    vote_against: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "anonymized_id": self.anonymized_id,
            "strategy_name": self.strategy_name,
            "strategy_spec": self.strategy_spec,
            "performance_summary": self.performance_summary,
            "success_score": round(self.success_score, 3),
            "contributor_tier": self.contributor_tier.value,
            "contributed_at": self.contributed_at,
            "factor_config": self.factor_config,
            "vote_count": self.vote_count,
            "vote_for": self.vote_for,
            "vote_against": self.vote_against,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeIdentifiedStrategy:
        return cls(
            id=data.get("id", uuid4().hex[:12]),
            anonymized_id=data.get("anonymized_id", uuid4().hex),
            strategy_name=data.get("strategy_name", ""),
            strategy_spec=data.get("strategy_spec", {}),
            performance_summary=data.get("performance_summary", {}),
            success_score=float(data.get("success_score", 0)),
            contributor_tier=StrategyShareTier(data.get("contributor_tier", "observe")),
            contributed_at=data.get("contributed_at", ""),
            factor_config=data.get("factor_config", {}),
            vote_count=data.get("vote_count", 0),
            vote_for=data.get("vote_for", 0),
            vote_against=data.get("vote_against", 0),
        )


# ---------------------------------------------------------------------------
# Crowdfactor contribution
# ---------------------------------------------------------------------------


@dataclass
class CrowdfactorContribution:
    """User-voted factor tweak contribution."""

    id: str = field(default_factory=lambda: uuid4().hex[:12])
    strategy_id: str = ""
    factor_name: str = ""
    original_weight: float = 0.0
    proposed_weight: float = 0.0
    votes_for: int = 0
    votes_against: int = 0
    rationale: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "factor_name": self.factor_name,
            "original_weight": self.original_weight,
            "proposed_weight": self.proposed_weight,
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "rationale": self.rationale,
            "created_at": self.created_at,
        }
