"""Evidence-Driven Decision — Phase 15. Decision snapshot → factor weight correction loop."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DecisionSnapshot:
    """A snapshot of all factors and context at decision time."""
    snapshot_id: str
    decision_id: str
    user_id: int
    symbol: str
    direction: str  # buy/sell/hold
    factor_values: dict[str, float]  # factors at decision time
    ai_opinion: dict[str, Any] = field(default_factory=dict)
    market_context: dict[str, Any] = field(default_factory=dict)
    predicted_outcome: float = 0.0
    actual_outcome: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FactorCorrection:
    """Corrected weight recommendation for a factor."""
    factor_name: str
    old_weight: float
    new_weight: float
    correction_reason: str
    confidence: float = 0.5


class EvidenceDrivenDecisionService:
    """Evidence-driven decision correction: snapshot → factor weight adjustment."""

    def __init__(self):
        self._snapshots: dict[str, DecisionSnapshot] = {}
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "decision_snapshots.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def capture_snapshot(self, decision_id: str, user_id: int, symbol: str, direction: str,
                         factor_values: dict, ai_opinion: dict | None = None,
                         market_context: dict | None = None) -> DecisionSnapshot:
        """Capture a decision snapshot before execution."""
        snapshot = DecisionSnapshot(
            snapshot_id=str(uuid4().hex[:12]),
            decision_id=decision_id,
            user_id=user_id,
            symbol=symbol,
            direction=direction,
            factor_values=factor_values,
            ai_opinion=ai_opinion or {},
            market_context=market_context or {},
        )
        self._snapshots[snapshot.snapshot_id] = snapshot
        self._persist(snapshot)
        return snapshot

    def close_outcome(self, snapshot_id: str, actual_outcome: float):
        """Record actual outcome for a snapshot (called N days later)."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return
        snapshot.actual_outcome = actual_outcome
        self._persist(snapshot)

    def compute_corrections(self, snapshot_id: str) -> list[FactorCorrection]:
        """Compute factor weight corrections based on prediction vs outcome."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return []

        error = snapshot.actual_outcome - snapshot.predicted_outcome
        corrections = []

        for factor, value in snapshot.factor_values.items():
            if abs(value) < 0.001:
                continue
            # Simple heuristic: if error is large and factor was extreme, adjust
            impact = abs(value) * abs(error)
            if impact > 0.1:
                direction = -1 if value > 0 and error < 0 else 1
                adjustment = impact * 0.05  # 5% correction rate
                corrections.append(FactorCorrection(
                    factor_name=factor,
                    old_weight=value,
                    new_weight=round(value + direction * adjustment, 4),
                    correction_reason=f"Outcome error {error:.4f}, impact {impact:.4f}",
                    confidence=min(0.95, abs(error) * 2),
                ))

        return corrections

    def _persist(self, snapshot: DecisionSnapshot):
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "snapshot_id": snapshot.snapshot_id,
                "decision_id": snapshot.decision_id,
                "user_id": snapshot.user_id,
                "symbol": snapshot.symbol,
                "direction": snapshot.direction,
                "predicted_outcome": snapshot.predicted_outcome,
                "actual_outcome": snapshot.actual_outcome,
                "timestamp": snapshot.timestamp,
            }) + "\n")
