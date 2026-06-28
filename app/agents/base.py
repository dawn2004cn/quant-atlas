from __future__ import annotations
"""Unified Agent Contract - Base classes and DTOs for all agents.

This module implements the Unified Agent Contract from midify_plan9.md:
- BaseAgent: Abstract base class for all agents
- AgentResponseDTO: Standardized response format
- Evidence integration with blackboard

This replaces the previous dict-based approaches and eliminates
hasattr() checks.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.logger import get_logger
logger = get_logger(__name__)

# Import blackboard utilities once at module load to avoid repeated imports
from .evidence_blackboard import (
    get_evidence_blackboard,
    EvidenceType,
    EvidenceStrength,
)


class AgentType(Enum):
    """Classification of agent types."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    TRADING = "trading"
    RISK = "risk"
    EXECUTION = "execution"


class AgentConclusion(Enum):
    """Standard conclusion values for all agents."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    HOLD = "HOLD"


@dataclass
class AgentResponseDTO:
    """Unified response DTO for all agents.

    This is the standard contract that eliminates dict.get() calls
    and provides structured evidence references.
    """
    conclusion: AgentConclusion
    confidence: float
    evidence_keys: list[str] = field(default_factory=list)
    narrative: str = ""
    agent_type: AgentType = AgentType.RESEARCH
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self):
        if isinstance(self.conclusion, str):
            self.conclusion = AgentConclusion(self.conclusion)

        self.confidence = max(0.0, min(1.0, self.confidence))

    @property
    def is_successful(self) -> bool:
        """Check if the agent execution was successful."""
        return self.error is None

    @property
    def is_actionable(self) -> bool:
        """Check if the conclusion is actionable (not NEUTRAL)."""
        return self.conclusion in [AgentConclusion.BULLISH, AgentConclusion.BEARISH]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conclusion": self.conclusion.value,
            "confidence": self.confidence,
            "evidence_keys": self.evidence_keys,
            "narrative": self.narrative,
            "agent_type": self.agent_type.value,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
            "error": self.error,
        }


class BaseAgent(ABC):
    """Abstract base class for all agents.

    All agents should inherit from this class to ensure
    consistent interface and integration with the blackboard.
    """

    def __init__(self, name: str, agent_type: AgentType):
        self.name = name
        self.agent_type = agent_type

    @abstractmethod
    def analyze(self, context: dict[str, Any]) -> AgentResponseDTO:
        """Execute agent analysis and return standardized response.

        Args:
            context: Input context with data for analysis

        Returns:
            AgentResponseDTO with conclusion, confidence, and evidence
        """
        raise NotImplementedError

    def write_evidence(
        self,
        key: str,
        value: Any,
        evidence_type: Any = None,
        strength: Any = None,
        narrative: str = "",
    ) -> None:
        """Write evidence to the blackboard.

        This is a convenience method for agents to contribute
        structured evidence to the shared blackboard.
        """

        bb = get_evidence_blackboard()
        bb.write(
            agent_name=self.name,
            key=key,
            value=value,
            evidence_type=evidence_type or EvidenceType.QUALITATIVE,
            strength=strength or EvidenceStrength.MODERATE,
            narrative=narrative,
        )

    def read_evidence(self, agent_name: str, key: str) -> Any:
        """Read evidence from another agent."""
        from .evidence_blackboard import get_evidence_blackboard

        bb = get_evidence_blackboard()
        return bb.read_value(agent_name, key)


class ResearchAgent(BaseAgent):
    """Base class for research-type agents."""

    def __init__(self, name: str):
        super().__init__(name, AgentType.RESEARCH)

    def analyze(self, context: dict[str, Any]) -> AgentResponseDTO:
        """Execute research analysis on the given context."""
        import time
        start = time.perf_counter()

        symbol = context.get("symbol", "")
        market = context.get("market", "CN")
        focus = context.get("focus", "fundamental")

        self.write_evidence(
            key="research_scope",
            value={"symbol": symbol, "focus": focus, "market": market},
            evidence_type="QUALITATIVE",
            strength="MODERATE",
        )

        narrative = f"对 {symbol} 进行{focus}研究分析，市场: {market}。"
        metadata = {
            "symbol": symbol,
            "market": market,
            "focus": focus,
        }

        return create_agent_response(
            conclusion=AgentConclusion.NEUTRAL,
            confidence=0.5,
            evidence_keys=["research_scope"],
            narrative=narrative,
            agent_type=self.agent_type,
            execution_time_ms=(time.perf_counter() - start) * 1000,
            metadata=metadata,
        )


class AnalysisAgent(BaseAgent):
    """Base class for analysis-type agents."""

    def __init__(self, name: str):
        super().__init__(name, AgentType.ANALYSIS)

    def analyze(self, context: dict[str, Any]) -> AgentResponseDTO:
        """Execute data analysis on the given context."""
        import time
        start = time.perf_counter()

        data = context.get("data", {})
        analysis_type = context.get("type", "technical")

        self.write_evidence(
            key="analysis_data",
            value={"type": analysis_type, "data_keys": list(data.keys()) if data else []},
            evidence_type="QUANTITATIVE",
            strength="MODERATE",
        )

        result = self._perform_analysis(data, analysis_type)

        return create_agent_response(
            conclusion=result.get("conclusion", AgentConclusion.NEUTRAL),
            confidence=result.get("confidence", 0.5),
            evidence_keys=["analysis_data"],
            narrative=result.get("narrative", "分析完成"),
            agent_type=self.agent_type,
            execution_time_ms=(time.perf_counter() - start) * 1000,
            metadata={"analysis_type": analysis_type},
        )

    def _perform_analysis(self, data: dict[str, Any], analysis_type: str) -> dict[str, Any]:
        """Subclass should override with specific analysis logic."""
        if analysis_type == "technical":
            return {"conclusion": AgentConclusion.NEUTRAL, "confidence": 0.5, "narrative": "技术分析完成"}
        elif analysis_type == "fundamental":
            return {"conclusion": AgentConclusion.HOLD, "confidence": 0.5, "narrative": "基本面分析完成"}
        return {"conclusion": AgentConclusion.NEUTRAL, "confidence": 0.4, "narrative": "分析完成"}


class TradingAgent(BaseAgent):
    """Base class for trading-type agents."""

    def __init__(self, name: str):
        super().__init__(name, AgentType.TRADING)

    def analyze(self, context: dict[str, Any]) -> AgentResponseDTO:
        """Execute trading analysis on the given context."""
        import time
        start = time.perf_counter()

        symbol = context.get("symbol", "")
        action = context.get("action", "analyze")
        price = context.get("price", 0)
        quantity = context.get("quantity", 0)

        self.write_evidence(
            key="trade_context",
            value={"symbol": symbol, "action": action, "price": price, "quantity": quantity},
            evidence_type="QUALITATIVE",
            strength="STRONG",
        )

        conclusion = self._determine_conclusion(context)

        return create_agent_response(
            conclusion=conclusion,
            confidence=0.6,
            evidence_keys=["trade_context"],
            narrative=f"交易决策: {action} {symbol} @ {price} x {quantity}",
            agent_type=self.agent_type,
            execution_time_ms=(time.perf_counter() - start) * 1000,
            metadata={"action": action, "symbol": symbol, "price": price, "quantity": quantity},
        )

    def _determine_conclusion(self, context: dict[str, Any]) -> AgentConclusion:
        """Determine trading conclusion based on context."""
        action = context.get("action", "")
        if action in ("buy", "long"):
            return AgentConclusion.BULLISH
        elif action in ("sell", "short"):
            return AgentConclusion.BEARISH
        return AgentConclusion.HOLD


class RiskAgent(BaseAgent):
    """Base class for risk-type agents."""

    def __init__(self, name: str):
        super().__init__(name, AgentType.RISK)

    def analyze(self, context: dict[str, Any]) -> AgentResponseDTO:
        """Execute risk analysis on the given context."""
        import time
        start = time.perf_counter()

        portfolio = context.get("portfolio", {})
        positions = context.get("positions", [])
        max_risk = context.get("max_risk_tolerance", 0.2)

        self.write_evidence(
            key="risk_assessment",
            value={"positions_count": len(positions), "max_risk": max_risk},
            evidence_type="QUANTITATIVE",
            strength="STRONG",
        )

        risk_score = self._calculate_risk(portfolio, positions)

        conclusion = AgentConclusion.BEARISH if risk_score > max_risk else AgentConclusion.NEUTRAL
        narrative = f"风险评估: 组合风险得分 {risk_score:.1%}, 阈值 {max_risk:.1%}"

        return create_agent_response(
            conclusion=conclusion,
            confidence=0.8,
            evidence_keys=["risk_assessment"],
            narrative=narrative,
            agent_type=self.agent_type,
            execution_time_ms=(time.perf_counter() - start) * 1000,
            metadata={"risk_score": risk_score, "max_risk": max_risk, "positions": len(positions)},
        )

    def _calculate_risk(self, portfolio: dict[str, Any], positions: list[dict[str, Any]]) -> float:
        """Calculate overall portfolio risk score."""
        if not positions:
            return 0.0
        total_weight = sum(p.get("weight", 0) for p in positions)
        vol_weight = sum(p.get("weight", 0) * p.get("volatility", 0.2) for p in positions)
        return min(1.0, vol_weight / max(total_weight, 0.01) if total_weight > 0 else 0.2)


def create_agent_response(
    conclusion: str | AgentConclusion,
    confidence: float,
    evidence_keys: list[str] | None = None,
    narrative: str = "",
    agent_type: AgentType = AgentType.RESEARCH,
    execution_time_ms: float = 0.0,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> AgentResponseDTO:
    """Factory function to create standardized agent responses.

    This eliminates the need for dict.get() calls and provides
    consistent interface across all agents.
    """
    return AgentResponseDTO(
        conclusion=conclusion,
        confidence=confidence,
        evidence_keys=evidence_keys or [],
        narrative=narrative,
        agent_type=agent_type,
        execution_time_ms=execution_time_ms,
        metadata=metadata or {},
        error=error,
    )


def conclusion_from_signal(signal: str) -> AgentConclusion:
    """Convert common signal strings to AgentConclusion."""
    signal_lower = signal.lower()

    if "buy" in signal_lower or "bullish" in signal_lower:
        return AgentConclusion.BULLISH
    elif "sell" in signal_lower or "bearish" in signal_lower:
        return AgentConclusion.BEARISH
    elif "hold" in signal_lower:
        return AgentConclusion.HOLD

    return AgentConclusion.NEUTRAL
