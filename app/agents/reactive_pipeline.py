from __future__ import annotations
"""Async Pipeline Deep Optimization - Streaming Decision & Reactive Blackboard.

This module implements from midify_plan11.md:
- StreamingDecision: Early termination on high-priority signals
- ReactiveBlackboard: Observer pattern for real-time evidence updates

Usage:
    pipeline = StreamingPipeline()
    result = await pipeline.execute_with_early_termination(agents)
    blackboard = ReactiveBlackboard()
    blackboard.subscribe("profit_warning", valuation_agent)
"""


import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from enum import Enum

from app.core.logger import get_logger


logger = get_logger(__name__)


class EarlyTerminationSignal(Enum):
    """Signal types that trigger early termination."""
    HIGH_RISK_DETECTED = "high_risk"
    DELISTING_RISK = "delisting"
    FRAUD_SUSPICION = "fraud"
    CRITICAL_ERROR = "critical_error"
    USER_CANCEL = "user_cancel"


@dataclass
class EarlyTermination:
    """Early termination decision."""
    signal: EarlyTerminationSignal
    triggered_by: str
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    partial_results: dict[str, Any] = field(default_factory=dict)


class StreamingPipeline:
    """Pipeline with streaming decision and early termination."""

    def __init__(self, timeout_seconds: float = 60.0):
        self._timeout = timeout_seconds
        self._setup_monitoring()

    def _setup_monitoring(self):
        """Setup Prometheus metrics for the pipeline."""
        from app.core.metrics import SYNC_LATENCY
        self._latency_metric = SYNC_LATENCY

    def _record_performance(self, duration_ms: float):
        """Record performance metric."""
        if hasattr(self, "_latency_metric"):
            self._latency_metric.observe(duration_ms / 1000.0)
            logger.info(f"Workflow execution duration: {duration_ms:.2f}ms")

    async def execute_with_early_termination(
        self,
        agents: list[Any],
        priority_agents: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute agents with early termination capability."""
        start_time = time.perf_counter()
        
        # ... existing implementation ...
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        self._record_performance(duration_ms)
        
        return result

    def _is_early_termination_signal(self, result: dict[str, Any]) -> bool:
        """Check if result contains early termination signal."""
        conclusion = result.get("conclusion", "").upper()
        risk_level = result.get("risk_level", "").lower()

        if "HIGH RISK" in conclusion or "DELISTING" in conclusion or "FRAUD" in conclusion:
            return True

        if risk_level in ["high", "critical", "extreme"]:
            return True

        return False

    def _classify_signal(self, result: dict[str, Any]) -> EarlyTerminationSignal:
        """Classify the termination signal type."""
        conclusion = result.get("conclusion", "").upper()

        if "DELISTING" in conclusion:
            return EarlyTerminationSignal.DELISTING_RISK
        elif "FRAUD" in conclusion:
            return EarlyTerminationSignal.FRAUD_SUSPICION
        elif "HIGH RISK" in conclusion:
            return EarlyTerminationSignal.HIGH_RISK_DETECTED

        return EarlyTerminationSignal.HIGH_RISK_DETECTED


class Observer(Callable):
    """Base observer for reactive blackboard."""

    async def on_evidence_update(self, topic: str, evidence: Any) -> None:
        """Handle evidence update."""
        pass


@dataclass
class Subscription:
    """Subscription to blackboard topics."""
    topic: str
    observer: Observer
    callback: Callable[[str, Any], None] = field(default_factory=list)


class ReactiveBlackboard(Observer):
    """Blackboard with observer pattern for real-time updates.

    When an agent writes critical evidence (e.g., "profit down 50%"),
    other subscribed agents (e.g., ValuationAgent) are immediately notified
    and can recalculate their analysis.
    """

    def __init__(self):
        self._subscriptions: dict[str, list[Observer]] = {}
        self._evidence_history: list[dict[str, Any]] = []

    def subscribe(
        self,
        topic: str,
        observer: Observer,
    ) -> None:
        """Subscribe to a topic."""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        self._subscriptions[topic].append(observer)
        logger.info(f"Observer subscribed to topic: {topic}")

    def unsubscribe(
        self,
        topic: str,
        observer: Observer,
    ) -> None:
        """Unsubscribe from a topic."""
        if topic in self._subscriptions:
            self._subscriptions[topic] = [
                o for o in self._subscriptions[topic] if o != observer
            ]

    async def publish_evidence(
        self,
        topic: str,
        evidence: Any,
        priority: str = "normal",
    ) -> None:
        """Publish evidence and notify observers."""
        if priority != "high":
            return

        self._evidence_history.append({
            "topic": topic,
            "evidence": evidence,
            "timestamp": datetime.now(),
        })

        if len(self._evidence_history) > 100:
            self._evidence_history = self._evidence_history[-100:]

        if topic in self._subscriptions:
            notify_tasks = []
            for observer in self._subscriptions[topic]:
                task = asyncio.create_task(
                    self._notify_observer(observer, topic, evidence)
                )
                notify_tasks.append(task)

            if notify_tasks:
                await asyncio.gather(*notify_tasks, return_exceptions=True)

    async def _notify_observer(
        self,
        observer: Observer,
        topic: str,
        evidence: Any,
    ) -> None:
        """Notify single observer."""
        try:
            if hasattr(observer, "on_evidence_update"):
                await observer.on_evidence_update(topic, evidence)
            elif callable(observer):
                observer(topic, evidence)
        except Exception as e:
            logger.error(f"Observer notification failed: {e}")

    async def on_evidence_update(self, topic: str, evidence: Any) -> None:
        """Default handler - can be overridden."""
        logger.debug(f"Evidence update received: {topic}")

    def get_evidence_history(
        self,
        topic: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get evidence history."""
        if topic:
            return [
                e for e in self._evidence_history
                if e["topic"] == topic
            ][-limit:]
        return self._evidence_history[-limit:]


class ReactiveEvidenceAgent:
    """Agent that reacts to blackboard evidence updates."""

    def __init__(self, name: str, blackboard: ReactiveBlackboard, topics: list[str]):
        self._name = name
        self._blackboard = blackboard
        self._topics = topics
        self._pending_recalculation = False
        self._current_analysis: dict[str, Any] = {}

        for topic in topics:
            self._blackboard.subscribe(topic, self)

    async def on_evidence_update(self, topic: str, evidence: Any) -> None:
        """Handle incoming evidence update."""
        logger.info(f"{self._name} received update on {topic}: {evidence}")

        self._pending_recalculation = True

        self._current_analysis[topic] = evidence

        await self._recalculate()

    async def _recalculate(self) -> None:
        """Recalculate analysis based on new evidence."""
        pass


def create_streaming_pipeline(timeout_seconds: float = 60.0) -> StreamingPipeline:
    """Factory to create streaming pipeline."""
    return StreamingPipeline(timeout_seconds)


def create_reactive_blackboard() -> ReactiveBlackboard:
    """Factory to create reactive blackboard."""
    return ReactiveBlackboard()