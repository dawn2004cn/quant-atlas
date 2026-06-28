from __future__ import annotations
"""Domain Events - implements Observer Pattern for event-driven architecture.

This module implements the event-driven architecture from midify_plan7.md:
- DomainEvent: Base class for all domain events
- EventDispatcher: Publish-subscribe event dispatcher
- Event handlers for signals, backtests, notifications
- Async event processing with Celery integration

Following Observer Pattern for loose coupling between components.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from logging import INFO
from datetime import datetime
from enum import Enum
from typing import Any
from collections.abc import Callable
from app.core.logger import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """Enumeration of all domain event types."""
    SIGNAL_TRIGGERED = "signal_triggered"
    BACKTEST_COMPLETED = "backtest_completed"
    TRADING_ORDER_PLACED = "trading_order_placed"
    TRADING_ORDER_FILLED = "trading_order_filled"
    TRADING_ORDER_CANCELLED = "trading_order_cancelled"
    MARKET_DATA_UPDATED = "market_data_updated"
    STRATEGY_OPTIMIZED = "strategy_optimized"
    AI_ANALYSIS_COMPLETED = "ai_analysis_completed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    ALERT_GENERATED = "alert_generated"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    RISK_VIOLATION = "risk_violation"

    RD_AGENT_EXPERIMENT_STARTED = "rd_agent_experiment_started"
    RD_AGENT_EXPERIMENT_COMPLETED = "rd_agent_experiment_completed"
    RD_AGENT_EXPERIMENT_FAILED = "rd_agent_experiment_failed"
    ALPHA_DISCOVERED = "alpha_discovered"
    FACTOR_DECAY_DETECTED = "factor_decay_detected"
    MARKET_REGIME_CHANGED = "market_regime_changed"


class EventPriority(Enum):
    """Event processing priority."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class DomainEvent:
    """Base domain event with metadata.

    Now integrates with Correlation ID system for full链路追踪.
    """
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    correlation_id: str | None = None
    priority: EventPriority = EventPriority.NORMAL
    async_processing: bool = False


@dataclass
class SignalEvent(DomainEvent):
    """Event triggered when a trading signal is generated."""

    def __init__(self, symbol: str, signal_type: str, strength: float, **kwargs):
        super().__init__(
            event_type=EventType.SIGNAL_TRIGGERED,
            async_processing=kwargs.get("async_processing", True),
            payload={
                "symbol": symbol,
                "signal_type": signal_type,
                "strength": strength,
                **kwargs,
            },
            **kwargs,
        )


@dataclass
class BacktestCompletedEvent(DomainEvent):
    """Event triggered when a backtest finishes."""

    def __init__(self, strategy_name: str, metrics: dict[str, Any], **kwargs):
        super().__init__(
            event_type=EventType.BACKTEST_COMPLETED,
            payload={
                "strategy_name": strategy_name,
                "metrics": metrics,
                **kwargs,
            },
            **kwargs,
        )


@dataclass
class TaskEvent(DomainEvent):
    """Event triggered for task lifecycle."""

    def __init__(self, task_id: str, task_name: str, status: str, result: Any = None, **kwargs):
        super().__init__(
            event_type=EventType.TASK_COMPLETED if status == "completed" else EventType.TASK_FAILED,
            payload={
                "task_id": task_id,
                "task_name": task_name,
                "status": status,
                "result": result,
                **kwargs,
            },
            **kwargs,
        )


class EventHandler(ABC):
    """Abstract base class for event handlers."""

    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        """Handle the event."""
        raise NotImplementedError

    @property
    @abstractmethod
    def event_type(self) -> EventType:
        """The event type this handler responds to."""
        raise NotImplementedError


class LoggingEventHandler(EventHandler):
    """Handler that logs events."""

    def __init__(self, log_level: int = INFO):
        self._log_level = log_level

    @property
    def event_type(self) -> EventType:
        return EventType.SIGNAL_TRIGGERED

    def handle(self, event: DomainEvent) -> None:
        logger.log(self._log_level, f"Event: {event.event_type.value} - {event.payload}")


class WebSocketEventHandler(EventHandler):
    """Handler that broadcasts events to WebSocket clients."""

    def __init__(self, broadcast_func: Callable[[str, dict], None] | None = None):
        self._broadcast = broadcast_func

    @property
    def event_type(self) -> EventType:
        return EventType.SIGNAL_TRIGGERED

    def handle(self, event: DomainEvent) -> None:
        if self._broadcast:
            self._broadcast(event.event_type.value, event.payload)


