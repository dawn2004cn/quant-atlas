"""Shadow Factor Pool — standby alpha candidates for hot-swap."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CandidateFactor:
    candidate_id: str
    expression: str
    category: str = ""
    ic: float = 0.0
    sharpe: float = 0.0
    complementarity_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "standby"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HotSwapDecision:
    decision_id: str
    decayed_factor_id: str
    replacement_candidate_id: str
    trigger_decay_rate: float
    complementarity_score: float
    decided_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class ShadowFactorPool:
    """In-memory shadow factor pool for proactive alpha hot-swap."""

    def __init__(self) -> None:
        self._candidates: dict[str, CandidateFactor] = {}
        self._decisions: list[HotSwapDecision] = []

    def add_candidate(self, candidate: CandidateFactor) -> CandidateFactor:
        self._candidates[candidate.candidate_id] = candidate
        return candidate

    def get_standby(self, decayed_category: str = "") -> CandidateFactor | None:
        best: CandidateFactor | None = None
        for c in self._candidates.values():
            if c.status != "standby":
                continue
            if decayed_category and c.category == decayed_category:
                continue
            if best is None or c.complementarity_score > best.complementarity_score:
                best = c
        return best

    def record_swap(self, decision: HotSwapDecision) -> HotSwapDecision:
        self._decisions.append(decision)
        candidate = self._candidates.get(decision.replacement_candidate_id)
        if candidate:
            candidate.status = "deployed"
        return decision

    def recent_decisions(self, limit: int = 20) -> list[HotSwapDecision]:
        items = sorted(self._decisions, key=lambda d: d.decided_at, reverse=True)
        return items[: max(1, limit)]


class AlphaHotSwapService:
    """Proactive alpha hot-swap orchestrator."""

    def __init__(self, *, decay_detector: Any | None = None, pool: ShadowFactorPool | None = None) -> None:
        self._decay = decay_detector
        self._pool = pool or ShadowFactorPool()

    def evaluate_hot_swap(self, factor_id: str, decay_rate: float, category: str = "") -> HotSwapDecision | None:
        if decay_rate < 0.35:
            return None
        replacement = self._pool.get_standby(decayed_category=category)
        if replacement is None:
            return None
        decision = HotSwapDecision(
            decision_id=f"swap-{datetime.now().strftime('%H%M%S')}",
            decayed_factor_id=factor_id,
            replacement_candidate_id=replacement.candidate_id,
            trigger_decay_rate=decay_rate,
            complementarity_score=replacement.complementarity_score,
        )
        return self._pool.record_swap(decision)

    def get_status(self) -> dict[str, Any]:
        return {
            "pool_size": len(self._pool._candidates),
            "decision_count": len(self._pool._decisions),
        }
