from __future__ import annotations

"""Weighted Consensus & Game Theory - Agent performance-based voting.

This module implements:
- Weighted Consensus: Use historical accuracy as vote weight
- Devil's Advocate: Assign opposing role to highest-performing agent

Usage:
    consensus = WeightedConsensus()
    result = consensus.calculate_weighted_vote(agent_reports)
    result = consensus.assign_devils_advocate(agents)
"""


from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger

from .auto_validator import AutoValidator

logger = get_logger(__name__)


@dataclass
class AgentVote:
    """Single agent's vote with weight."""
    agent_name: str
    conclusion: str
    confidence: float
    weight: float = 1.0
    is_devils_advocate: bool = False


@dataclass
class WeightedVoteResult:
    """Result of weighted consensus calculation."""
    final_conclusion: str
    confidence: float
    bullish_score: float
    bearish_score: float
    neutral_score: float
    total_weight: float
    votes: list[AgentVote]
    dissenting_agents: list[str] = field(default_factory=list)


class WeightedConsensus:
    """Calculate consensus with performance-based weights."""

    def __init__(self, validator: AutoValidator | None = None):
        self._validator = validator or AutoValidator()
        self._weight_cache: dict[str, float] = {}

    def calculate_weighted_vote(
        self,
        agent_reports: list[dict[str, Any]],
        min_weight: float = 0.3,
        max_weight: float = 2.0,
    ) -> WeightedVoteResult:
        """Calculate weighted consensus from agent reports."""
        votes = []

        for report in agent_reports:
            agent_name = report.get("agent_name", "unknown")
            weight = self._get_agent_weight(agent_name, min_weight, max_weight)

            vote = AgentVote(
                agent_name=agent_name,
                conclusion=report.get("conclusion", "NEUTRAL"),
                confidence=report.get("confidence", 0.5),
                weight=weight,
            )
            votes.append(vote)

        return self._aggregate_votes(votes)

    def _get_agent_weight(
        self,
        agent_name: str,
        min_weight: float,
        max_weight: float,
    ) -> float:
        """Get agent's weight based on historical accuracy."""
        if agent_name in self._weight_cache:
            return self._weight_cache[agent_name]

        rankings = self._validator.get_real_time_rankings()

        accuracy = 0.5
        for r in rankings:
            if r["agent_name"] == agent_name:
                accuracy = r["accuracy"]
                break

        normalized = (accuracy - 0.5) / 0.5
        weight = 1.0 + normalized

        weight = max(min_weight, min(max_weight, weight))

        self._weight_cache[agent_name] = weight
        return weight

    def _aggregate_votes(self, votes: list[AgentVote]) -> WeightedVoteResult:
        """Aggregate weighted votes."""
        bullish_score = 0.0
        bearish_score = 0.0
        neutral_score = 0.0
        total_weight = 0.0

        for vote in votes:
            total_weight += vote.weight

            if "BULLISH" in vote.conclusion.upper():
                bullish_score += vote.weight * vote.confidence
            elif "BEARISH" in vote.conclusion.upper():
                bearish_score += vote.weight * vote.confidence
            else:
                neutral_score += vote.weight * vote.confidence

        if total_weight == 0:
            return WeightedVoteResult(
                final_conclusion="NEUTRAL",
                confidence=0.0,
                bullish_score=0.0,
                bearish_score=0.0,
                neutral_score=0.0,
                total_weight=0.0,
                votes=votes,
            )

        score_diff = bullish_score - bearish_score

        if score_diff > total_weight * 0.3:
            final_conclusion = "BULLISH"
            confidence = min(1.0, score_diff / total_weight)
        elif score_diff < -total_weight * 0.3:
            final_conclusion = "BEARISH"
            confidence = min(1.0, abs(score_diff) / total_weight)
        else:
            final_conclusion = "NEUTRAL"
            confidence = 0.5

        return WeightedVoteResult(
            final_conclusion=final_conclusion,
            confidence=confidence,
            bullish_score=bullish_score,
            bearish_score=bearish_score,
            neutral_score=neutral_score,
            total_weight=total_weight,
            votes=votes,
        )

    def assign_devils_advocate(
        self,
        agent_reports: list[dict[str, Any]],
    ) -> list[AgentVote]:
        """Assign devil's advocate role to highest-performing agent.

        The highest-performing agent is assigned an opposing role to
        find flaws in their own logic, preventing groupthink.
        """
        if not agent_reports:
            return []

        rankings = self._validator.get_real_time_rankings()

        if not rankings:
            return self._convert_to_votes(agent_reports)

        top_agent = rankings[0]["agent_name"]

        votes = []
        for report in agent_reports:
            agent_name = report.get("agent_name", "unknown")

            is_devils = agent_name == top_agent

            vote = AgentVote(
                agent_name=agent_name,
                conclusion=report.get("conclusion", "NEUTRAL"),
                confidence=report.get("confidence", 0.5),
                is_devils_advocate=is_devils,
            )

            if is_devils:
                logger.info(f"Devil's Advocate assigned to: {agent_name}")
                vote.conclusion = self._flip_conclusion(vote.conclusion)

            votes.append(vote)

        return votes

    def _flip_conclusion(self, conclusion: str) -> str:
        """Flip conclusion for devil's advocate."""
        upper = conclusion.upper()
        if "BULLISH" in upper:
            return "BEARISH"
        elif "BEARISH" in upper:
            return "BULLISH"
        return "NEUTRAL"

    def _convert_to_votes(
        self,
        agent_reports: list[dict[str, Any]],
    ) -> list[AgentVote]:
        """Convert reports to votes without game theory."""
        votes = []
        for report in agent_reports:
            votes.append(AgentVote(
                agent_name=report.get("agent_name", "unknown"),
                conclusion=report.get("conclusion", "NEUTRAL"),
                confidence=report.get("confidence", 0.5),
            ))
        return votes


def create_consensus(validator: AutoValidator | None = None) -> WeightedConsensus:
    """Factory to create weighted consensus calculator."""
    return WeightedConsensus(validator)
