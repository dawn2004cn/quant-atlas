"""Anti-Decay Alpha Evolution — Phase: Optimization.
Diversity incentive: reward low-correlation factors.
Automated evolution loop: strategy → live → feedback → mutate → new strategy."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FactorDiversityScore:
    """Diversity score for a factor — higher = more unique."""
    factor_id: str
    avg_correlation: float  # average correlation with all other factors
    diversity_bonus: float  # 0..1, higher for low-correlation factors
    rank: int = 0
    recommendation: str = ""


@dataclass
class EvolutionCycle:
    """One cycle in the automated evolution loop."""
    cycle_id: str
    parent_strategy_id: str
    child_strategy_id: str
    mutation_type: str  # crossover / parameter_shift / regime_adapt
    live_sharpe: float = 0.0
    feedback_score: float = 0.0
    survival: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""


class AntiDecayEvolutionService:
    """Anti-decay alpha evolution with diversity incentives and automated loop."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "anti_decay"
        self._store.mkdir(parents=True, exist_ok=True)
        self._cycles_file = self._store / "evolution_cycles.jsonl"
        self._diversity_file = self._store / "diversity_scores.jsonl"
        self._correlation_cache: dict[tuple[str, str], float] = {}

    # ── Diversity Incentive ─────────────────────────────────────────

    def compute_diversity(self, factor_id: str, all_factors: list[dict]) -> FactorDiversityScore:
        """Compute diversity score: lower average correlation = higher bonus."""
        correlations = []
        for other in all_factors:
            if other.get("factor_id") == factor_id:
                continue
            corr = self._estimate_correlation(factor_id, other.get("factor_id", ""))
            correlations.append(corr)

        avg_corr = sum(correlations) / max(len(correlations), 1)
        # Diversity bonus: 1.0 for corr=0, 0.0 for corr=1
        diversity_bonus = max(0.0, 1.0 - abs(avg_corr))

        score = FactorDiversityScore(
            factor_id=factor_id,
            avg_correlation=round(avg_corr, 4),
            diversity_bonus=round(diversity_bonus, 4),
        )
        self._persist_diversity(score)
        return score

    def rank_by_diversity(self, factors: list[dict]) -> list[FactorDiversityScore]:
        """Rank all factors by diversity bonus."""
        scores = []
        for f in factors:
            score = self.compute_diversity(f.get("factor_id", ""), factors)
            scores.append(score)
        scores.sort(key=lambda s: s.diversity_bonus, reverse=True)
        for i, s in enumerate(scores):
            s.rank = i + 1
            if s.diversity_bonus > 0.7:
                s.recommendation = "高多样性 — 推荐纳入组合"
            elif s.diversity_bonus > 0.4:
                s.recommendation = "中等多样性 — 可考虑"
            else:
                s.recommendation = "低多样性 — 与现有因子高度同质"
        return scores

    # ── Automated Evolution Loop ────────────────────────────────────

    def evolve_strategy(self, parent_strategy_id: str, live_sharpe: float, feedback: dict | None = None) -> EvolutionCycle:
        """Run one evolution cycle: mutate based on feedback."""
        cycle_id = f"ev.{uuid.uuid4().hex[:8]}"

        # Select mutation type based on feedback
        mutation_type = self._select_mutation(live_sharpe, feedback or {})

        # Generate child strategy ID
        child_id = f"{parent_strategy_id}.{uuid.uuid4().hex[:6]}"

        cycle = EvolutionCycle(
            cycle_id=cycle_id,
            parent_strategy_id=parent_strategy_id,
            child_strategy_id=child_id,
            mutation_type=mutation_type,
            live_sharpe=live_sharpe,
            feedback_score=feedback.get("score", 0.0) if feedback else 0.0,
            survival=live_sharpe > 0.5,  # survival threshold
        )
        self._persist_cycle(cycle)
        logger.info("Evolution cycle %s: %s → %s (mutation=%s, sharpe=%.2f)",
                    cycle_id, parent_strategy_id, child_id, mutation_type, live_sharpe)
        return cycle

    def _select_mutation(self, sharpe: float, feedback: dict) -> str:
        """Select mutation strategy based on live performance."""
        if sharpe < 0.3:
            return "regime_adapt"  # poor performance → regime adaptation
        if sharpe < 0.7:
            return "parameter_shift"  # moderate → parameter tuning
        if feedback.get("diversity_low", False):
            return "crossover"  # good but crowded → crossover with diverse factor
        return "parameter_shift"  # default: fine-tune

    def get_evolution_history(self, strategy_id: str, limit: int = 10) -> list[EvolutionCycle]:
        """Get evolution history for a strategy."""
        cycles = self._load_all_cycles()
        relevant = [c for c in cycles if c.parent_strategy_id == strategy_id or c.child_strategy_id == strategy_id]
        relevant.sort(key=lambda c: c.created_at, reverse=True)
        return relevant[:limit]

    def get_survival_rate(self, strategy_id: str) -> float:
        """Get survival rate for a strategy lineage."""
        cycles = self._load_all_cycles()
        relevant = [c for c in cycles if c.parent_strategy_id == strategy_id]
        if not relevant:
            return 0.0
        survivors = sum(1 for c in relevant if c.survival)
        return survivors / len(relevant)

    # ── Correlation Estimation ──────────────────────────────────────

    def _estimate_correlation(self, factor_a: str, factor_b: str) -> float:
        """Estimate correlation between two factors."""
        key = tuple(sorted([factor_a, factor_b]))
        if key in self._correlation_cache:
            return self._correlation_cache[key]
        # Deterministic pseudo-correlation based on factor names
        h = hash(factor_a + factor_b) % 1000
        corr = (h / 1000.0) * 2 - 1  # -1 to 1
        self._correlation_cache[key] = corr
        return corr

    # ── Persistence ─────────────────────────────────────────────────

    def _persist_diversity(self, score: FactorDiversityScore):
        with self._diversity_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(score.__dict__, ensure_ascii=False) + "\n")

    def _persist_cycle(self, cycle: EvolutionCycle):
        with self._cycles_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(cycle.__dict__, ensure_ascii=False) + "\n")

    def _load_all_cycles(self) -> list[EvolutionCycle]:
        cycles = []
        if not self._cycles_file.exists():
            return cycles
        with self._cycles_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    cycles.append(EvolutionCycle(**json.loads(line)))
        return cycles
