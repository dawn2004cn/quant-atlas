from __future__ import annotations
"""Hedge Fund Agent Base Classes."""


from dataclasses import dataclass, field
from typing import Any
from enum import Enum


@dataclass
class AgentSignal:
    """Signal output from a hedge fund agent."""

    agent_id: str
    agent_name: str
    style: str
    signal: str
    confidence: float
    reasoning: str
    details: dict[str, Any] = field(default_factory=dict)


class SignalType(str, Enum):
    """Types of trading signals."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class AgentAnalysisContext:
    """Context passed to agents for analysis."""

    symbol: str
    market: str
    end_date: str
    start_date: str
    financial_metrics: list[dict] = field(default_factory=list)
    line_items: list[dict] = field(default_factory=list)
    prices: list[dict] = field(default_factory=list)
    news: list[dict] = field(default_factory=list)
    insider_trades: list[dict] = field(default_factory=list)
    market_cap: float | None = None


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    agent_id: str
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""
    include_reasoning: bool = True


class BaseHedgeFundAgent:
    """Base class for all hedge fund agents."""

    def __init__(self, config: AgentConfig):
        self.config = config

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    def analyze(self, context: AgentAnalysisContext) -> AgentSignal:
        """Run agent analysis. Must be implemented by subclasses."""
        raise NotImplementedError

    def get_system_prompt(self) -> str:
        """Get the agent's system prompt. Override in subclasses."""
        return self.config.system_prompt

    def get_style_prompt(self) -> str:
        """Get style-specific prompt. Override in subclasses."""
        return ""


__all__ = [
    "AgentSignal",
    "SignalType",
    "AgentAnalysisContext",
    "AgentConfig",
    "BaseHedgeFundAgent",
]