class EmailNotificationHandler(EventHandler):
    """Handler that sends email notifications for important events."""

    def __init__(self, email_service: Any = None):
        self._email_service = email_service

    @property
    def event_type(self) -> EventType:
        return EventType.ALERT_GENERATED

    def handle(self, event: DomainEvent) -> None:
        if self._email_service:
            subject = f"Alert: {event.event_type.value}"
            body = f"Event payload: {event.payload}"
            self._email_service.send(subject, body)


class EventDispatcher:
    """Central event dispatcher implementing Observer Pattern."""

    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._middlewares: list[Callable[[DomainEvent], DomainEvent | None]] = []

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__class__.__name__} to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    def add_middleware(self, middleware: Callable[[DomainEvent], DomainEvent | None]) -> None:
        """Add middleware to process events before handlers."""
        self._middlewares.append(middleware)

    def dispatch(self, event: DomainEvent) -> None:
        """Dispatch event to all subscribed handlers."""
        for middleware in self._middlewares:
            processed = middleware(event)
            if processed is None:
                logger.debug(f"Event {event.event_type.value} filtered by middleware")
                return
            event = processed

        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type.value}")
            return

        for handler in handlers:
            try:
                handler.handle(event)
            except Exception as e:
                logger.error(f"Handler {handler.__class__.__name__} failed: {e}")

    def dispatch_signal(
        self,
        symbol: str,
        signal_type: str,
        strength: float,
        **kwargs
    ) -> None:
        """Convenience method to dispatch a signal event."""
        event = SignalEvent(symbol, signal_type, strength, **kwargs)
        self.dispatch(event)

    def dispatch_backtest(
        self,
        strategy_name: str,
        metrics: dict[str, Any],
        **kwargs
    ) -> None:
        """Convenience method to dispatch a backtest completion event."""
        event = BacktestCompletedEvent(strategy_name, metrics, **kwargs)
        self.dispatch(event)


_global_dispatcher: EventDispatcher | None = None


def get_event_dispatcher() -> EventDispatcher:
    """Get the global event dispatcher."""
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = EventDispatcher()
    return _global_dispatcher


def set_event_dispatcher(dispatcher: EventDispatcher) -> None:
    """Set the global event dispatcher."""
    global _global_dispatcher
    _global_dispatcher = dispatcher


class DomainEventPublisher:
    """Mixin class for entities that can publish domain events."""

    def __init__(self):
        self._dispatcher = get_event_dispatcher()

    def publish_event(self, event: DomainEvent) -> None:
        """Publish a domain event."""
        self._dispatcher.dispatch(event)


class AsyncEventProcessor:
    """Async event processor using Celery for distributed processing.

    This implements the async handler integration from midify_plan8.md.
    """

    def __init__(self, celery_app=None):
        self._celery_app = celery_app
        self._event_queue: list[DomainEvent] = []

    def queue_event(self, event: DomainEvent) -> None:
        """Queue event for async processing."""
        if event.async_processing and self._celery_app:
            self._dispatch_celery(event)
        else:
            self._dispatch_sync(event)

    def _dispatch_celery(self, event: DomainEvent) -> None:
        """Dispatch event to Celery for async processing."""
        try:
            from app.tasks.event_tasks import process_domain_event
            process_domain_event.delay(
                event_type=event.event_type.value,
                payload=event.payload,
                source=event.source,
                correlation_id=event.correlation_id,
            )
            logger.info(f"Event {event.event_type.value} dispatched to Celery")
        except Exception as e:
            logger.error(f"Failed to dispatch to Celery: {e}")
            self._dispatch_sync(event)

    def _dispatch_sync(self, event: DomainEvent) -> None:
        """Dispatch event synchronously."""
        dispatcher = get_event_dispatcher()
        dispatcher.dispatch(event)


_global_async_processor: AsyncEventProcessor | None = None


def get_async_event_processor() -> AsyncEventProcessor:
    """Get the global async event processor."""
    global _global_async_processor
    if _global_async_processor is None:
        _global_async_processor = AsyncEventProcessor()
    return _global_async_processor


def publish_event_async(event: DomainEvent) -> None:
    """Publish event with async processing support."""
    processor = get_async_event_processor()
    processor.queue_event(event)


