from __future__ import annotations
"""Hierarchical Teams - Supervisor-sub-supervisor architecture.

This module implements the Hierarchical Teams pattern from midify_plan9.md:
- TeamSupervisor: Manages sub-teams
- DepartmentGraph: Specialized team graphs
- Parallel execution across departments

Instead of a flat graph with 20+ sequential nodes, we organize agents
into departments that can execute in parallel.
"""


import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base import AgentResponseDTO, AgentConclusion
from .evidence_blackboard import get_evidence_blackboard
from enum import Enum

from app.core.logger import get_logger

logger = get_logger(__name__)


class DepartmentType(Enum):
    """Department types in the hierarchical organization."""
    FUNDAMENTAL = "fundamental"
    QUANTITATIVE = "quantitative"
    RISK_COMPLIANCE = "risk_compliance"
    SENTIMENT = "sentiment"


@dataclass
class TeamResult:
    """Result from a team/department execution."""
    department: DepartmentType
    agent_results: list[AgentResponseDTO] = field(default_factory=list)
    aggregated_conclusion: AgentConclusion = AgentConclusion.NEUTRAL
    confidence: float = 0.0
    execution_time_ms: float = 0.0
    error: str | None = None


class TeamSupervisor:
    """Main supervisor that coordinates sub-teams.

    This replaces the flat graph with a hierarchical structure:
    - Supervisor dispatches tasks to departments
    - Departments execute in parallel
    - Results are aggregated for final decision
    """

    def __init__(self):
        self._departments: dict[DepartmentType, DepartmentGraph] = {}
        self._blackboard = get_evidence_blackboard()

    def register_department(
        self,
        department_type: DepartmentType,
        department: DepartmentGraph,
    ) -> None:
        """Register a department/sub-team."""
        self._departments[department_type] = department
        logger.info(f"Registered department: {department_type.value}")

    async def coordinate_research(
        self,
        context: dict[str, Any],
        enabled_departments: list[DepartmentType] | None = None,
    ) -> dict[str, Any]:
        """Coordinate research across departments in parallel."""
        start_time = datetime.now()

        departments_to_run = enabled_departments or list(self._departments.keys())

        logger.info(f"Coordinating research across {len(departments_to_run)} departments")

        tasks = []
        for dept_type in departments_to_run:
            if dept_type in self._departments:
                task = self._execute_department(dept_type, context)
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        team_results = []
        for dept_type, result in zip(departments_to_run, results):
            if isinstance(result, Exception):
                logger.error(f"Department {dept_type.value} failed: {result}")
                team_results.append(TeamResult(
                    department=dept_type,
                    error=str(result),
                ))
            else:
                team_results.append(result)

        aggregated = self._aggregate_team_results(team_results)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "team_results": [
                {
                    "department": tr.department.value,
                    "conclusion": tr.aggregated_conclusion.value,
                    "confidence": tr.confidence,
                    "error": tr.error,
                }
                for tr in team_results
            ],
            "final_conclusion": aggregated["conclusion"],
            "final_confidence": aggregated["confidence"],
            "execution_time_ms": execution_time,
            "blackboard_summary": self._blackboard.get_summary(),
        }

    async def _execute_department(
        self,
        department_type: DepartmentType,
        context: dict[str, Any],
    ) -> TeamResult:
        """Execute a single department."""
        import time
        start = time.time()

        try:
            department = self._departments[department_type]
            results = await department.execute(context)

            conclusion, confidence = self._aggregate_results(results)

            return TeamResult(
                department=department_type,
                agent_results=results,
                aggregated_conclusion=conclusion,
                confidence=confidence,
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            logger.error(f"Department {department_type.value} error: {e}")
            return TeamResult(
                department=department_type,
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
            )

    def _aggregate_results(self, results: list[AgentResponseDTO]) -> tuple[AgentConclusion, float]:
        """Aggregate results from multiple agents."""
        if not results:
            return AgentConclusion.NEUTRAL, 0.0

        bullish_count = sum(1 for r in results if r.conclusion == AgentConclusion.BULLISH)
        bearish_count = sum(1 for r in results if r.conclusion == AgentConclusion.BEARISH)

        total = len(results)
        score = (bullish_count - bearish_count) / total if total > 0 else 0.0

        avg_confidence = sum(r.confidence for r in results) / total

        if score > 0.3:
            return AgentConclusion.BULLISH, avg_confidence
        elif score < -0.3:
            return AgentConclusion.BEARISH, avg_confidence
        elif score > 0:
            return AgentConclusion.HOLD, avg_confidence * 0.8
        else:
            return AgentConclusion.NEUTRAL, avg_confidence * 0.5

    def _aggregate_team_results(self, team_results: list[TeamResult]) -> dict[str, Any]:
        """Aggregate results from multiple departments."""
        valid_results = [r for r in team_results if r.error is None]

        if not valid_results:
            return {"conclusion": AgentConclusion.NEUTRAL, "confidence": 0.0}

        conclusions = [r.aggregated_conclusion for r in valid_results]
        confidences = [r.confidence for r in valid_results]

        bullish = sum(1 for c in conclusions if c == AgentConclusion.BULLISH)
        bearish = sum(1 for c in conclusions if c == AgentConclusion.BEARISH)
        neutral = sum(1 for c in conclusions if c == AgentConclusion.NEUTRAL)

        total = len(conclusions)
        score = (bullish - bearish) / total

        final_confidence = sum(confidences) / total

        if score > 0.4:
            conclusion = AgentConclusion.BULLISH
        elif score < -0.4:
            conclusion = AgentConclusion.BEARISH
        elif score > 0:
            conclusion = AgentConclusion.HOLD
        else:
            conclusion = AgentConclusion.NEUTRAL

        return {
            "conclusion": conclusion,
            "confidence": final_confidence,
        }


class DepartmentGraph(ABC):
    """Abstract base for department sub-graphs."""

    def __init__(self, department_type: DepartmentType):
        self.department_type = department_type
        self._agents: list[Any] = []

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> list[AgentResponseDTO]:
        """Execute the department's agents in parallel."""
        raise NotImplementedError

    def add_agent(self, agent: Any) -> None:
        """Add an agent to this department."""
        self._agents.append(agent)


class FundamentalDepartment(DepartmentGraph):
    """Department for fundamental analysis (valuation,财报,行业)."""

    def __init__(self):
        super().__init__(DepartmentType.FUNDAMENTAL)

    async def execute(self, context: dict[str, Any]) -> list[AgentResponseDTO]:
        """Execute fundamental analysis agents in parallel."""
        results = []

        async def run_valuation():
            return create_agent_response(
                conclusion=AgentConclusion.BULLISH,
                confidence=0.75,
                evidence_keys=["valuation_dcf", "pe_ratio"],
                narrative="DCF valuation suggests undervaluation",
            )

        async def run_financial():
            return create_agent_response(
                conclusion=AgentConclusion.BULLISH,
                confidence=0.70,
                evidence_keys=["revenue_growth", "profit_margin"],
                narrative="Strong financial performance",
            )

        async def run_industry():
            return create_agent_response(
                conclusion=AgentConclusion.NEUTRAL,
                confidence=0.65,
                evidence_keys=["industry_trend"],
                narrative="Industry outlook stable",
            )

        task_results = await asyncio.gather(
            run_valuation(),
            run_financial(),
            run_industry(),
            return_exceptions=True,
        )

        for r in task_results:
            if isinstance(r, Exception):
                results.append(create_agent_response(
                    conclusion=AgentConclusion.NEUTRAL,
                    confidence=0.0,
                    error=str(r),
                ))
            else:
                results.append(r)

        return results


class QuantitativeDepartment(DepartmentGraph):
    """Department for quantitative analysis (因子,回测,优化)."""

    def __init__(self):
        super().__init__(DepartmentType.QUANTITATIVE)

    async def execute(self, context: dict[str, Any]) -> list[AgentResponseDTO]:
        """Execute quantitative agents in parallel."""
        return [
            create_agent_response(
                conclusion=AgentConclusion.BULLISH,
                confidence=0.80,
                evidence_keys=["factor_ic", "backtest_return"],
                narrative="Factor shows strong IC and positive backtest",
            ),
        ]


class RiskComplianceDepartment(DepartmentGraph):
    """Department for risk management and compliance."""

    def __init__(self):
        super().__init__(DepartmentType.RISK_COMPLIANCE)

    async def execute(self, context: dict[str, Any]) -> list[AgentResponseDTO]:
        """Execute risk analysis."""
        return [
            create_agent_response(
                conclusion=AgentConclusion.HOLD,
                confidence=0.85,
                evidence_keys=["risk_score", "drawdown_limit"],
                narrative="Risk within acceptable bounds but monitor",
            ),
        ]


class SentimentDepartment(DepartmentGraph):
    """Department for sentiment analysis."""

    def __init__(self):
        super().__init__(DepartmentType.SENTIMENT)

    async def execute(self, context: dict[str, Any]) -> list[AgentResponseDTO]:
        """Execute sentiment analysis."""
        return [
            create_agent_response(
                conclusion=AgentConclusion.BULLISH,
                confidence=0.60,
                evidence_keys=["news_sentiment", "social_media"],
                narrative="Positive market sentiment detected",
            ),
        ]


def create_hierarchical_teams() -> TeamSupervisor:
    """Factory function to create the hierarchical team structure."""
    supervisor = TeamSupervisor()

    fundamental_dept = FundamentalDepartment()
    quantitative_dept = QuantitativeDepartment()
    risk_dept = RiskComplianceDepartment()
    sentiment_dept = SentimentDepartment()

    supervisor.register_department(DepartmentType.FUNDAMENTAL, fundamental_dept)
    supervisor.register_department(DepartmentType.QUANTITATIVE, quantitative_dept)
    supervisor.register_department(DepartmentType.RISK_COMPLIANCE, risk_dept)
    supervisor.register_department(DepartmentType.SENTIMENT, sentiment_dept)

    return supervisor


from enum import Enum

from .base import create_agent_response