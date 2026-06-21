from __future__ import annotations
"""Shared Evidence Blackboard - structured evidence storage for multi-agent collaboration.

This module implements the Shared Evidence Blackboard from midify_plan9.md:
- EvidencePoint: Structured evidence entries
- EvidenceBlackboard: Central storage for evidence across agents
- Thread-safe access for concurrent agent operations

Usage:
    blackboard = EvidenceBlackboard()
    blackboard.write("technical", "support_level", 0.75, {"ma_cross": "golden_cross"})
    support = blackboard.read("technical", "support_level")
"""


import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EvidenceType(Enum):
    """Types of evidence that agents can contribute."""
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    RISK = "risk"
    BACKTEST = "backtest"
    CORRELATION = "correlation"


class EvidenceStrength(Enum):
    """Strength classification for evidence."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "neutral"


@dataclass
class EvidencePoint:
    """Single evidence point from an agent.

    This replaces the previous approach of passing Markdown reports.
    Agents now write structured evidence that can be directly referenced.
    """
    id: str
    agent_name: str
    evidence_type: EvidenceType
    key: str
    value: Any
    strength: EvidenceStrength
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    narrative: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "evidence_type": self.evidence_type.value,
            "key": self.key,
            "value": str(self.value),
            "strength": self.strength.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "narrative": self.narrative,
        }


class EvidenceBlackboard:
    """Centralized evidence storage for multi-agent collaboration.

    Implements the Shared Evidence Blackboard pattern where all agents
    write and read from a common structured storage.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._evidence: dict[str, dict[str, EvidencePoint]] = {}
        self._by_type: dict[EvidenceType, list[EvidencePoint]] = {}

    def write(
        self,
        agent_name: str,
        key: str,
        value: Any,
        evidence_type: EvidenceType = EvidenceType.QUALITATIVE,
        strength: EvidenceStrength = EvidenceStrength.MODERATE,
        narrative: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> EvidencePoint:
        """Write an evidence point to the blackboard."""
        import uuid

        point = EvidencePoint(
            id=str(uuid.uuid4()),  # full UUID for uniqueness
            agent_name=agent_name,
            evidence_type=evidence_type,
            key=key,
            value=value,
            strength=strength,
            narrative=narrative,
            metadata=metadata or {},
        )

        with self._lock:
            if agent_name not in self._evidence:
                self._evidence[agent_name] = {}
            self._evidence[agent_name][key] = point

            if evidence_type not in self._by_type:
                self._by_type[evidence_type] = []
            self._by_type[evidence_type].append(point)

        return point

    def read(self, agent_name: str, key: str) -> Any | None:
        """Read a specific evidence value."""
        with self._lock:
            return self._evidence.get(agent_name, {}).get(key, None)

    def read_value(self, agent_name: str, key: str) -> Any:
        """Read just the value (convenience method)."""
        point = self.read(agent_name, key)
        return point.value if point else None

    def get_agent_evidence(self, agent_name: str) -> list[EvidencePoint]:
        """Get all evidence from a specific agent."""
        with self._lock:
            return list(self._evidence.get(agent_name, {}).values())

    def get_evidence_by_type(self, evidence_type: EvidenceType) -> list[EvidencePoint]:
        """Get all evidence of a specific type."""
        with self._lock:
            return list(self._by_type.get(evidence_type, []))

    def get_all_evidence(self) -> list[EvidencePoint]:
        """Get all evidence points."""
        with self._lock:
            all_points = []
            for agent_evidence in self._evidence.values():
                all_points.extend(agent_evidence.values())
            return all_points

    def query_evidence(
        self,
        min_strength: EvidenceStrength | None = None,
        key_pattern: str | None = None,
    ) -> list[EvidencePoint]:
        """Query evidence with filters."""
        results = []

        with self._lock:
            for agent_evidence in self._evidence.values():
                for point in agent_evidence.values():
                    if min_strength and point.strength.value not in [
                        EvidenceStrength.STRONG.value,
                        min_strength.value,
                    ]:
                        continue

                    if key_pattern and key_pattern not in point.key:
                        continue

                    results.append(point)

        return results

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all evidence for decision making."""
        with self._lock:
            summary = {
                "total_agents": len(self._evidence),
                "total_points": sum(len(e) for e in self._evidence.values()),
                "by_type": {},
                "by_agent": {},
                "strong_evidence": [],
            }

            for etype, points in self._by_type.items():
                summary["by_type"][etype.value] = len(points)

            for agent, points in self._evidence.items():
                summary["by_agent"][agent] = len(points)
                for p in points:
                    if p.strength == EvidenceStrength.STRONG:
                        summary["strong_evidence"].append({
                            "agent": agent,
                            "key": p.key,
                            "value": str(p.value)[:50],
                        })

            return summary

    def clear(self, agent_name: str | None = None) -> None:
        """Clear evidence for a specific agent or all."""
        with self._lock:
            if agent_name:
                self._evidence.pop(agent_name, None)
                for etype in self._by_type:
                    self._by_type[etype] = [
                        p for p in self._by_type[etype]
                        if p.agent_name != agent_name
                    ]
            else:
                self._evidence.clear()
                self._by_type.clear()


class ThreadLocalBlackboard:
    """Thread-local wrapper for EvidenceBlackboard.

    Provides isolated blackboard instances for concurrent agent operations.
    """

    def __init__(self):
        self._local = threading.local()

    def get(self) -> EvidenceBlackboard:
        """Get or create thread-local blackboard."""
        if not hasattr(self._local, "blackboard"):
            self._local.blackboard = EvidenceBlackboard()
        return self._local.blackboard


_global_blackboard = EvidenceBlackboard()
_thread_local_blackboard = ThreadLocalBlackboard()


def get_evidence_blackboard() -> EvidenceBlackboard:
    """Get the global evidence blackboard."""
    return _global_blackboard


def get_thread_local_blackboard() -> EvidenceBlackboard:
    """Get thread-local blackboard for concurrent operations."""
    return _thread_local_blackboard.get()