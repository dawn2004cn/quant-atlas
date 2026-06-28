from __future__ import annotations

"""Dynamic Confidence Weighting - Historical Accuracy Weighted Aggregation.

This module implements from midify_plan12.md:
- WeightedAggregator: Aggregate agent results using historical accuracy
- Formula: Final_Score = Σ (Conclusion * Confidence * Historical_Accuracy) / Σ (Confidence * Accuracy)
- Meta-learning at decision layer

Usage:
    aggregator = WeightedAggregator()
    final_decision = aggregator.aggregate_with_accuracy_weight(
        agent_results,
        team_supervisor_context
    )
"""


from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger

from .auto_validator import AutoValidator

logger = get_logger(__name__)


@dataclass
class AgentWeightedResult:
    """Single agent result with weighting."""
    agent_name: str
    conclusion: str
    confidence: float
    historical_accuracy: float
    weighted_score: float
    evidence_keys: list[str] = field(default_factory=list)
    raw_report: str = ""


@dataclass
class WeightedAggregationResult:
    """Final aggregated result with weighting."""
    final_conclusion: str
    final_confidence: float
    weighted_score: float
    agent_results: list[AgentWeightedResult]
    accuracy_adjusted: bool
    meta_learning_note: str | None = None


class WeightedAggregator:
    """Aggregate agent results using historical accuracy weighting.

    Formula: Final_Score = Σ (Agent_Conclusion * Agent_Confidence * Historical_Accuracy) / Σ (Confidence * Accuracy)

    This implements meta-learning at the decision layer, automatically
    down-weighting agents with poor recent performance.
    """

    def __init__(self, validator: AutoValidator | None = None):
        self._validator = validator or AutoValidator()
        self._conclusion_values = {
            "BULLISH": 1.0,
            "BEARISH": -1.0,
            "NEUTRAL": 0.0,
        }

    def aggregate_with_accuracy_weight(
        self,
        agent_results: list[dict[str, Any]],
        min_accuracy_threshold: float = 0.3,
    ) -> WeightedAggregationResult:
        """Aggregate results with historical accuracy weighting."""
        rankings = self._validator.get_real_time_rankings()
        accuracy_map = {r["agent_name"]: r["accuracy"] for r in rankings}

        weighted_results = []

        for result in agent_results:
            agent_name = result.get("agent_name", "unknown")
            conclusion = result.get("conclusion", "NEUTRAL")
            confidence = result.get("confidence", 0.5)

            historical_accuracy = accuracy_map.get(agent_name, 0.5)

            if historical_accuracy < min_accuracy_threshold:
                logger.info(f"Agent {agent_name} below accuracy threshold ({historical_accuracy:.2f}), reducing weight")
                historical_accuracy = min_accuracy_threshold

            conclusion_value = self._conclusion_values.get(
                conclusion.upper() if isinstance(conclusion, str) else "NEUTRAL",
                0.0
            )

            weight_factor = confidence * historical_accuracy
            weighted_score = conclusion_value * weight_factor

            weighted_results.append(AgentWeightedResult(
                agent_name=agent_name,
                conclusion=conclusion,
                confidence=confidence,
                historical_accuracy=historical_accuracy,
                weighted_score=weighted_score,
                evidence_keys=result.get("evidence_keys", []),
                raw_report=result.get("raw_report", ""),
            ))

        total_weight = sum(r.confidence * r.historical_accuracy for r in weighted_results)

        if total_weight == 0:
            return self._create_neutral_result(weighted_results)

        final_score = sum(r.weighted_score for r in weighted_results) / total_weight

        final_conclusion, final_confidence = self._interpret_score(final_score, weighted_results)

        meta_note = self._generate_meta_learning_note(weighted_results, rankings)

        return WeightedAggregationResult(
            final_conclusion=final_conclusion,
            final_confidence=final_confidence,
            weighted_score=final_score,
            agent_results=weighted_results,
            accuracy_adjusted=True,
            meta_learning_note=meta_note,
        )

    def _interpret_score(
        self,
        final_score: float,
        results: list[AgentWeightedResult],
    ) -> tuple[str, float]:
        """Interpret weighted score into conclusion and confidence."""
        if final_score > 0.3:
            confidence = min(1.0, final_score)
            return "BULLISH", confidence
        elif final_score < -0.3:
            confidence = min(1.0, abs(final_score))
            return "BEARISH", confidence
        else:
            avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.5
            return "NEUTRAL", avg_confidence * 0.5

    def _generate_meta_learning_note(
        self,
        results: list[AgentWeightedResult],
        rankings: list[dict],
    ) -> str | None:
        """Generate meta-learning note about decision quality."""
        low_performers = [r for r in results if r.historical_accuracy < 0.4]
        high_performers = [r for r in results if r.historical_accuracy > 0.7]

        if not low_performers and not high_performers:
            return None

        note = "Meta-Learning: "
        note += f"High accuracy agents: {', '.join(r.agent_name for r in high_performers[:2])}"
        if low_performers:
            note += f". Reduced weight for: {', '.join(r.agent_name for r in low_performers[:2])}"

        return note

    def _create_neutral_result(
        self,
        results: list[AgentWeightedResult],
    ) -> WeightedAggregationResult:
        """Create neutral result when no valid aggregation possible."""
        return WeightedAggregationResult(
            final_conclusion="NEUTRAL",
            final_confidence=0.0,
            weighted_score=0.0,
            agent_results=results,
            accuracy_adjusted=False,
            meta_learning_note="Insufficient data for accuracy-weighted aggregation",
        )

    def get_agent_weight_report(self) -> list[dict[str, Any]]:
        """Get detailed report of all agent weights."""
        rankings = self._validator.get_real_time_rankings()
        return [
            {
                "agent_name": r["agent_name"],
                "accuracy": r["accuracy"],
                "recent_performance": r["recent_performance"],
                "rank": r.get("rank", 0),
                "recommendation": "increase_weight" if r["accuracy"] > 0.7 else "reduce_weight" if r["accuracy"] < 0.4 else "maintain",
            }
            for r in rankings
        ]


def create_weighted_aggregator(validator: AutoValidator | None = None) -> WeightedAggregator:
    """Factory to create weighted aggregator."""
    return WeightedAggregator(validator)
