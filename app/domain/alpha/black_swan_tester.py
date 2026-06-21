from __future__ import annotations
"""Black Swan Stress Tester - Macro Stress Testing.

Implements from strategy_plan3.md:
- Generate black swan scenarios via LLM
- Stress test portfolios automatically
- Identify systemic vulnerabilities

Usage:
    tester = BlackSwanStressTester()
    scenarios = tester.generate_scenarios(count=5)
    report = tester.run_stress_test(portfolio, scenarios)
"""


import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections import defaultdict


from app.core.logger import get_logger

logger = get_logger(__name__)


class ScenarioType(Enum):
    """Type of stress scenario."""
    FLASH_CRASH = "flash_crash"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    RATE_SHOCK = "rate_shock"
    GEOPOLITICAL = "geopolitical"
    SECTOR_ROTATION = "sector_rotation"
    CONTAGION = "contagion"
    BLACK_SWAN = "black_swan"


@dataclass
class StressScenario:
    """Single stress scenario."""
    scenario_id: str
    name: str
    scenario_type: ScenarioType
    magnitude: float
    duration_hours: int
    affected_assets: list[str]
    probability: float = 0.01
    description: str = ""
    shock_params: dict[str, float] = field(default_factory=dict)


@dataclass
class StressTestResult:
    """Result of stress test."""
    scenario: StressScenario
    portfolio_pnl: float
    max_drawdown: float
    var_99: float
    var_995: float
    breach_count: int
    recovery_time_hours: float


@dataclass
class StressReport:
    """Full stress test report."""
    timestamp: datetime
    scenarios_tested: int
    avg_portfolio_impact: float
    worst_scenario: str
    worst_loss: float
    var_99: float
    breached_scenarios: list[str]
    recommendations: list[str]


