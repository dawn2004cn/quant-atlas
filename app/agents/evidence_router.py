from __future__ import annotations

"""Evidence-Driven Routing - Conditional jumps based on blackboard evidence.

This module implements the Evidence-Driven Routing from midify_plan10.md:
- EvidenceRouter: Makes routing decisions based on evidence
- Condition-based skip logic for departments
- Cost and time optimization

Usage:
    router = EvidenceRouter()
    should_skip = router.should_skip_department("backtest", blackboard)
    routing_decision = router.decide_next_step(blackboard)
"""


from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger

from .evidence_blackboard import (
    EvidenceBlackboard,
    EvidenceType,
    get_evidence_blackboard,
)

logger = get_logger(__name__)


class SkipReason:
    """Reasons for skipping a department."""
    RISK_FLAG = "risk_flag"
    NO_DATA = "no_data"
    COST_OPTIMIZATION = "cost_optimization"
    EARLY_TERMINATION = "early_termination"


@dataclass
class RoutingDecision:
    """Routing decision for the next step."""
    action: str
    target: str | None
    reason: str
    confidence: float
    skip_departments: list[str] = field(default_factory=list)
    early_termination: bool = False


class EvidenceRouter:
    """Evidence-driven routing decision maker.

    Analyzes the blackboard to decide which departments to skip
    or which path to take based on critical evidence.
    """

    def __init__(self):
        self._risk_signals = self._init_risk_signals()
        self._skip_thresholds = self._init_skip_thresholds()

    def _init_risk_signals(self) -> dict[str, list[str]]:
        """Initialize risk signal patterns that trigger early termination."""
        return {
            "delisting_risk": ["delisting", "suspended", "bankruptcy"],
            "fraud_suspicion": ["fraud", "accounting_manipulation", "investigation"],
            "regulatory_risk": ["warning", "penalty", "investigation"],
            "liquidity_risk": ["zero_volume", "no_trades"],
        }

    def _init_skip_thresholds(self) -> dict[str, float]:
        """Initialize cost optimization thresholds."""
        return {
            "min_confidence_skip": 0.3,
            "max_cost_per_query": 0.01,
        }

    def should_skip_department(
        self,
        department: str,
        blackboard: EvidenceBlackboard | None = None,
    ) -> tuple[bool, str | None]:
        """Determine if a department should be skipped based on evidence.

        Returns:
            (should_skip, reason)
        """
        bb = blackboard or get_evidence_blackboard()

        all_evidence = bb.get_all_evidence()

        risk_evidence = self._check_risk_signals(all_evidence)
        if risk_evidence:
            logger.info(f"Skipping {department} due to risk: {risk_evidence}")
            return True, SkipReason.RISK_FLAG

        no_data_evidence = self._check_no_data(all_evidence)
        if no_data_evidence:
            logger.info(f"Skipping {department} due to no data: {no_data_evidence}")
            return True, SkipReason.NO_DATA

        return False, None

    def _check_risk_signals(self, evidence: list) -> str | None:
        """Check for risk signals in evidence."""
        for point in evidence:
            evidence_value = str(point.value).lower()
            evidence_narrative = point.narrative.lower() if point.narrative else ""

            for risk_type, patterns in self._risk_signals.items():
                for pattern in patterns:
                    if pattern in evidence_value or pattern in evidence_narrative:
                        logger.warning(f"Risk signal detected: {risk_type}")
                        return risk_type

        return None

    def _check_no_data(self, evidence: list) -> str | None:
        """Check if required data is missing."""
        required_keys = ["close_price", "volume", "market_cap"]

        for point in evidence:
            if point.key in required_keys and (point.value is None or point.value == 0):
                return f"missing_{point.key}"

        return None

    def decide_next_step(
        self,
        blackboard: EvidenceBlackboard | None = None,
        enabled_departments: list[str] | None = None,
    ) -> RoutingDecision:
        """Decide the next steps based on evidence analysis.

        Returns a RoutingDecision with action, target, and skip list.
        """
        bb = blackboard or get_evidence_blackboard()

        skip_departments = []
        confidence = 1.0

        all_evidence = bb.get_all_evidence()

        risk_evidence = self._check_risk_signals(all_evidence)
        if risk_evidence:
            skip_departments.extend([
                "backtest",
                "sentiment",
            ])
            confidence *= 0.5
            return RoutingDecision(
                action="risk_override",
                target="risk_department",
                reason=f"Risk signal: {risk_evidence}",
                confidence=confidence,
                skip_departments=skip_departments,
                early_termination=True,
            )

        fundamental_evidence = bb.get_evidence_by_type(EvidenceType.FUNDAMENTAL)
        if fundamental_evidence:
            for point in fundamental_evidence:
                if "negative" in str(point.value).lower():
                    skip_departments.append("sentiment")
                    confidence *= 0.9

        return RoutingDecision(
            action="continue",
            target=None,
            reason="Normal flow",
            confidence=confidence,
            skip_departments=skip_departments,
            early_termination=len(skip_departments) > 2,
        )

    def estimate_cost_savings(
        self,
        skip_departments: list[str],
        cost_per_department: float = 0.005,
    ) -> float:
        """Estimate token cost savings from skipping departments."""
        return len(skip_departments) * cost_per_department


class ConditionalRouter:
    """Conditional router with custom rules for specific scenarios."""

    def __init__(self):
        self._rules: list[tuple[callable, str]] = []

    def add_rule(
        self,
        condition: callable,
        action: str,
    ) -> None:
        """Add a custom routing rule."""
        self._rules.append((condition, action))

    def evaluate(
        self,
        context: dict[str, Any],
        blackboard: EvidenceBlackboard,
    ) -> str:
        """Evaluate rules and return action."""
        for condition, action in self._rules:
            try:
                if condition(context, blackboard):
                    return action
            except Exception as e:
                logger.warning(f"Rule evaluation failed: {e}")

        return "continue"


def create_default_router() -> EvidenceRouter:
    """Factory to create default evidence router."""
    return EvidenceRouter()
