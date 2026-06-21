"""Centralized prompt template registry.

Replaces scattered hardcoded system prompts across the codebase
with a pluggable, domain-organized template system.

Usage:
    from app.core.prompts import get_prompt
    prompt = get_prompt("kline", symbol="600519", interval="日线")
    response = await ai.chat(prompt.text, system_prompt=prompt.system)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptTemplate:
    """A domain-specific prompt with system instruction + formatting."""
    domain: str
    system: str
    template: str = ""
    variables: list[str] = field(default_factory=list)

    def format(self, **kwargs: Any) -> str:
        if not self.template:
            return ""
        return self.template.format(**kwargs)


class PromptRegistry:
    """Registry of domain-specific prompt templates."""

    def __init__(self):
        self._templates: dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.domain] = template

    def get(self, domain: str) -> PromptTemplate | None:
        return self._templates.get(domain)

    def list_domains(self) -> list[str]:
        return list(self._templates.keys())


_registry: PromptRegistry | None = None


def get_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
        _register_defaults(_registry)
    return _registry


def get_prompt(domain: str, **kwargs: Any) -> PromptTemplate | None:
    reg = get_registry()
    tmpl = reg.get(domain)
    return tmpl


def _register_defaults(reg: PromptRegistry) -> None:
    from .kline import KLINE_TEMPLATE, KLINE_IMAGE_TEMPLATE
    from .market import MARKET_TEMPLATE
    from .chart import CHART_ANALYSIS_TEMPLATE
    reg.register(KLINE_TEMPLATE)
    reg.register(KLINE_IMAGE_TEMPLATE)
    reg.register(MARKET_TEMPLATE)
    reg.register(CHART_ANALYSIS_TEMPLATE)