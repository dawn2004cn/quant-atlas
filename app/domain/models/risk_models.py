from __future__ import annotations

"""Risk domain models and calculators."""


import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class PriceLevel:
    """A horizontal price level (support / resistance / fib)."""

    price: float
    label: str = ""


@dataclass
class RiskMetrics:
    """Aggregated risk view for a position, portfolio, or instrument."""

    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    value_at_risk: float = 0.0
    expected_shortfall: float = 0.0
    concentration_risk: float = 0.0
    max_drawdown: float = 0.0
    warnings: list[str] = field(default_factory=list)
    # From-price-history / equity style
    score: float = 0.0
    level: str = "low"
    beta: float = 1.0

    @classmethod
    def from_price_history(cls, prices: list[float]) -> RiskMetrics:
        if len(prices) < 2:
            return cls(score=10.0, level="low", warnings=[])

        rets = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)) if prices[i - 1]]
        vol = statistics.pstdev(rets) if len(rets) > 1 else 0.0
        # Map volatility to 0–100 score (heuristic)
        score = min(100.0, vol * 800.0 + abs(prices[-1] / prices[0] - 1.0) * 40.0)
        if score < 25:
            level = "low"
        elif score < 50:
            level = "medium"
        elif score < 75:
            level = "high"
        else:
            level = "extreme"

        warnings: list[str] = []
        if vol > 0.03:
            warnings.append("elevated_recent_volatility")

        return cls(score=score, level=level, warnings=warnings, risk_score=score, risk_level=_level_str_to_enum(level))


def _level_str_to_enum(level: str) -> RiskLevel:
    try:
        return RiskLevel(level)
    except ValueError:
        return RiskLevel.MEDIUM


class RiskCalculator:
    """Static helpers used by application and domain services."""

    @staticmethod
    def calculate_position_risk(
        position_value: float,
        portfolio_value: float,
        weight: float,
        volatility: float,
        sector: str = "default",
    ) -> RiskMetrics:
        w = weight if weight <= 1.0 else weight / 100.0
        risk_score = min(
            100.0,
            w * 40.0 + volatility * 120.0 + (0.05 if sector != "consumer" else 0.0) * 10.0,
        )
        if risk_score < 30:
            rl = RiskLevel.LOW
        elif risk_score < 55:
            rl = RiskLevel.MEDIUM
        elif risk_score < 75:
            rl = RiskLevel.HIGH
        else:
            rl = RiskLevel.EXTREME
        var95 = position_value * volatility * 1.65
        return RiskMetrics(
            risk_score=risk_score,
            risk_level=rl,
            value_at_risk=var95,
            score=risk_score,
            level=rl.value,
        )

    @staticmethod
    def calculate_portfolio_risk(
        positions: list[dict[str, Any]],
        total_value: float,
        confidence_level: float = 0.95,
    ) -> RiskMetrics:
        if not positions or total_value <= 0:
            return RiskMetrics(
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                value_at_risk=0.0,
                expected_shortfall=0.0,
                concentration_risk=0.0,
                max_drawdown=0.0,
                warnings=[],
            )

        weights = [float(p.get("weight", 0.0)) for p in positions]
        max_w = max(weights) if weights else 0.0
        vols = [float(p.get("volatility", 0.2)) for p in positions]
        avg_vol = sum(vols) / len(vols) if vols else 0.2

        concentration_risk = max_w
        port_vol = avg_vol * math.sqrt(max(1, len(positions)) / max(len(positions), 1))
        z = 1.65 if confidence_level <= 0.95 else 2.33
        var95 = total_value * port_vol * z / math.sqrt(max(len(positions), 1))
        es = var95 * 1.15
        risk_score = min(100.0, concentration_risk * 80.0 + avg_vol * 60.0)

        if risk_score < 30:
            rl = RiskLevel.LOW
        elif risk_score < 55:
            rl = RiskLevel.MEDIUM
        elif risk_score < 75:
            rl = RiskLevel.HIGH
        else:
            rl = RiskLevel.EXTREME

        warnings: list[str] = []
        if concentration_risk > 0.35:
            warnings.append("concentrated_book")

        return RiskMetrics(
            risk_score=risk_score,
            risk_level=rl,
            value_at_risk=var95,
            expected_shortfall=es,
            concentration_risk=concentration_risk,
            max_drawdown=min(0.5, avg_vol * 1.2),
            warnings=warnings,
            score=risk_score,
            level=rl.value,
        )

    @staticmethod
    def calculate_support_resistance(prices: list[float]) -> dict[str, list[PriceLevel]]:
        if len(prices) < 3:
            return {"support": [], "resistance": []}
        lo = min(prices)
        hi = max(prices)
        mid = (hi + lo) / 2.0
        return {
            "support": [PriceLevel(lo, "swing_low"), PriceLevel(mid * 0.98, "mid")],
            "resistance": [PriceLevel(hi, "swing_high"), PriceLevel(mid * 1.02, "mid")],
        }

    @staticmethod
    def calculate_fibonacci_levels(high: float, low: float) -> list[PriceLevel]:
        span = high - low
        ratios = (0.0, 0.236, 0.382, 0.5, 0.618)
        return [PriceLevel(price=low + span * r, label=f"{r:.1%}") for r in ratios]
