from __future__ import annotations
"""Regime-Adaptive Strategy Switching - Market State Based Parameter Tuning.

This module implements from strategy_plan.md:
- RegimeTemplates: Predefined parameters for each market state
- StressTest: LLM-based extreme scenario simulation
- AutoSwitch: Automatic strategy parameter adjustment

Usage:
    switcher = RegimeStrategySwitcher()
    params = switcher.get_adaptive_params("bear", base_params)
"""


from dataclasses import dataclass
from datetime import datetime
from typing import Any

# NOTE: Previously imported MarketRegime from app.agents.dynamic_personality,
# which created a circular import chain:
#   domain → regime → agents → research → graph → quant_tools →
#   market_data module → application services → core.factory
# MarketRegime was never actually used in this file. If needed later, use
# TYPE_CHECKING guard or resolve the agent dependency properly.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RegimeParameters:
    """Strategy parameters for a specific regime."""
    regime: str
    stoploss: float
    risk_per_trade: float
    position_size: float
    max_positions: int
    factor_weights: dict[str, float]


@dataclass
class StressTestResult:
    """Result of stress test simulation."""
    scenario_name: str
    max_drawdown: float
    portfolio_value_change: float
    trigger_stoploss: bool
    survival_probability: float
    recommendations: list[str]


class RegimeTemplate:
    """Predefined regime templates for strategy parameters."""

    BULL = RegimeParameters(
        regime="bull",
        stoploss=-0.10,
        risk_per_trade=0.02,
        position_size=0.2,
        max_positions=8,
        factor_weights={
            "momentum": 0.4,
            "growth": 0.3,
            "value": 0.2,
            "quality": 0.1,
        },
    )

    BEAR = RegimeParameters(
        regime="bear",
        stoploss=-0.02,
        risk_per_trade=0.01,
        position_size=0.1,
        max_positions=3,
        factor_weights={
            "value": 0.4,
            "quality": 0.3,
            "dividend": 0.2,
            "momentum": 0.1,
        },
    )

    HIGH_VOLATILITY = RegimeParameters(
        regime="high_volatility",
        stoploss=-0.05,
        risk_per_trade=0.015,
        position_size=0.15,
        max_positions=5,
        factor_weights={
            "low_volatility": 0.4,
            "quality": 0.3,
            "momentum": 0.2,
            "mean_reversion": 0.1,
        },
    )

    NEUTRAL = RegimeParameters(
        regime="neutral",
        stoploss=-0.07,
        risk_per_trade=0.02,
        position_size=0.18,
        max_positions=6,
        factor_weights={
            "momentum": 0.25,
            "value": 0.25,
            "growth": 0.25,
            "quality": 0.25,
        },
    )

    @classmethod
    def get_template(cls, regime: str) -> RegimeParameters:
        """Get template for specific regime."""
        templates = {
            "bull": cls.BULL,
            "bear": cls.BEAR,
            "high_volatility": cls.HIGH_VOLATILITY,
            "low_volatility": cls.NEUTRAL,
            "neutral": cls.NEUTRAL,
        }
        return templates.get(regime, cls.NEUTRAL)


class RegimeStrategySwitcher:
    """Switch strategy parameters based on market regime."""

    def __init__(self):
        self._templates = RegimeTemplate()
        self._custom_templates: dict[str, RegimeParameters] = {}
        self._history: list[dict[str, Any]] = []

    def register_template(self, regime: str, params: RegimeParameters) -> None:
        """Register custom template for regime."""
        self._custom_templates[regime] = params

    def get_adaptive_params(
        self,
        regime: str,
        base_params: dict[str, Any],
    ) -> dict[str, Any]:
        """Get adaptive parameters based on regime."""
        template = self._custom_templates.get(regime) or self._templates.get_template(regime)

        adapted = base_params.copy()
        adapted["stoploss"] = template.stoploss
        adapted["risk_per_trade"] = template.risk_per_trade
        adapted["position_size"] = template.position_size
        adapted["max_positions"] = template.max_positions

        if "factor_weights" in base_params:
            for factor, weight in template.factor_weights.items():
                if factor in base_params["factor_weights"]:
                    base_params["factor_weights"][factor] = weight

        self._history.append({
            "timestamp": datetime.now(),
            "regime": regime,
            "params": adapted,
        })

        logger.info(f"Adapted params for regime: {regime}")
        return adapted


