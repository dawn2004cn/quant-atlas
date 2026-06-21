"""Conditional routers for the custom trading research graph."""

from __future__ import annotations

from typing import Any, Literal

from ...agents.evidence_blackboard import (
    EvidenceType,
    get_evidence_blackboard,
)
from ...agents.constants import BlackboardKey
from .state import INVESTMENT_DEBATE_ROUNDS, RISK_DEBATE_ROUNDS, ResearchState


def route_after_fundamental(state: ResearchState) -> Literal["technical_analyst", "risk_manager"]:
    """Evidence-driven early exit: skip expensive nodes if critical evidence exists."""
    bb_data = get_evidence_blackboard().get_all_evidence()
    has_critical_risk = any(
        e.key == str(BlackboardKey.CRITICAL_RISK)
        for e in bb_data
    )
    if has_critical_risk:
        from ...core.logger import get_logger
        get_logger(__name__).info("Early exit: critical_risk evidence found, routing to risk_manager")
        return "risk_manager"
    return "technical_analyst"


def route_after_bull(state: ResearchState) -> Literal["bear", "risky_analyst"]:
    t = int(state.get("debate_turn") or 0)
    pairs = t // 2
    if pairs >= INVESTMENT_DEBATE_ROUNDS:
        return "risky_analyst"
    return "bear"


def route_after_bear(state: ResearchState) -> Literal["bull", "risky_analyst"]:
    t = int(state.get("debate_turn") or 0)
    pairs = t // 2
    if pairs >= INVESTMENT_DEBATE_ROUNDS:
        return "risky_analyst"
    return "bull"


def route_after_risky(state: ResearchState) -> Literal["safe_analyst", "risk_manager"]:
    t = int(state.get("risk_debate_turn") or 0)
    pairs = t // 2
    if pairs >= RISK_DEBATE_ROUNDS:
        return "risk_manager"
    return "safe_analyst"


def route_after_safe(state: ResearchState) -> Literal["risky_analyst", "risk_manager"]:
    t = int(state.get("risk_debate_turn") or 0)
    pairs = t // 2
    if pairs >= RISK_DEBATE_ROUNDS:
        return "risk_manager"
    return "risky_analyst"


# Map of router name → function for topology integration
ROUTERS: dict[str, Any] = {
    "route_after_fundamental": route_after_fundamental,
    "route_after_bull": route_after_bull,
    "route_after_bear": route_after_bear,
    "route_after_risky": route_after_risky,
    "route_after_safe": route_after_safe,
}
