from __future__ import annotations
"""Reactive Evidence Processing - Evidence Listeners with Interrupt Mechanism.

This module implements from midify_plan12.md:
- EvidenceListener: Subscribe to specific evidence patterns
- InterruptSignal: Trigger recalculation when critical evidence is written
- PatchSignal: Inject additional context without interrupting

Usage:
    listener = EvidenceListener(agent=backtest_agent)
    blackboard.subscribe("profit_warning", listener)
    # When "profit down 50%" is written, backtest_agent receives interrupt
"""


import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from enum import Enum

from app.core.logger import get_logger


logger = get_logger(__name__)


class SignalType(Enum):
    """Types of reactive signals."""
    INTERRUPT = "interrupt"
    PATCH = "patch"
    RECALCULATE = "recalculate"
    ESCALATE = "escalate"


@dataclass
class InterruptSignal:
    """Signal to interrupt agent execution."""
    signal_type: SignalType
    triggered_by: str
    evidence_key: str
    evidence_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceListenerConfig:
    """Configuration for evidence listener."""
    subscribed_patterns: list[str]
    signal_threshold: str = "strong"
    on_interrupt: Callable[[InterruptSignal], Any] | None = None
    on_patch: Callable[[InterruptSignal], Any] | None = None


class EvidenceListener:
    """Listener that reacts to evidence changes in blackboard.

    When strong evidence matching subscribed patterns is written,
    triggers interrupt or patch signal to dependent agents.
    """

    def __init__(
        self,
        agent_name: str,
        config: EvidenceListenerConfig,
    ):
        self._agent_name = agent_name
        self._config = config
        self._pending_signals: list[InterruptSignal] = []

    async def on_evidence_published(
        self,
        topic: str,
        evidence_key: str,
        evidence_value: Any,
        strength: str,
    ) -> None:
        """Handle published evidence."""
        if strength not in ["strong", "critical"]:
            return

        for pattern in self._config.subscribed_patterns:
            if self._match_pattern(pattern, evidence_key, evidence_value):
                await self._trigger_signal(
                    topic,
                    evidence_key,
                    evidence_value,
                )
                break

    def _match_pattern(
        self,
        pattern: str,
        key: str,
        value: Any,
    ) -> bool:
        """Match evidence against subscribed pattern."""
        if pattern in key.lower():
            return True

        value_str = str(value).lower()
        if pattern in value_str:
            return True

        return False

    async def _trigger_signal(
        self,
        topic: str,
        key: str,
        value: Any,
    ) -> None:
        """Trigger appropriate signal type."""
        signal = InterruptSignal(
            signal_type=SignalType.INTERRUPT if self._config.on_interrupt else SignalType.PATCH,
            triggered_by=topic,
            evidence_key=key,
            evidence_value=value,
            payload={"agent": self._agent_name},
        )

        self._pending_signals.append(signal)

        if signal.signal_type == SignalType.INTERRUPT and self._config.on_interrupt:
            logger.warning(f"INTERRUPT signal to {self._agent_name}: {key}={value}")
            await self._config.on_interrupt(signal)
        elif signal.signal_type == SignalType.PATCH and self._config.on_patch:
            logger.info(f"PATCH signal to {self._agent_name}: {key}={value}")
            await self._config.on_patch(signal)

    def get_pending_signals(self) -> list[InterruptSignal]:
        """Get all pending signals."""
        return self._pending_signals.copy()

    def clear_signals(self) -> None:
        """Clear pending signals."""
        self._pending_signals.clear()


class ReactiveEvidencePublisher:
    """Enhanced blackboard that publishes evidence to listeners."""

    def __init__(self):
        self._listeners: dict[str, list[EvidenceListener]] = {}

    def register_listener(
        self,
        topic: str,
        listener: EvidenceListener,
    ) -> None:
        """Register listener for a topic."""
        if topic not in self._listeners:
            self._listeners[topic] = []
        self._listeners[topic].append(listener)
        logger.info(f"Listener {listener._agent_name} registered for topic: {topic}")

    async def publish_evidence_with_strength(
        self,
        topic: str,
        key: str,
        value: Any,
        strength: str = "medium",
    ) -> None:
        """Publish evidence and notify listeners."""
        if topic in self._listeners:
            tasks = []
            for listener in self._listeners[topic]:
                task = asyncio.create_task(
                    listener.on_evidence_published(topic, key, value, strength)
                )
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)


class EvidencePatternMatcher:
    """Match evidence against patterns for reactive triggering."""

    CRITICAL_PATTERNS = {
        "profit_drop": ["profit.*down", "净利润.*下降", " earnings .* decline"],
        "cash_crisis": ["cash.*tight", "现金流.*紧张", " liquidity .* crisis"],
        "fraud_indicator": ["fraud", "会计.*违规", "财务.*造假"],
        "delisting_risk": ["delist", "退市.*风险"],
        "debt_default": ["default.*risk", "债务.*违约"],
    }

    @classmethod
    def is_critical_evidence(
        cls,
        key: str,
        value: Any,
    ) -> tuple[bool, str]:
        """Check if evidence matches critical pattern."""
        key_lower = key.lower()
        value_str = str(value).lower()

        for pattern_name, patterns in cls.CRITICAL_PATTERNS.items():
            for pattern in patterns:
                if pattern in key_lower or pattern in value_str:
                    return True, pattern_name

        return False, ""

    @classmethod
    def get_matching_listeners(
        cls,
        key: str,
        value: Any,
        listeners: list[EvidenceListener],
    ) -> list[EvidenceListener]:
        """Get listeners that should react to this evidence."""
        is_critical, pattern_name = cls.is_critical_evidence(key, value)

        if not is_critical:
            return []

        matching = []
        for listener in listeners:
            for subscribed in listener._config.subscribed_patterns:
                if subscribed in pattern_name or subscribed in key.lower():
                    matching.append(listener)
                    break

        return matching


def create_evidence_listener(
    agent_name: str,
    patterns: list[str],
    on_interrupt: Callable | None = None,
) -> EvidenceListener:
    """Factory to create evidence listener."""
    config = EvidenceListenerConfig(
        subscribed_patterns=patterns,
        on_interrupt=on_interrupt,
    )
    return EvidenceListener(agent_name, config)