class StressTestSimulator:
    """Simulate extreme market scenarios for stress testing."""

    SCENARIOS = {
        "2008_crisis": {
            "price_drop": 0.50,
            "volatility_spike": 3.0,
            "liquidity_shock": True,
        },
        "2020_crash": {
            "price_drop": 0.30,
            "volatility_spike": 2.5,
            "liquidity_shock": True,
        },
        "liquidity_dry": {
            "price_drop": 0.20,
            "volatility_spike": 1.5,
            "liquidity_shock": True,
        },
        "high_inflation": {
            "price_drop": 0.25,
            "volatility_spike": 1.8,
            "liquidity_shock": False,
        },
    }

    def run_stress_test(
        self,
        portfolio_value: float,
        positions: list[dict[str, Any]],
        scenario: str = "2008_crisis",
    ) -> StressTestResult:
        """Run stress test for given scenario."""
        scenario_params = self.SCENARIOS.get(scenario, self.SCENARIOS["2008_crisis"])

        total_exposure = sum(p.get("weight", 0) for p in positions)
        price_impact = scenario_params["price_drop"]

        portfolio_change = -(portfolio_value * total_exposure * price_impact)
        new_value = portfolio_value + portfolio_change

        drawdown = (portfolio_value - new_value) / portfolio_value

        trigger_stoploss = drawdown > 0.05
        survival_prob = 1.0 - min(1.0, drawdown / 0.5)

        recommendations = []
        if drawdown > 0.3:
            recommendations.append("建议大幅降仓或清仓")
        if scenario_params["liquidity_shock"]:
            recommendations.append("增加现金储备以应对流动性风险")
        if scenario_params["volatility_spike"] > 2.0:
            recommendations.append("增加波动率对冲")

        return StressTestResult(
            scenario_name=scenario,
            max_drawdown=drawdown,
            portfolio_value_change=portfolio_change,
            trigger_stoploss=trigger_stoploss,
            survival_probability=survival_prob,
            recommendations=recommendations,
        )

    def run_all_scenarios(
        self,
        portfolio_value: float,
        positions: list[dict[str, Any]],
    ) -> list[StressTestResult]:
        """Run all predefined scenarios."""
        results = []
        for scenario_name in self.SCENARIOS:
            result = self.run_stress_test(portfolio_value, positions, scenario_name)
            results.append(result)
        return results


class RegimeAwarePortfolioManager:
    """Complete regime-aware portfolio management."""

    def __init__(
        self,
        switcher: RegimeStrategySwitcher | None = None,
        stress_tester: StressTestSimulator | None = None,
    ):
        self._switcher = switcher or RegimeStrategySwitcher()
        self._stress_tester = stress_tester or StressTestSimulator()

    def adjust_for_regime(
        self,
        current_regime: str,
        current_params: dict[str, Any],
    ) -> dict[str, Any]:
        """Adjust portfolio parameters for current regime."""
        return self._switcher.get_adaptive_params(current_regime, current_params)

    def validate_regime_switch(
        self,
        portfolio_value: float,
        positions: list[dict[str, Any]],
        target_regime: str,
    ) -> dict[str, Any]:
        """Validate regime switch with stress test."""
        test_results = self._stress_tester.run_all_scenarios(portfolio_value, positions)

        avg_survival = sum(r.survival_probability for r in test_results) / len(test_results)

        return {
            "can_switch": avg_survival > 0.5,
            "stress_test_results": [
                {"scenario": r.scenario_name, "drawdown": r.max_drawdown}
                for r in test_results
            ],
            "avg_survival_rate": avg_survival,
        }


_global_regime_manager: RegimeAwarePortfolioManager | None = None


def get_regime_portfolio_manager() -> RegimeAwarePortfolioManager:
    """Get singleton regime portfolio manager."""
    global _global_regime_manager
    if _global_regime_manager is None:
        _global_regime_manager = RegimeAwarePortfolioManager()
    return _global_regime_manager