class BusinessEventPublisher:
    """Business-level event publisher with common business scenarios.

    This implements the business埋点 from midify_plan8.md.
    """

    @staticmethod
    def publish_signal_triggered(
        symbol: str,
        signal_type: str,
        strength: float,
        source: str = "signal_scanner",
    ) -> None:
        """Publish signal triggered event."""
        event = SignalEvent(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            source=source,
            async_processing=True,
        )
        publish_event_async(event)

    @staticmethod
    def publish_order_placed(
        order_id: str,
        symbol: str,
        direction: str,
        quantity: int,
        price: float,
    ) -> None:
        """Publish order placed event."""
        event = DomainEvent(
            event_type=EventType.TRADING_ORDER_PLACED,
            payload={
                "order_id": order_id,
                "symbol": symbol,
                "direction": direction,
                "quantity": quantity,
                "price": price,
            },
            async_processing=False,
        )
        publish_event_async(event)

    @staticmethod
    def publish_order_filled(
        order_id: str,
        symbol: str,
        filled_price: float,
        filled_quantity: int,
    ) -> None:
        """Publish order filled event."""
        event = DomainEvent(
            event_type=EventType.TRADING_ORDER_FILLED,
            payload={
                "order_id": order_id,
                "symbol": symbol,
                "filled_price": filled_price,
                "filled_quantity": filled_quantity,
            },
            async_processing=True,
        )
        publish_event_async(event)

    @staticmethod
    def publish_risk_violation(
        violation_type: str,
        details: dict[str, Any],
    ) -> None:
        """Publish risk violation event."""
        event = DomainEvent(
            event_type=EventType.RISK_VIOLATION,
            payload={
                "violation_type": violation_type,
                "details": details,
            },
            priority=EventPriority.HIGH,
            async_processing=False,
        )
        publish_event_async(event)

    @staticmethod
    def publish_backtest_completed(
        strategy_name: str,
        metrics: dict[str, Any],
    ) -> None:
        """Publish backtest completed event."""
        event = BacktestCompletedEvent(
            strategy_name=strategy_name,
            metrics=metrics,
            async_processing=True,
        )
        publish_event_async(event)


@dataclass
class RDAgentExperimentEvent(DomainEvent):
    """Event for RD-Agent experiment lifecycle."""

    def __init__(
        self,
        run_id: str,
        formula: str,
        goal: str | None = None,
        status: str = "started",
        **kwargs
    ):
        event_type_map = {
            "started": EventType.RD_AGENT_EXPERIMENT_STARTED,
            "completed": EventType.RD_AGENT_EXPERIMENT_COMPLETED,
            "failed": EventType.RD_AGENT_EXPERIMENT_FAILED,
        }
        super().__init__(
            event_type=event_type_map.get(status, EventType.RD_AGENT_EXPERIMENT_STARTED),
            async_processing=True,
            payload={
                "run_id": run_id,
                "formula": formula,
                "goal": goal,
                "status": status,
                **kwargs
            },
        )


@dataclass
class AlphaDiscoveredEvent(DomainEvent):
    """Event when a new alpha is discovered."""

    def __init__(
        self,
        alpha_id: str,
        formula: str,
        source: str,
        metrics: dict[str, Any],
        **kwargs
    ):
        super().__init__(
            event_type=EventType.ALPHA_DISCOVERED,
            async_processing=True,
            payload={
                "alpha_id": alpha_id,
                "formula": formula,
                "source": source,
                "metrics": metrics,
                **kwargs
            },
        )


@dataclass
class FactorDecayDetectedEvent(DomainEvent):
    """Event when factor decay is detected."""

    def __init__(
        self,
        factor_name: str,
        decay_reason: str,
        ir_before: float,
        ir_after: float,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.FACTOR_DECAY_DETECTED,
            priority=EventPriority.HIGH,
            async_processing=True,
            payload={
                "factor_name": factor_name,
                "decay_reason": decay_reason,
                "ir_before": ir_before,
                "ir_after": ir_after,
                **kwargs
            },
        )


@dataclass
class MarketRegimeChangedEvent(DomainEvent):
    """Event when market regime changes."""

    def __init__(
        self,
        old_regime: str,
        new_regime: str,
        confidence: float,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.MARKET_REGIME_CHANGED,
            priority=EventPriority.HIGH,
            async_processing=False,
            payload={
                "old_regime": old_regime,
                "new_regime": new_regime,
                "confidence": confidence,
                **kwargs
            },
        )
