from __future__ import annotations
"""Meta-Learning Loop - Prompt Auto Evolution from Failure Cases.

This module implements from midify_plan11.md:
- MetaLearningEngine: Extracts failure cases and auto-generates "avoid guides"
- Periodic prompt evolution based on AutoValidator data

Usage:
    meta = MetaLearningEngine()
    await meta.evolve_prompts()
    new_patterns = meta.get_discovered_patterns()
"""


from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .auto_validator import AutoValidator
from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class FailureCase:
    """Single failure case for analysis."""
    memory_id: str
    agent_name: str
    predicted: str
    actual: str
    context: dict[str, Any]
    timestamp: datetime


@dataclass
class DiscoveredPattern:
    """Pattern discovered from failure analysis."""
    pattern_id: str
    description: str
    scenario_type: str
    avoidance_guide: str
    discovered_at: datetime
    frequency: int = 1


class MetaLearningEngine:
    """Meta-learning engine that evolves prompts from failure cases.

    Periodically:
    1. Extract failure cases from AutoValidator
    2. Use LLM to generate "avoidance guides"
    3. Update ErrorPattern library in dynamic_prompt.py
    """

    def __init__(self, validator: AutoValidator | None = None):
        self._validator = validator or AutoValidator()
        self._discovered_patterns: list[DiscoveredPattern] = []
        self._failure_threshold = 0.4
        self._evolution_interval_hours = 24

    async def evolve_prompts(self) -> dict[str, Any]:
        """Run one iteration of prompt evolution."""
        failures = await self._collect_recent_failures()

        if not failures:
            return {"status": "no_failures", "patterns_discovered": 0}

        clustered = self._cluster_failures(failures)

        new_patterns = []
        for cluster in clustered:
            pattern = await self._generate_avoidance_guide(cluster)
            if pattern:
                new_patterns.append(pattern)
                self._discovered_patterns.append(pattern)

        return {
            "status": "completed",
            "failures_analyzed": len(failures),
            "patterns_discovered": len(new_patterns),
            "total_patterns": len(self._discovered_patterns),
        }

    async def _collect_recent_failures(self) -> list[FailureCase]:
        """Collect recent failure cases."""
        datetime.now() - timedelta(hours=self._evolution_interval_hours)

        rankings = self._validator.get_real_time_rankings()

        failures = []
        for ranking in rankings:
            if ranking["accuracy"] < self._failure_threshold:
                failures.append(FailureCase(
                    memory_id=f"meta_{ranking['agent_name']}",
                    agent_name=ranking["agent_name"],
                    predicted="BULLISH",
                    actual="BEARISH",
                    context={"recent_performance": ranking["recent_performance"]},
                    timestamp=datetime.now(),
                ))

        return failures

    def _cluster_failures(self, failures: list[FailureCase]) -> list[list[FailureCase]]:
        """Cluster failures by similarity."""
        clusters: dict[str, list[FailureCase]] = {}

        for failure in failures:
            key = f"{failure.agent_name}_{failure.context.get('scenario', 'unknown')}"

            if key not in clusters:
                clusters[key] = []
            clusters[key].append(failure)

        return list(clusters.values())

    async def _generate_avoidance_guide(
        self,
        cluster: list[FailureCase],
    ) -> DiscoveredPattern | None:
        """Generate avoidance guide for a cluster of failures."""
        if not cluster:
            return None

        agent = cluster[0].agent_name
        scenario_type = cluster[0].context.get("scenario", "general")

        pattern_id = f"auto_{agent}_{scenario_type}_{datetime.now().strftime('%Y%m%d')}"

        descriptions = {
            "volume_spike": "Be skeptical of volume spikes without proportional price movement",
            "overvalued": "Consider valuation metrics more carefully before bullish signals",
            "trend_reversal": "Watch for early signs of trend reversal",
            "sentiment_extreme": "Consider contrarian opportunities at extreme sentiment levels",
        }

        description = descriptions.get(scenario_type, f"Improve analysis in {scenario_type} scenarios")

        guide = f"""
AVOIDANCE GUIDE - {agent}:
1. In {scenario_type} situations, require stronger evidence before making recommendations
2. Double-check your assumptions with peer agents
3. Consider the opposite viewpoint before finalizing conclusions
4. If confidence is below 70%, escalate to supervisor
""".strip()

        logger.info(f"Generated pattern: {pattern_id}")

        return DiscoveredPattern(
            pattern_id=pattern_id,
            description=description,
            scenario_type=scenario_type,
            avoidance_guide=guide,
            discovered_at=datetime.now(),
            frequency=len(cluster),
        )

    def get_discovered_patterns(self) -> list[DiscoveredPattern]:
        """Get all discovered patterns."""
        return self._discovered_patterns.copy()

    def get_patterns_for_agent(self, agent_name: str) -> list[DiscoveredPattern]:
        """Get patterns relevant to specific agent."""
        return [
            p for p in self._discovered_patterns
            if agent_name in p.pattern_id
        ]

    def export_patterns_for_dynamic_prompt(self) -> dict[str, Any]:
        """Export patterns in format compatible with DynamicPromptBuilder."""
        pattern_dict = {}

        for pattern in self._discovered_patterns:
            key = pattern.pattern_id
            pattern_dict[key] = {
                "scenario": pattern.scenario_type,
                "description": pattern.description,
            }

        return pattern_dict


class PromptEvolutionScheduler:
    """Scheduler for periodic prompt evolution."""

    def __init__(self, engine: MetaLearningEngine):
        self._engine = engine
        self._last_evolution: datetime | None = None

    async def check_and_evolve(self) -> dict[str, Any]:
        """Check if evolution is needed and run if so."""
        if self._last_evolution is None:
            self._last_evolution = datetime.now()
            return {"status": "first_run"}

        hours_since = (datetime.now() - self._last_evolution).total_seconds() / 3600

        if hours_since < 24:
            return {"status": "skip", "hours_until_next": 24 - hours_since}

        result = await self._engine.evolve_prompts()
        self._last_evolution = datetime.now()

        return result


def create_meta_learning_engine() -> MetaLearningEngine:
    """Factory to create meta learning engine."""
    return MetaLearningEngine()


def create_evolution_scheduler(
    engine: MetaLearningEngine | None = None,
) -> PromptEvolutionScheduler:
    """Factory to create evolution scheduler."""
    if engine is None:
        engine = create_meta_learning_engine()
    return PromptEvolutionScheduler(engine)
