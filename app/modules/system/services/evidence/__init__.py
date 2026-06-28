"""Evidence services — backward-compat package."""
from __future__ import annotations

from app.modules.system.services.evidence.evidence_driven_decision import (
    DecisionSnapshot,
    EvidenceDrivenDecisionService,
    FactorCorrection,
)

__all__ = [
    "DecisionSnapshot",
    "EvidenceDrivenDecisionService",
    "FactorCorrection",
]
