"""3D Portfolio Resonance Field — Phase 18.2.
Three.js particle visualization: portfolio holdings as energy particles.
Related stocks attract (red ripple = crowding warning), uncorrelated stocks repel."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResonanceParticle:
    """A single portfolio holding represented as an energy particle."""
    symbol: str
    name: str
    weight: float  # portfolio weight 0..1
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    energy: float = 0.5  # particle energy level
    color: str = "#00ff88"  # hex color
    correlation_pairs: list[dict] = field(default_factory=list)  # [{symbol, corr, ripple}]


@dataclass
class ResonanceFieldState:
    """Full 3D field state for rendering."""
    particles: list[ResonanceParticle] = field(default_factory=list)
    crowding_warnings: list[dict] = field(default_factory=list)
    diversity_score: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PortfolioResonanceFieldService:
    """Generates 3D particle field data for portfolio visualization."""

    def __init__(self, neural_mesh=None):
        self._mesh = neural_mesh
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "resonance_fields.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def compute_field(self, holdings: list[dict], regime: str = "bull") -> ResonanceFieldState:
        """Compute 3D particle positions and interactions from portfolio holdings."""
        n = len(holdings)
        if n == 0:
            return ResonanceFieldState()

        particles = []
        crowding_warnings = []

        # Golden-angle spiral layout for initial positions
        golden_angle = math.pi * (3 - math.sqrt(5))
        for i, holding in enumerate(holdings):
            y = 1 - (i / (n - 1 or 1)) * 2  # -1 to 1
            radius = math.sqrt(1 - y * y)
            theta = golden_angle * i
            x = math.cos(theta) * radius
            z = math.sin(theta) * radius

            weight = float(holding.get("weight", 0.05))
            energy = weight * 2  # heavier = more energetic

            particle = ResonanceParticle(
                symbol=str(holding.get("symbol", "")),
                name=str(holding.get("name", "")),
                weight=weight,
                x=x, y=y, z=z,
                energy=min(1.0, energy),
                color=_weight_to_color(weight),
            )
            particles.append(particle)

        # Compute pairwise correlations and interactions
        for i, p_a in enumerate(particles):
            for j, p_b in enumerate(particles):
                if j <= i:
                    continue
                # Simulate correlation (real impl would use NeuralFeatureMesh)
                corr = self._estimate_correlation(p_a.symbol, p_b.symbol)
                ripple = "red" if abs(corr) > 0.8 else "blue" if abs(corr) > 0.5 else "green"
                p_a.correlation_pairs.append({
                    "symbol": p_b.symbol,
                    "correlation": round(corr, 3),
                    "ripple": ripple,
                })
                if abs(corr) > 0.8:
                    crowding_warnings.append({
                        "symbol_a": p_a.symbol,
                        "symbol_b": p_b.symbol,
                        "correlation": round(corr, 3),
                        "message": f"{p_a.symbol} 与 {p_b.symbol} 高度相关 ({corr:.0%})，建议分散",
                    })

        diversity = self._compute_diversity(particles)
        state = ResonanceFieldState(
            particles=particles,
            crowding_warnings=crowding_warnings[:5],
            diversity_score=round(diversity, 4),
        )
        self._persist(state)
        return state

    def _estimate_correlation(self, symbol_a: str, symbol_b: str) -> float:
        """Estimate correlation between two symbols."""
        if self._mesh and hasattr(self._mesh, "_correlation_cache"):
            key = tuple(sorted([symbol_a, symbol_b]))
            cached = self._mesh._correlation_cache.get(key)
            if cached is not None:
                return cached / 100.0  # convert from pct
        # Fallback: hash-based deterministic pseudo-correlation
        h = hash(symbol_a + symbol_b) % 1000
        return (h / 1000.0) * 2 - 1  # -1 to 1

    def _compute_diversity(self, particles: list[ResonanceParticle]) -> float:
        """Compute portfolio diversity score from correlation pairs."""
        if not particles:
            return 0.0
        total_corr = 0.0
        count = 0
        for p in particles:
            for pair in p.correlation_pairs:
                total_corr += abs(pair["correlation"])
                count += 1
        avg_corr = total_corr / max(count, 1)
        return 1.0 - avg_corr  # 0 = all correlated, 1 = all diverse

    def _persist(self, state: ResonanceFieldState) -> None:
        try:
            with self._store.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "timestamp": state.last_updated,
                    "particle_count": len(state.particles),
                    "crowding_warnings": state.crowding_warnings,
                    "diversity_score": state.diversity_score,
                }) + "\n")
        except Exception as exc:
            logger.warning("Resonance field persist failed: %s", exc)


def _weight_to_color(weight: float) -> str:
    """Map portfolio weight to particle color."""
    if weight > 0.2:
        return "#ff4444"  # heavy = red
    if weight > 0.1:
        return "#ff8800"  # medium = orange
    if weight > 0.05:
        return "#00ff88"  # light = green
    return "#4488ff"  # tiny = blue
