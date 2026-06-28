from __future__ import annotations
"""Agent Memory and Self-Correction - RAG-driven long-term memory for agents.

This module implements the RAG-Driven Memory from midify_plan9.md:
- AgentMemory: Long-term memory for agent experiences
- Self-Correction: Agent can reference past failures
- Integration with ResearchReportRAGService

Usage:
    memory = AgentMemory(symbol="600519")
    past_failures = memory.get_past_failures()
    agent.inject_memory_context(past_failures)
"""


from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """Single memory entry for an agent."""
    id: str
    timestamp: datetime
    symbol: str
    agent_name: str
    event_type: str
    content: str
    outcome: str
    accuracy_score: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentMemory:
    """Long-term memory for agent experiences.

    Tracks agent decisions and outcomes to enable:
    - Historical pattern recognition
    - Self-correction based on past failures
    - Dynamic weight adjustment
    """

    def __init__(self, symbol: str | None = None):
        self._symbol = symbol
        self._memory: list[MemoryEntry] = []

    def record_decision(
        self,
        symbol: str,
        agent_name: str,
        decision: str,
        context: dict[str, Any],
    ) -> str:
        """Record an agent decision for future reference."""
        import uuid

        entry = MemoryEntry(
            id=str(uuid.uuid4())[:12],
            timestamp=datetime.now(),
            symbol=symbol,
            agent_name=agent_name,
            event_type="decision",
            content=decision,
            outcome="pending",
            metadata=context,
        )

        self._memory.append(entry)
        logger.info(f"Recorded decision for {agent_name} on {symbol}")

        return entry.id

    def record_outcome(
        self,
        memory_id: str,
        actual_outcome: str,
        accuracy_score: float,
    ) -> None:
        """Record the actual outcome of a decision."""
        for entry in self._memory:
            if entry.id == memory_id:
                entry.outcome = actual_outcome
                entry.accuracy_score = accuracy_score
                logger.info(f"Updated outcome for {memory_id}: {actual_outcome}")
                break

    def get_past_decisions(
        self,
        agent_name: str | None = None,
        days_back: int = 90,
    ) -> list[MemoryEntry]:
        """Get past decisions within time window."""
        cutoff = datetime.now() - timedelta(days=days_back)

        results = []
        for entry in self._memory:
            if entry.timestamp < cutoff:
                continue
            if agent_name and entry.agent_name != agent_name:
                continue
            results.append(entry)

        return sorted(results, key=lambda e: e.timestamp, reverse=True)

    def get_past_failures(
        self,
        agent_name: str | None = None,
        threshold: float = 0.4,
    ) -> list[MemoryEntry]:
        """Get past failures for self-correction.

        This enables the CriticAgent to automatically reference
        historical failures during analysis.
        """
        failures = []
        for entry in self._memory:
            if entry.outcome == "pending":
                continue

            is_failure = (
                entry.accuracy_score < threshold or
                (entry.outcome == "bearish" and entry.content == "bullish") or
                (entry.outcome == "bullish" and entry.content == "bearish")
            )

            if is_failure and (agent_name is None or entry.agent_name == agent_name):
                failures.append(entry)

        return failures

    def get_agent_performance(self, agent_name: str) -> dict[str, Any]:
        """Calculate performance metrics for an agent."""
        decisions = [e for e in self._memory if e.agent_name == agent_name]

        if not decisions:
            return {
                "total_decisions": 0,
                "accuracy": 0.0,
                "avg_confidence": 0.0,
            }

        total = len(decisions)
        accurate = sum(1 for e in decisions if e.accuracy_score >= 0.5)

        return {
            "total_decisions": total,
            "accuracy": accurate / total if total > 0 else 0.0,
            "recent_failures": len(self.get_past_failures(agent_name)),
        }

    def get_historical_patterns(self, symbol: str) -> dict[str, Any]:
        """Get historical patterns for a symbol."""
        symbol_entries = [e for e in self._memory if e.symbol == symbol]

        if not symbol_entries:
            return {"pattern": "insufficient_data"}

        bullish_count = sum(1 for e in symbol_entries if e.content == "bullish")
        bearish_count = sum(1 for e in symbol_entries if e.content == "bearish")
        avg_accuracy = sum(e.accuracy_score for e in symbol_entries) / len(symbol_entries)

        return {
            "total_decisions": len(symbol_entries),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "avg_accuracy": avg_accuracy,
            "first_decision": symbol_entries[-1].timestamp.isoformat() if symbol_entries else None,
            "last_decision": symbol_entries[0].timestamp.isoformat() if symbol_entries else None,
        }


class AgentMemoryInjector:
    """Injects memory context into agent prompts.

    This enables agents to be aware of their historical performance
    and make more informed decisions.
    """

    def __init__(self, memory: AgentMemory):
        self._memory = memory

    def inject_into_context(
        self,
        agent_name: str,
        symbol: str,
        base_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Inject memory context into agent's analysis context."""
        context = base_context.copy()

        past_failures = self._memory.get_past_failures(agent_name)
        if past_failures:
            context["self_correction_reminder"] = (
                f"Note: {agent_name} has made {len(past_failures)} historically inaccurate "
                f"decisions in recent analysis. Consider being more conservative."
            )
            context["past_failure_summary"] = [
                {
                    "date": f.timestamp.isoformat(),
                    "symbol": f.symbol,
                    "decision": f.content,
                    "outcome": f.outcome,
                }
                for f in past_failures[:3]
            ]

        performance = self._memory.get_agent_performance(agent_name)
        context["agent_performance"] = performance

        patterns = self._memory.get_historical_patterns(symbol)
        context["symbol_patterns"] = patterns

        return context


_global_memories: dict[str, AgentMemory] = {}


def get_agent_memory(symbol: str | None = None) -> AgentMemory:
    """Get or create agent memory for a symbol."""
    key = symbol or "global"

    if key not in _global_memories:
        _global_memories[key] = AgentMemory(symbol)

    return _global_memories[key]
