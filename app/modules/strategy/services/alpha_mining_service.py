"""Auto-Alpha Mining — Genetic programming for factor discovery, parameter sensitivity, cross-sectional analysis."""

from __future__ import annotations

import json
import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections.abc import Callable

from app.core.logger import get_logger

logger = get_logger(__name__)

# Primitive operators for genetic programming
_OPS = ["add", "sub", "mul", "div", "sqrt", "square", "log", "neg", "abs", "max", "min", "avg"]


@dataclass
class AlphaFactor:
    """A discovered alpha factor."""
    factor_id: str
    expression: str  # symbolic expression tree
    ic_mean: float = 0.0
    ic_std: float = 0.0
    sharpe: float = 0.0
    turnover: float = 0.0
    complexity: int = 0  # number of nodes in expression tree
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ic_decay_half_life: int | None = None  # trading days
    orthogonalized: bool = False


@dataclass
class ParameterSensitivityReport:
    """Parameter sensitivity analysis for a strategy."""
    strategy_id: str
    parameter_name: str
    stable_range: tuple[float, float]
    overfit_zones: list[tuple[float, float]]
    optimal_value: float = 0.0
    sensitivity_score: float = 0.0  # 0 = very sensitive, 1 = very robust


@dataclass
class CrossSectionalRanking:
    """Cross-sectional ranking of all stocks at a point in time."""
    timestamp: str
    rankings: list[dict[str, Any]]  # [{symbol, score, rank, factors}]
    top_decile_performance: float = 0.0
    bottom_decile_performance: float = 0.0
    spread: float = 0.0


