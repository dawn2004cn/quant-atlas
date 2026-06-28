from __future__ import annotations

"""Agent Workflow DTOs for standardized agent interaction."""


from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Agent type enumeration."""
    BUFFETT = "buffett"
    LYNCH = "lynch"
    WOOD = "wood"
    ACKMAN = "ackman"
    BURRY = "burry"
    DRUCKENMILLER = "druckenmiller"
    TALEB = "taleb"
    RISK_MAN = "risk_man"
    SENTIMENT = "sentiment"
    CUSTOM = "custom"


class AgentSignal(str, Enum):
    """Agent signal enumeration."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    RISK = "risk"


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    id: str
    name: str
    role: str
    avatar: str
    prompt_prefix: str
    weight: float = 0.1
    agent_type: AgentType = AgentType.CUSTOM
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30


class AgentContext(BaseModel):
    """Context passed to agents for analysis."""
    symbol: str
    market: str
    quote: dict[str, Any] = Field(default_factory=dict)
    indicators: dict[str, Any] = Field(default_factory=dict)
    news: list[dict[str, Any]] = Field(default_factory=list)
    additional_data: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Result from a single agent analysis."""
    agent_id: str
    agent_name: str
    agent_role: str
    signal: AgentSignal = AgentSignal.NEUTRAL
    reasoning: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M"))


class WorkflowState(BaseModel):
    """State of an agent workflow."""
    workflow_id: str
    symbol: str
    market: str
    status: str = "pending"
    start_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    end_time: str | None = None
    agent_results: list[AgentResult] = Field(default_factory=list)
    consensus: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class WorkflowConfig(BaseModel):
    """Configuration for agent workflow orchestration."""
    workflow_id: str | None = None
    agents: list[AgentConfig] = Field(default_factory=list)
    max_parallel: int = 6
    enable_consensus: bool = True
    consensus_threshold: float = 0.6
    timeout_seconds: int = 120


class IntentResult(BaseModel):
    """Result from intent parsing."""
    intent: str = "search"
    query: str = ""
    symbol: str | None = None
    market: str = "CN"
    criteria: dict[str, Any] = Field(default_factory=dict)
    original: str = ""
