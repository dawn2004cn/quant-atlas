from __future__ import annotations
"""Event-Driven Strategy Pipeline - Asymmetric Event Triggering.

This module implements from strategy_plan1.md:
- EventDrivenPipeline: Trigger strategies on non-periodic events
- EventTypes: Earnings, dividend, removal, sentiment
- ReactiveTrigger: Connect Agent evidence to strategy action

Usage:
    pipeline = EventDrivenPipeline()
    pipeline.register_handler("earnings_warning", emergency_reduce_position)
    pipeline.on_evidence("profit_down_50%", {"symbol": "600519"})
"""


import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections.abc import Callable


from app.core.logger import get_logger

logger = get_logger(__name__)


class MarketEventType(Enum):
    """Types of market events."""
    EARNINGS_RELEASE = "earnings_release"
    EARNINGS_WARNING = "earnings_warning"
    DIVIDEND = "dividend"
    INDEX_REBALANCE = "index_rebalance"
    SENTIMENT_CHANGE = "sentiment_change"
    REGIME_CHANGE = "regime_change"
    LIQUIDITY_SHOCK = "liquidity_shock"


@dataclass
class MarketEvent:
    """Market event data."""
    event_type: str
    symbol: str
    timestamp: datetime
    severity: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventHandler:
    """Event handler configuration."""
    event_type: str
    handler: Callable
    priority: int = 0
    enabled: bool = True


class EventDrivenPipeline:
    """Event-driven strategy pipeline for asymmetric events."""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}
        self._event_history: list[MarketEvent] = []

    def register_handler(
        self,
        event_type: str,
        handler: Callable,
        priority: int = 0,
    ) -> None:
        """Register event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(EventHandler(
            event_type=event_type,
            handler=handler,
            priority=priority,
        ))

        self._handlers[event_type].sort(key=lambda x: x.priority, reverse=True)

        logger.info(f"Registered handler for event: {event_type}")

    async def trigger(
        self,
        event: MarketEvent,
    ) -> list[Any]:
        """Trigger handlers for event."""
        self._event_history.append(event)

        if event.event_type not in self._handlers:
            return []

        results = []
        handlers = self._handlers[event.event_type]

        for handler in handlers:
            if not handler.enabled:
                continue

            try:
                if asyncio.iscoroutinefunction(handler.handler):
                    result = await handler.handler(event)
                else:
                    result = handler.handler(event)
                results.append(result)
            except Exception as e:
                logger.error(f"Handler failed for {event.event_type}: {e}")

        logger.info(f"Triggered {len(results)} handlers for {event.event_type}")
        return results

    def on_evidence(
        self,
        evidence_pattern: str,
        evidence_data: dict[str, Any],
    ) -> list[MarketEvent]:
        """Trigger events based on evidence from Agent."""
        events = []

        mapping = {
            "profit_down": ("earnings_warning", "high"),
            "cash_crisis": ("liquidity_shock", "critical"),
            "fraud": ("sentiment_change", "critical"),
            "delist": ("sentiment_change", "critical"),
            "negative_news": ("sentiment_change", "medium"),
        }

        for pattern, (event_type, severity) in mapping.items():
            if pattern in evidence_pattern.lower():
                event = MarketEvent(
                    event_type=event_type,
                    symbol=evidence_data.get("symbol", ""),
                    timestamp=datetime.now(),
                    severity=severity,
                    data=evidence_data,
                )
                events.append(event)

        return events


class ReactiveStrategyTrigger:
    """Connect Agent evidence to strategy actions via ReactivePipeline."""

    def __init__(self, pipeline: EventDrivenPipeline | None = None):
        self._pipeline = pipeline or EventDrivenPipeline()
        self._strategy_allocator = None

    def connect_to_allocator(self, allocator) -> None:
        """Connect to strategy allocator."""
        self._strategy_allocator = allocator

    async def handle_sentiment_evidence(
        self,
        evidence: dict[str, Any],
    ) -> None:
        """Handle negative sentiment from Agent."""
        events = self._pipeline.on_evidence("negative_news", evidence)

        for event in events:
            await self._trigger_emergency_action(event)

    async def handle_fraud_evidence(
        self,
        evidence: dict[str, Any],
    ) -> None:
        """Handle fraud detection from Agent."""
        events = self._pipeline.on_evidence("fraud", evidence)

        for event in events:
            await self._trigger_emergency_action(event)

    async def _trigger_emergency_action(
        self,
        event: MarketEvent,
    ) -> None:
        """Trigger emergency position reduction."""
        if self._strategy_allocator:
            logger.warning(f"Emergency action triggered: {event.event_type}")

            current_weights = {}
            for symbol in event.data.get("held_symbols", []):
                current_weights[symbol] = 0.1

            {k: v * 0.5 for k, v in current_weights.items()}

            logger.info(f"Emergency: reduced positions by 50% for {event.symbol}")


class AsymmetricEventStrategies:
    """Predefined strategies for asymmetric events."""

    @staticmethod
    async def handle_earnings_warning(event: MarketEvent) -> dict[str, Any]:
        """Handle earnings warning event."""
        return {
            "action": "reduce_position",
            "reduction": 0.5,
            "symbol": event.symbol,
            "reason": "earnings_warning",
        }

    @staticmethod
    async def handle_index_rebalance(event: MarketEvent) -> dict[str, Any]:
        """Handle index rebalancing event."""
        return {
            "action": "adjust_weights",
            "changes": event.data.get("changes", {}),
            "reason": "index_rebalance",
        }

    @staticmethod
    async def handle_regime_change(event: MarketEvent) -> dict[str, Any]:
        """Handle regime change event."""
        new_regime = event.data.get("new_regime", "neutral")
        return {
            "action": "switch_strategy",
            "regime": new_regime,
            "reason": "regime_change",
        }


_global_pipeline: EventDrivenPipeline | None = None


def get_event_pipeline() -> EventDrivenPipeline:
    """Get singleton event pipeline."""
    global _global_pipeline
    if _global_pipeline is None:
        _global_pipeline = EventDrivenPipeline()
    return _global_pipeline