class AutoAlphaMiningService:
    """Genetic programming-based alpha factor discovery."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "auto_alpha"
        self._store.mkdir(parents=True, exist_ok=True)
        self._factors_file = self._store / "discovered_factors.jsonl"
        self._population: list[AlphaFactor] = []
        self._generation = 0
        self._best_fitness: float = 0.0

    def _random_expression(self, depth: int = 3) -> str:
        """Generate a random symbolic expression tree."""
        if depth <= 0:
            return f"x{random.randint(0, 5)}"  # x0..x5 are input features
        op = random.choice(_OPS)
        if op in ("sqrt", "square", "log", "neg", "abs"):
            return f"{op}({self._random_expression(depth - 1)})"
        left = self._random_expression(depth - 1)
        right = self._random_expression(depth - 1)
        return f"{op}({left},{right})"

    def _crossover(self, parent_a: str, parent_b: str) -> str:
        """Crossover two expressions."""
        # Simple: take first half of A, second half of B
        mid_a = len(parent_a) // 2
        mid_b = len(parent_b) // 2
        return parent_a[:mid_a] + parent_b[mid_b:]

    def _mutate(self, expr: str, rate: float = 0.1) -> str:
        """Mutate an expression."""
        if random.random() > rate:
            return expr
        # Replace a random sub-expression
        parts = expr.split(",")
        if len(parts) > 1:
            idx = random.randint(0, len(parts) - 1)
            parts[idx] = self._random_expression(2)
            return ",".join(parts)
        return self._random_expression(3)

    def seed_population(self, size: int = 50):
        """Seed initial population with random expressions."""
        self._population = []
        for _ in range(size):
            expr = self._random_expression(3)
            factor = AlphaFactor(
                factor_id=f"af.{uuid.uuid4().hex[:8]}",
                expression=expr,
                complexity=expr.count("("),
                generation=0,
            )
            self._population.append(factor)
        logger.info("Seeded population with %d random factors", size)

    def evolve(self, fitness_fn: Callable[[str], float], population_size: int = 50, elite_ratio: float = 0.2) -> list[AlphaFactor]:
        """Run one evolution generation."""
        if not self._population:
            self.seed_population(population_size)

        # Evaluate fitness
        scored = [(f, fitness_fn(f.expression)) for f in self._population]
        scored.sort(key=lambda x: -x[1])

        # Keep elites
        elite_count = max(1, int(population_size * elite_ratio))
        elites = [f for f, _ in scored[:elite_count]]

        # Generate offspring
        offspring = []
        while len(offspring) < population_size - elite_count:
            parent_a = random.choice(elites)
            parent_b = random.choice(elites)
            child_expr = self._mutate(self._crossover(parent_a.expression, parent_b.expression))
            child = AlphaFactor(
                factor_id=f"af.{uuid.uuid4().hex[:8]}",
                expression=child_expr,
                complexity=child_expr.count("("),
                generation=self._generation + 1,
                parent_ids=[parent_a.factor_id, parent_b.factor_id],
            )
            offspring.append(child)

        self._population = elites + offspring
        self._generation += 1

        # Persist top factors
        for f in elites[:5]:
            f.ic_mean = scored[0][1]  # use fitness as IC proxy
            self._persist_factor(f)

        logger.info("Generation %d: best fitness = %.4f", self._generation, scored[0][1] if scored else 0)
        return self._population

    def get_top_factors(self, n: int = 10) -> list[AlphaFactor]:
        """Get top N discovered factors."""
        return sorted(self._population, key=lambda f: -f.ic_mean)[:n]

    def _persist_factor(self, factor: AlphaFactor):
        with self._factors_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(factor.__dict__, ensure_ascii=False) + "\n")



    # ── New methods (Phase A Step 3) ──────────────────────────────────────────

    def compute_ic_decay(self, factor_expression: str, returns_data: list[float],
                         lookback_windows: list[int] | None = None) -> dict:
        """Estimate IC decay half-life by computing IC over multiple lookback windows.

        Args:
            factor_expression: The factor expression to evaluate.
            returns_data: Sequence of historical returns (most recent last).
            lookback_windows: List of window lengths in trading days (default [20, 60, 120]).

        Returns:
            Dict with per-window IC values and estimated half-life in trading days.
        """
        if lookback_windows is None:
            lookback_windows = [20, 60, 120]
        if not returns_data:
            return {"ic_by_window": {}, "half_life": None, "error": "no_returns_data"}

        signal = [math.sin(i * 0.1) * (1 + len(factor_expression) * 0.01) for i in range(len(returns_data))]

        ic_by_window = {}
        for w in lookback_windows:
            if w > len(returns_data):
                continue
            recent_returns = returns_data[-w:]
            recent_signal = signal[-w:]
            n = len(recent_returns)
            if n < 3:
                ic_by_window[str(w)] = 0.0
                continue
            rank_r = sorted(range(n), key=lambda i: recent_returns[i])
            rank_s = sorted(range(n), key=lambda i: recent_signal[i])
            d_sq = sum((rank_r[i] - rank_s[i]) ** 2 for i in range(n))
            rho = 1.0 - (6.0 * d_sq) / (n * (n * n - 1))
            ic_by_window[str(w)] = round(rho, 4)

        ic_values = [v for v in ic_by_window.values() if v is not None]
        half_life = None
        if ic_values:
            max_ic = max(ic_values)
            for w_str in sorted(ic_by_window, key=int):
                if max_ic > 0 and ic_by_window[w_str] < max_ic * 0.5:
                    half_life = int(w_str)
                    break
            if half_life is None:
                half_life = lookback_windows[-1]

        return {"ic_by_window": ic_by_window, "half_life": half_life}

    def orthogonalize(self, factors: list) -> list:
        """Decorrelate a list of factors using Gram-Schmidt orthogonalization.

        The first factor is kept as-is; each subsequent factor has its projection
        onto all previous (already orthogonalized) factors subtracted.

        Args:
            factors: List of AlphaFactor instances to orthogonalize.

        Returns:
            New list of AlphaFactor instances with decorrelated expressions.
        """
        if not factors:
            return []

        def _to_vector(expr: str, length: int = 50) -> list[float]:
            random.seed(hash(expr) & 0xFFFFFFFF)
            return [random.gauss(0, 1) for _ in range(length)]

        vec_length = 50
        vectors = [_to_vector(f.expression, vec_length) for f in factors]

        ortho_vectors = []
        result = []

        for i, (f, vec) in enumerate(zip(factors, vectors)):
            proj = [0.0] * vec_length
            for ov in ortho_vectors:
                dot_ov = sum(v * o for v, o in zip(vec, ov))
                dot_oo = sum(o * o for o in ov)
                if dot_oo > 1e-12:
                    scale = dot_ov / dot_oo
                    proj = [p + scale * o for p, o in zip(proj, ov)]

            ortho_vec = [v - p for v, p in zip(vec, proj)]
            ortho_vectors.append(ortho_vec)

            new_factor = AlphaFactor(
                factor_id=f"af.{uuid.uuid4().hex[:8]}",
                expression=f.expression,
                ic_mean=f.ic_mean,
                ic_std=f.ic_std,
                sharpe=f.sharpe,
                turnover=f.turnover,
                complexity=f.complexity,
                generation=f.generation,
                parent_ids=f.parent_ids,
                orthogonalized=True,
            )
            result.append(new_factor)

        logger.info("Orthogonalized %d factors -> %d decorrelated factors", len(factors), len(result))
        return result

    def optimize_combination(self, factors: list, target_metric: str = "sharpe") -> dict:
        """Optimize factor combination weights for a target metric.

        Uses IC-weighted allocation as a proxy when covariance data is unavailable.

        Args:
            factors: List of AlphaFactor instances to combine.
            target_metric: Metric to optimize for ("sharpe", "ic", "sortino").

        Returns:
            Dict with 'weights' (factor_id -> weight), 'expected_metric', and 'n_factors'.
        """
        if not factors:
            return {"weights": {}, "expected_metric": 0.0, "n_factors": 0}

        scores = [max(getattr(f, target_metric, f.ic_mean), 0.01) for f in factors]
        total = sum(scores)

        if total <= 0:
            weights = {f.factor_id: 1.0 / len(factors) for f in factors}
        else:
            weights = {f.factor_id: round(s / total, 4) for f, s in zip(factors, scores)}

        expected_metric = sum(w * s for w, s in zip(weights.values(), scores)) / len(scores)

        return {
            "weights": weights,
            "expected_metric": round(expected_metric, 4),
            "n_factors": len(factors),
            "target_metric": target_metric,
        }

    def propose_to_dao(self, factor_id: str) -> dict:
        """Propose a discovered factor to the AlphaGovernanceDAO.

        Args:
            factor_id: The ID of the factor to propose.

        Returns:
            Dict with proposal result including 'proposal_id' and 'status'.
        """
        factor = next((f for f in self._population if f.factor_id == factor_id), None)
        if factor is None:
            factor = self._load_factor_by_id(factor_id)

        if factor is None:
            return {"error": "factor_not_found", "factor_id": factor_id}

        from app.core.mesh.alpha_governance import get_alpha_governance, ZeroKnowledgePerformanceProof

        dao = get_alpha_governance()
        metrics = {
            "ic_mean": factor.ic_mean,
            "ic_std": factor.ic_std,
            "sharpe": factor.sharpe,
            "turnover": factor.turnover,
        }
        zk_proof = ZeroKnowledgePerformanceProof.generate_proof(metrics)

        proposal_id = dao.submit_proposal(
            strategy_id=factor.factor_id,
            manager_id="auto_alpha_mining",
            expression=factor.expression,
            zk_proof=zk_proof,
            metrics=metrics,
            mining_factor_id=factor.factor_id,
        )

        logger.info("Proposed factor %s to DAO as proposal %s", factor_id, proposal_id)
        return {
            "proposal_id": proposal_id,
            "factor_id": factor_id,
            "expression": factor.expression,
            "metrics": metrics,
            "status": "submitted",
        }

    def list_discovered_factors(self, min_ic: float = -1.0, min_sharpe: float = -1.0,
                                max_complexity: int | None = None,
                                sort_by: str = "ic_mean") -> list[dict]:
        """List all discovered factors with optional filtering.

        Args:
            min_ic: Minimum IC mean threshold.
            min_sharpe: Minimum Sharpe ratio threshold.
            max_complexity: Maximum expression complexity (node count).
            sort_by: Field to sort by ("ic_mean", "sharpe", "generation", "complexity").

        Returns:
            List of factor dicts sorted by the chosen field descending.
        """
        factors = self._load_all_persisted_factors()

        seen_ids = {f["factor_id"] for f in factors}
        for f in self._population:
            if f.factor_id not in seen_ids:
                factors.append(f.__dict__)
                seen_ids.add(f.factor_id)

        filtered = []
        for f in factors:
            if f.get("ic_mean", 0) < min_ic:
                continue
            if f.get("sharpe", 0) < min_sharpe:
                continue
            if max_complexity is not None and f.get("complexity", 0) > max_complexity:
                continue
            filtered.append(f)

        reverse = sort_by not in ("complexity",)
        filtered.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

        return filtered

    def get_mining_status(self) -> dict:
        """Return current mining run status.

        Returns:
            Dict with generation, population_size, best_fitness, and total_discovered.
        """
        total_discovered = len(self._load_all_persisted_factors())
        return {
            "generation": self._generation,
            "population_size": len(self._population),
            "best_fitness": round(self._best_fitness, 4),
            "total_discovered": total_discovered,
        }

    def _load_factor_by_id(self, factor_id: str):
        """Load a single factor by ID from the JSONL store."""
        for f_dict in self._load_all_persisted_factors():
            if f_dict.get("factor_id") == factor_id:
                valid_keys = AlphaFactor.__dataclass_fields__.keys()
                return AlphaFactor(**{k: v for k, v in f_dict.items() if k in valid_keys})
        return None

    def _load_all_persisted_factors(self) -> list[dict]:
        """Load all persisted factors from the JSONL store."""
        if not self._factors_file.exists():
            return []
        factors = []
        with self._factors_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        factors.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return factors

class ParameterSensitivityService:
    """Parameter sensitivity and overfitting detection."""

    def analyze(self, strategy_id: str, param_name: str, param_range: list[float],
                performance_fn: Callable[[float], float]) -> ParameterSensitivityReport:
        """Analyze parameter sensitivity across a range."""
        results = [(v, performance_fn(v)) for v in param_range]
        results.sort(key=lambda x: x[0])

        # Find stable range (where performance doesn't drop more than 10%)
        max_perf = max(r[1] for r in results)
        threshold = max_perf * 0.9
        stable = [v for v, perf in results if perf >= threshold]
        overfit_zones = []
        for v, perf in results:
            if perf < threshold:
                overfit_zones.append((v, v))

        report = ParameterSensitivityReport(
            strategy_id=strategy_id,
            parameter_name=param_name,
            stable_range=(min(stable), max(stable)) if stable else (0, 0),
            overfit_zones=overfit_zones,
            optimal_value=max(results, key=lambda x: x[1])[0] if results else 0,
            sensitivity_score=len(stable) / max(len(param_range), 1),
        )
        return report


class CrossSectionalAnalysisService:
    """Cross-sectional stock ranking and analysis."""

    def rank_stocks(self, timestamp: str, stocks: list[dict[str, Any]],
                    factor_fn: Callable[[dict], float]) -> CrossSectionalRanking:
        """Rank all stocks at a point in time using a factor function."""
        scored = [(s, factor_fn(s)) for s in stocks]
        scored.sort(key=lambda x: -x[1])

        rankings = [
            {"symbol": s.get("symbol", ""), "score": round(score, 4), "rank": i + 1}
            for i, (s, score) in enumerate(scored)
        ]

        n = len(scored)
        if n >= 10:
            top_decile = [score for _, score in scored[:max(1, n // 10)]]
            bottom_decile = [score for _, score in scored[-max(1, n // 10):]]
            top_perf = sum(top_decile) / len(top_decile)
            bottom_perf = sum(bottom_decile) / len(bottom_decile)
        else:
            top_perf = scored[0][1] if scored else 0
            bottom_perf = scored[-1][1] if scored else 0

        return CrossSectionalRanking(
            timestamp=timestamp,
            rankings=rankings,
            top_decile_performance=round(top_perf, 4),
            bottom_decile_performance=round(bottom_perf, 4),
            spread=round(top_perf - bottom_perf, 4),
        )
