from __future__ import annotations

"""Dynamic Prompt Engineering - Adaptive prompts based on agent history.

This module implements the Dynamic Prompt Engineering from midify_plan10.md:
- DynamicPromptBuilder: Builds prompts with self-correction reminders
- Agent-specific error patterns: Track what errors each agent makes
- Context-aware prompt injection

Usage:
    builder = DynamicPromptBuilder(agent_name="TechnicalAgent")
    prompt = builder.build_prompt(base_prompt, context)
    # Prompt now includes reminders about past failures
"""


from app.security.prompt_sanitizer import PromptSanitizer

_sanitizer = PromptSanitizer()


from dataclasses import dataclass
from typing import Any

from app.core.logger import get_logger
from app.security.prompt_sanitizer import PromptSanitizer

from .agent_memory import get_agent_memory

_sanitizer = PromptSanitizer()

logger = get_logger(__name__)


@dataclass
class ErrorPattern:
    """Pattern of errors an agent commonly makes."""
    pattern_id: str
    scenario: str
    description: str
    frequency: int = 0
    last_occurred: str | None = None


class DynamicPromptBuilder:
    """Dynamic prompt builder with self-correction capabilities.

    Builds prompts that adapt based on the agent's historical performance,
    injecting relevant reminders about past failures.
    """

    def __init__(self, agent_name: str):
        self._agent_name = agent_name
        self._memory = get_agent_memory()
        self._error_patterns = self._load_error_patterns()

    def _load_meta_learned_patterns(self) -> dict[str, ErrorPattern]:
        """Merge persisted patterns from MetaLearningEngine runs."""
        out: dict[str, ErrorPattern] = {}
        try:
            from app.infrastructure.repositories.file_meta_learning_repository import (
                FileMetaLearningRepository,
            )

            for row in FileMetaLearningRepository().load_patterns():
                pid = str(row.get("pattern_id") or "").strip()
                if not pid:
                    continue
                agent = self._agent_name.lower()
                if agent not in pid.lower() and "auto_" not in pid:
                    continue
                out[pid] = ErrorPattern(
                    pattern_id=pid,
                    scenario=str(row.get("scenario_type") or "general"),
                    description=str(row.get("description") or row.get("avoidance_guide") or "")[:240],
                    frequency=int(row.get("frequency") or 1),
                    last_occurred=str(row.get("discovered_at") or ""),
                )
        except Exception as exc:
            logger.debug("dynamic_prompt meta patterns: %s", exc)
        return out

    def _load_error_patterns(self) -> dict[str, ErrorPattern]:
        """Load known error patterns for the agent."""
        builtin = {
            "volume_spike_false_positive": ErrorPattern(
                pattern_id="volume_spike_false_positive",
                scenario="high_volume_no_price_movement",
                description="False positive on volume spike breakout signals",
            ),
            "overvalued_tech_ignore": ErrorPattern(
                pattern_id="overvalued_tech_ignore",
                scenario="tech_stock_overvaluation",
                description="Ignoring high PE in bullish tech stock analysis",
            ),
            "trend_reversal_late": ErrorPattern(
                pattern_id="trend_reversal_late",
                scenario="trend_reversal",
                description="Late to detect trend reversal signals",
            ),
            "sentiment_contrarian": ErrorPattern(
                pattern_id="sentiment_contrarian",
                scenario="extreme_sentiment",
                description="Failing to recognize contrarian opportunities",
            ),
        }
        learned = self._load_meta_learned_patterns()
        merged = {**builtin, **learned}
        return merged

    def build_prompt(
        self,
        base_prompt: str,
        context: dict[str, Any],
    ) -> str:
        """Build prompt with dynamic self-correction reminders and injection protection."""
        # Sanitize any user-provided input in context
        sanitized_context = {}
        for key, value in context.items():
            if isinstance(value, str):
                sanitized_context[key] = _sanitizer.sanitize(value)
            else:
                sanitized_context[key] = value

        prompt = base_prompt

        performance = self._memory.get_agent_performance(self._agent_name)

        if performance["total_decisions"] == 0:
            return prompt

        failures = self._memory.get_past_failures(self._agent_name, threshold=0.4)

        if failures:
            correction_reminder = self._build_correction_reminder(failures, sanitized_context)
            prompt = f"{prompt}\n\n{correction_reminder}"

        weak_areas = self._identify_weak_areas(performance)
        if weak_areas:
            area_warning = self._build_area_warning(weak_areas)
            prompt = f"{prompt}\n\n{area_warning}"

        return prompt

    def _build_correction_reminder(
        self,
        failures: list,
        context: dict[str, Any],
    ) -> str:
        """Build self-correction reminder based on recent failures."""
        recent_failures = failures[:3]

        reminder = "⚠️ SELF-CORRECTION REMINDER:\n"
        reminder += f"You have made {len(recent_failures)} historically inaccurate decisions recently.\n\n"

        for failure in recent_failures:
            scenario = self._match_error_scenario(failure)
            if scenario:
                reminder += f"- {scenario.description}\n"

        reminder += "\nPlease be extra cautious and verify your analysis with additional evidence.\n"

        return reminder

    def _build_area_warning(self, weak_areas: list[str]) -> str:
        """Build warning about weak areas."""
        warning = "📊 PERFORMANCE WARNING:\n"

        for area in weak_areas:
            warning += f"- In {area} scenarios, your accuracy has been below average.\n"

        warning += "\nConsider consulting other agents or requiring stronger evidence before making recommendations.\n"

        return warning

    def _match_error_scenario(self, failure) -> ErrorPattern | None:
        """Match a failure to known error patterns."""
        content = failure.content.lower()
        outcome = failure.outcome.lower()

        for pattern in self._error_patterns.values():
            if pattern.scenario in content or pattern.scenario in outcome:
                pattern.frequency += 1
                return pattern

        return None

    def _identify_weak_areas(self, performance: dict[str, Any]) -> list[str]:
        """Identify areas where agent performs poorly."""
        weak_areas = []

        recent_failures = self._memory.get_past_failures(self._agent_name, threshold=0.3)
        if len(recent_failures) > 3:
            weak_areas.append("general")

        return weak_areas

    def get_dynamic_system_prompt(
        self,
        agent_role: str,
    ) -> str:
        """Get system prompt with injected dynamic warnings."""
        base_prompts = {
            "technical": "You are a technical analysis expert. Analyze price charts, patterns, and indicators.",
            "fundamental": "You are a fundamental analysis expert. Analyze financial statements, valuations, and business models.",
            "sentiment": "You are a sentiment analysis expert. Analyze news, social media, and market mood.",
            "risk": "You are a risk management expert. Evaluate potential risks and suggest mitigation strategies.",
        }

        base = base_prompts.get(agent_role.lower(), "You are a research analyst.")

        context = {}
        return self.build_prompt(base, context)


class PromptTemplateManager:
    """Manages prompt templates with dynamic variable substitution."""

    def __init__(self):
        self._templates: dict[str, str] = {}

    def register_template(
        self,
        name: str,
        template: str,
        variables: list[str],
    ) -> None:
        """Register a prompt template."""
        self._templates[name] = template

    def render(
        self,
        name: str,
        variables: dict[str, Any],
        dynamic_enhance: bool = True,
    ) -> str:
        """Render a template with variables."""
        if name not in self._templates:
            raise ValueError(f"Template {name} not found")

        template = self._templates[name]

        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))

        if dynamic_enhance:
            if "agent_name" in variables:
                builder = DynamicPromptBuilder(variables["agent_name"])
                # Sanitize all string variables before building prompt
                sanitized_vars = {}
                for k, v in variables.items():
                    if isinstance(v, str):
                        sanitized_vars[k] = _sanitizer.sanitize(v)
                    else:
                        sanitized_vars[k] = v
                rendered = builder.build_prompt(rendered, sanitized_vars)

        return rendered


_global_template_manager = PromptTemplateManager()


def get_template_manager() -> PromptTemplateManager:
    """Get the global template manager."""
    return _global_template_manager
