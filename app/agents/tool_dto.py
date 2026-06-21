from __future__ import annotations
"""Agent Tool Result DTO - Standardized Tool Output Format.

This module implements from midify_plan11.md:
- AgentToolResult: Structured DTO for tool outputs
- ToolResultBuilder: Builder for creating tool results
- Eliminates json deserialization overhead in knowledge_intermediary

Usage:
    result = AgentToolResult(
        tool_name="get_stock_price",
        success=True,
        data={"price": 150.0, "change": 2.5},
        evidence_points=["price_up_2pct"],
    )
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EvidencePoint:
    """Single evidence point from tool result."""
    key: str
    value: Any
    strength: str = "medium"
    source: str = ""


@dataclass
class AgentToolResult:
    """Standardized tool result DTO.

    Replaces dict-based tool outputs with structured objects.
    Reduces deserialization overhead in knowledge_intermediary.
    """

    tool_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    evidence_points: list[EvidencePoint] = field(default_factory=list)
    error: str | None = None
    execution_time_ms: float = 0.0
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_evidence_keys(self) -> list[str]:
        """Get list of evidence point keys."""
        return [e.key for e in self.evidence_points]

    def has_evidence(self, key: str) -> bool:
        """Check if specific evidence exists."""
        return any(e.key == key for e in self.evidence_points)

    def get_evidence(self, key: str) -> EvidencePoint | None:
        """Get specific evidence by key."""
        for e in self.evidence_points:
            if e.key == key:
                return e
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for legacy compatibility."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "data": self.data,
            "evidence_points": [
                {"key": e.key, "value": e.value, "strength": e.strength, "source": e.source}
                for e in self.evidence_points
            ],
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "cached": self.cached,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentToolResult:
        """Create from dictionary."""
        evidence_points = []
        for ep in data.get("evidence_points", []):
            if isinstance(ep, dict):
                evidence_points.append(EvidencePoint(**ep))
            elif isinstance(ep, EvidencePoint):
                evidence_points.append(ep)

        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            tool_name=data.get("tool_name", ""),
            success=data.get("success", False),
            data=data.get("data", {}),
            evidence_points=evidence_points,
            error=data.get("error"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            cached=data.get("cached", False),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
        )


class ToolResultBuilder:
    """Builder for creating AgentToolResult objects."""

    def __init__(self, tool_name: str):
        self._tool_name = tool_name
        self._data: dict[str, Any] = {}
        self._evidence_points: list[EvidencePoint] = []
        self._metadata: dict[str, Any] = {}

    def with_data(self, key: str, value: Any) -> "ToolResultBuilder":
        """Add data to result."""
        self._data[key] = value
        return self

    def with_evidence(
        self,
        key: str,
        value: Any,
        strength: str = "medium",
        source: str = "",
    ) -> "ToolResultBuilder":
        """Add evidence point."""
        self._evidence_points.append(EvidencePoint(
            key=key,
            value=value,
            strength=strength,
            source=source,
        ))
        return self

    def with_metadata(self, key: str, value: Any) -> "ToolResultBuilder":
        """Add metadata."""
        self._metadata[key] = value
        return self

    def build_success(
        self,
        execution_time_ms: float = 0.0,
        cached: bool = False,
    ) -> AgentToolResult:
        """Build successful result."""
        return AgentToolResult(
            tool_name=self._tool_name,
            success=True,
            data=self._data,
            evidence_points=self._evidence_points,
            execution_time_ms=execution_time_ms,
            cached=cached,
            metadata=self._metadata,
        )

    def build_error(
        self,
        error: str,
        execution_time_ms: float = 0.0,
    ) -> AgentToolResult:
        """Build error result."""
        return AgentToolResult(
            tool_name=self._tool_name,
            success=False,
            data=self._data,
            error=error,
            execution_time_ms=execution_time_ms,
            metadata=self._metadata,
        )


def create_tool_result(
    tool_name: str,
    data: dict[str, Any],
    evidence_points: list[str] | None = None,
) -> AgentToolResult:
    """Factory to create tool result with common evidence points."""
    builder = ToolResultBuilder(tool_name)

    for key, value in data.items():
        builder.with_data(key, value)

    if evidence_points:
        for ep in evidence_points:
            builder.with_evidence(ep, data.get(ep, True))

    return builder.build_success()


def wrap_legacy_tool_output(
    tool_name: str,
    raw_output: Any,
) -> AgentToolResult:
    """Wrap legacy dict/JSON output into AgentToolResult."""
    if isinstance(raw_output, AgentToolResult):
        return raw_output

    if isinstance(raw_output, dict):
        return AgentToolResult.from_dict({
            "tool_name": tool_name,
            **raw_output,
        })

    return ToolResultBuilder(tool_name).with_data("value", raw_output).build_success()