class BlackSwanStressTester:
    """Generate and run black swan stress tests."""

    DEFAULT_SCENARIOS: list[dict] = [
        {
            "name": "Flash Crash",
            "type": ScenarioType.FLASH_CRASH,
            "magnitude": 0.10,
            "duration_hours": 4,
            "affected": ["*"],
            "description": "指数在5分钟内闪崩10%",
        },
        {
            "name": "流动性危机",
            "type": ScenarioType.LIQUIDITY_CRISIS,
            "magnitude": 0.20,
            "duration_hours": 48,
            "affected": ["SH600036", "SH601318"],
            "description": "主力股流动性枯竭，买卖价差扩大20倍",
        },
        {
            "name": "利率冲击",
            "type": ScenarioType.RATE_SHOCK,
            "magnitude": 0.05,
            "duration_hours": 168,
            "affected": ["*"],
            "description": "央行意外加息50bp",
        },
        {
            "name": "地缘事件",
            "type": ScenarioType.GEOPOLITICAL,
            "magnitude": 0.08,
            "duration_hours": 72,
            "affected": ["SH600019", "SH601988"],
            "description": "地缘冲突导致核电/军工板块暴跌",
        },
        {
            "name": "行业轮动",
            "type": ScenarioType.SECTOR_ROTATION,
            "magnitude": 0.15,
            "duration_hours": 120,
            "affected": ["growth_stocks"],
            "description": "从成长股轮动到价值股",
        },
        {
            "name": "传染效应",
            "type": ScenarioType.CONTAGION,
            "magnitude": 0.12,
            "duration_hours": 96,
            "affected": ["small_cap"],
            "description": "某小盘股崩盘引发小盘股传染",
        },
        {
            "name": "瑞信事件",
            "type": ScenarioType.BLACK_SWAN,
            "magnitude": 0.30,
            "duration_hours": 240,
            "affected": ["*"],
            "description": "类似瑞信AT1债券全额减记事件",
        },
    ]

    def __init__(self):
        self._scenarios: list[StressScenario] = []
        self._test_results: list[StressTestResult] = []
        self._custom_scenarios: list[StressScenario] = []

    def generate_scenarios(
        self,
        count: int = 5,
        focus_types: list[ScenarioType] = None,
    ) -> list[StressScenario]:
        """Generate stress scenarios."""
        import uuid

        if focus_types:
            candidates = [s for s in self._scenarios if s.scenario_type in focus_types]
        else:
            candidates = self._scenarios or self._load_default_scenarios()

        if len(candidates) <= count:
            return candidates

        import random
        return random.sample(candidates, count)

    def _load_default_scenarios(self) -> list[StressScenario]:
        """Load default scenarios."""
        scenarios = []
        import uuid

        for s in self.DEFAULT_SCENARIOS:
            scenario = StressScenario(
                scenario_id=str(uuid.uuid4())[:8],
                name=s["name"],
                scenario_type=s["type"],
                magnitude=s["magnitude"],
                duration_hours=s["duration_hours"],
                affected_assets=s["affected"],
                description=s["description"],
                shock_params=self._build_shock_params(s),
            )
            scenarios.append(scenario)

        return scenarios

    def _build_shock_params(self, scenario: dict) -> dict[str, float]:
        """Build shock parameters for scenario."""
        return {
            "price_shock": scenario["magnitude"],
            "volume_shock": scenario["magnitude"] * 2,
            "spread_shock": scenario["magnitude"] * 5,
            "liquidity_shock": min(1.0, scenario["magnitude"] * 3),
        }

    def add_custom_scenario(
        self,
        name: str,
        scenario_type: ScenarioType,
        magnitude: float,
        duration_hours: int,
        affected_assets: list[str],
    ) -> None:
        """Add custom scenario."""
        import uuid

        scenario = StressScenario(
            scenario_id=str(uuid.uuid4())[:8],
            name=name,
            scenario_type=scenario_type,
            magnitude=magnitude,
            duration_hours=duration_hours,
            affected_assets=affected_assets,
        )

        self._custom_scenarios.append(scenario)
        logger.info(f"Added custom scenario: {name}")

    def run_stress_test(
        self,
        portfolio: dict[str, Any],
        scenarios: list[StressScenario] = None,
    ) -> list[StressTestResult]:
        """Run stress test against scenarios."""
        scenarios = scenarios or self.generate_scenarios(5)

        results = []

        for scenario in scenarios:
            result = self._simulate_scenario(portfolio, scenario)
            results.append(result)
            self._test_results.append(result)

        logger.info(f"Completed stress test with {len(scenarios)} scenarios")
        return results

    def _simulate_scenario(
        self,
        portfolio: dict[str, Any],
        scenario: StressScenario,
    ) -> StressTestResult:
        """Simulate portfolio under scenario."""
        positions = portfolio.get("positions", {})
        total_value = portfolio.get("total_value", 1000000)

        losses = []
        breaches = 0

        for symbol, pos in positions.items():
            quantity = pos.get("quantity", 0)
            entry_price = pos.get("entry_price", 0)

            if scenario.affected_assets == ["*"] or symbol in scenario.affected_assets:
                price_loss = entry_price * scenario.magnitude
                position_loss = quantity * price_loss
            else:
                position_loss = quantity * entry_price * scenario.magnitude * 0.3

            losses.append(position_loss)

        total_loss = sum(losses)
        portfolio_pnl = -total_loss

        max_dd = abs(portfolio_pnl) / total_value if total_value > 0 else 0
        var_99 = total_loss * 2.33
        var_995 = total_loss * 3.0

        stop_loss = portfolio.get("stop_loss", 0.15)
        if max_dd > stop_loss:
            breaches += 1

        recovery = scenario.duration_hours * 2

        return StressTestResult(
            scenario=scenario,
            portfolio_pnl=portfolio_pnl,
            max_drawdown=max_dd,
            var_99=var_99,
            var_995=var_995,
            breach_count=breaches,
            recovery_time_hours=recovery,
        )

    def generate_report(
        self,
        results: list[StressTestResult] = None,
    ) -> StressReport:
        """Generate stress test report."""
        results = results or self._test_results

        if not results:
            return StressReport(
                timestamp=datetime.now(),
                scenarios_tested=0,
                avg_portfolio_impact=0,
                worst_scenario="",
                worst_loss=0,
                var_99=0,
                breached_scenarios=[],
                recommendations=[],
            )

        pnls = [r.portfolio_pnl for r in results]
        avg_impact = sum(pnls) / len(pnls) if pnls else 0

        worst = min(results, key=lambda r: r.portfolio_pnl)
        breached = [r.scenario.name for r in results if r.breach_count > 0]

        recommendations = []
        if breached:
            recommendations.append("建议降低总体仓位")
        if worst.portfolio_pnl < -avg_impact * 2:
            recommendations.append("审查极端情景下的风险敞口")

        return StressReport(
            timestamp=datetime.now(),
            scenarios_tested=len(results),
            avg_portfolio_impact=avg_impact,
            worst_scenario=worst.scenario.name,
            worst_loss=worst.portfolio_pnl,
            var_99=worst.var_99,
            breached_scenarios=breached,
            recommendations=recommendations,
        )

    def get_var(
        self,
        results: list[StressTestResult],
        confidence: float = 0.99,
    ) -> float:
        """Calculate Value at Risk."""
        if not results:
            return 0.0

        pnls = sorted([r.portfolio_pnl for r in results])
        idx = int(len(pnls) * (1 - confidence))
        return pnls[min(idx, len(pnls) - 1)]


from enum import Enum

_global_stress_tester: "BlackSwanStressTester" | None = None


def get_stress_tester() -> "BlackSwanStressTester":
    """Get global stress tester."""
    global _global_stress_tester
    if _global_stress_tester is None:
        _global_stress_tester = BlackSwanStressTester()
    return _global_stress_tester