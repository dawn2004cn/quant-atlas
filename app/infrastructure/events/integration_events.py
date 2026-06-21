from __future__ import annotations
"""Integration Events - Emit domain events to external systems.

Emits domain events to Celery tasks and other external systems.
"""


import logging
from typing import Any, Optional

from app.domain.events.handlers import (
    DomainEvent,
    EventBus,
    StockCreatedEvent,
    SignalGeneratedEvent,
    PositionOpenedEvent,
    PositionClosedEvent,
    OrderSubmittedEvent,
    OrderFilledEvent,
    get_event_bus,
    publish_event,
)


from app.core.logger import get_logger

logger = get_logger(__name__)


class IntegrationEventEmitter:
    """Emit events to external systems."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus or get_event_bus()
        self._handlers: dict[str, list[callable]] = {}
        self._enabled = True
    
    def _register_default_handlers(self) -> None:
        """Register default handlers."""
        self._handlers = {
            "StockCreatedEvent": [self._handle_stock_created],
            "SignalGeneratedEvent": [self._handle_signal_generated],
            "PositionOpenedEvent": [self._handle_position_opened],
            "PositionClosedEvent": [self._handle_position_closed],
            "OrderSubmittedEvent": [self._handle_order_submitted],
            "OrderFilledEvent": [self._handle_order_filled],
        }
    
    def emit(self, event: DomainEvent) -> None:
        """Emit event to external systems."""
        if not self._enabled:
            return
        
        logger.info(f"Emitting event: {event.event_type}")
        
        publish_event(event)
        
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    def _handle_stock_created(self, event: DomainEvent) -> None:
        """Handle stock created."""
        logger.info(f"External: Stock created {event.metadata.get('stock_code')}")
    
    def _handle_signal_generated(self, event: DomainEvent) -> None:
        """Handle signal generated."""
        logger.info(f"External: Signal generated {event.metadata.get('signal_type')}")
    
    def _handle_position_opened(self, event: DomainEvent) -> None:
        """Handle position opened."""
        logger.info(f"External: Position opened {event.metadata.get('stock_code')}")
    
    def _handle_position_closed(self, event: DomainEvent) -> None:
        """Handle position closed."""
        logger.info(f"External: Position closed {event.metadata.get('pnl')}")
    
    def _handle_order_submitted(self, event: DomainEvent) -> None:
        """Handle order submitted."""
        logger.info(f"External: Order submitted {event.metadata.get('order_id')}")
    
    def _handle_order_filled(self, event: DomainEvent) -> None:
        """Handle order filled."""
        logger.info(f"External: Order filled {event.metadata.get('order_id')}")
    
    def enable(self) -> None:
        self._enabled = True
    
    def disable(self) -> None:
        self._enabled = False


class CeleryEventDispatcher:
    """Dispatch events to Celery tasks."""
    
    def __init__(self):
        self._celery_app = None
        self._enabled = False
    
    def set_celery_app(self, app) -> None:
        """Set Celery app."""
        self._celery_app = app
        self._enabled = True
    
    def dispatch(self, event: DomainEvent) -> None:
        """Dispatch event to Celery task."""
        if not self._enabled or not self._celery_app:
            return
        
        task_map = {
            "StockCreatedEvent": "tasks.sync_stock_data",
            "SignalGeneratedEvent": "tasks.process_signal",
            "OrderSubmittedEvent": "tasks.process_order",
            "OrderFilledEvent": "tasks.settle_trade",
        }
        
        task_name = task_map.get(event.event_type)
        if task_name:
            try:
                task = self._celery_app.send_task(
                    task_name,
                    args=[event.metadata],
                    queue="events",
                )
                logger.info(f"Dispatched: {task_name}")
            except Exception as e:
                logger.error(f"Failed to dispatch {task_name}: {e}")


class IntegrationEvents:
    """Integration events facade."""
    
    def __init__(self):
        self._emitter = IntegrationEventEmitter()
        self._dispatcher = CeleryEventDispatcher()
        self._emitter._register_default_handlers()
    
    def emit_stock_created(
        self,
        stock_code: str,
        name: str,
        market: str,
        aggregate_id: Optional[str] = None
    ) -> None:
        """Emit stock created event."""
        event = StockCreatedEvent(
            stock_code=stock_code,
            name=name,
            market=market,
        )
        event.metadata = {
            "stock_code": stock_code,
            "name": name,
            "market": market,
            "aggregate_id": aggregate_id or stock_code,
        }
        
        self._emitter.emit(event)
        self._dispatcher.dispatch(event)
    
    def emit_signal_generated(
        self,
        stock_code: str,
        signal_type: str,
        confidence: float,
        source: str,
        aggregate_id: Optional[str] = None
    ) -> None:
        """Emit signal generated event."""
        event = SignalGeneratedEvent(
            stock_code=stock_code,
            signal_type=signal_type,
            confidence=confidence,
            source=source,
        )
        event.metadata = {
            "stock_code": stock_code,
            "signal_type": signal_type,
            "confidence": confidence,
            "source": source,
            "aggregate_id": aggregate_id or stock_code,
        }
        
        self._emitter.emit(event)
        self._dispatcher.dispatch(event)
    
    def emit_position_opened(
        self,
        stock_code: str,
        quantity: float,
        price: float,
        aggregate_id: Optional[str] = None
    ) -> None:
        """Emit position opened event."""
        event = PositionOpenedEvent(
            stock_code=stock_code,
            quantity=quantity,
            price=price,
        )
        event.metadata = {
            "stock_code": stock_code,
            "quantity": quantity,
            "price": price,
            "aggregate_id": aggregate_id or "",
        }
        
        self._emitter.emit(event)
        self._dispatcher.dispatch(event)
    
    def emit_position_closed(
        self,
        stock_code: str,
        quantity: float,
        pnl: float,
        aggregate_id: Optional[str] = None
    ) -> None:
        """Emit position closed event."""
        event = PositionClosedEvent(
            stock_code=stock_code,
            quantity=quantity,
            pnl=pnl,
        )
        event.metadata = {
            "stock_code": stock_code,
            "quantity": quantity,
            "pnl": pnl,
            "aggregate_id": aggregate_id or stock_code,
        }
        
        self._emitter.emit(event)
        self._dispatcher.dispatch(event)
    
    def emit_order_submitted(
        self,
        order_id: str,
        stock_code: str,
        side: str,
        quantity: float,
        aggregate_id: Optional[str] = None
    ) -> None:
        """Emit order submitted event."""
        event = OrderSubmittedEvent(
            order_id=order_id,
            stock_code=stock_code,
            side=side,
            quantity=quantity,
        )
        event.metadata = {
            "order_id": order_id,
            "stock_code": stock_code,
            "side": side,
            "quantity": quantity,
            "aggregate_id": aggregate_id or "",
        }
        
        self._emitter.emit(event)
        self._dispatcher.dispatch(event)
    
    def emit_order_filled(
        self,
        order_id: str,
        stock_code: str,
        quantity: float,
        price: float,
        aggregate_id: Optional[str] = None
    ) -> None:
        """Emit order filled event."""
        event = OrderFilledEvent(
            order_id=order_id,
            stock_code=stock_code,
            quantity=quantity,
            price=price,
        )
        event.metadata = {
            "order_id": order_id,
            "stock_code": stock_code,
            "quantity": quantity,
            "price": price,
            "aggregate_id": aggregate_id or "",
        }
        
        self._emitter.emit(event)
        self._dispatcher.dispatch(event)


_global_integration_events: Optional[IntegrationEvents] = None


def get_integration_events() -> IntegrationEvents:
    """Get global integration events."""
    global _global_integration_events
    if _global_integration_events is None:
        _global_integration_events = IntegrationEvents()
    return _global_integration_events


__all__ = [
    "IntegrationEventEmitter",
    "CeleryEventDispatcher",
    "IntegrationEvents",
    "get_integration_events",
]