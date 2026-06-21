from __future__ import annotations
"""Domain Event Publisher - Publishes domain events from application layer.

Wires domain events to Flask and external systems.
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


class IEventStore:
    """Interface for event store."""
    
    def save(self, event: DomainEvent) -> None:
        pass
    
    def get_events(self, aggregate_id: str, limit: int = 100) -> list[DomainEvent]:
        pass


class IIntegrationEvents:
    """Interface for integration events."""
    
    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        pass


class DomainEventPublisher:
    """Publisher for domain events.
    
    Connects domain event system to application layer.
    """
    
    def __init__(
        self,
        event_store: Optional[IEventStore] = None,
        integration_events: Optional[IIntegrationEvents] = None,
    ):
        self._event_bus = get_event_bus()
        self._event_store = event_store
        self._integration = integration_events
        self._enabled = True
        logger.info("DomainEventPublisher initialized")
    
    @property
    def event_store(self):
        if self._event_store is None:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self._event_store = resolve_optional_service(IEventStore)
        if self._event_store is None:
            from app.modules.system.services.helpers.events_access import get_default_event_store
            self._event_store = get_default_event_store()
        return self._event_store
    
    @property
    def integration(self):
        if self._integration is None:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self._integration = resolve_optional_service(IIntegrationEvents)
        if self._integration is None:
            from app.modules.system.services.helpers.events_access import get_default_integration_events
            self._integration = get_default_integration_events()
        return self._integration
    
    def publish(self, event: DomainEvent, aggregate_id: Optional[str] = None) -> None:
        """Publish event to all subscribers."""
        if not self._enabled:
            return
        
        publish_event(event)
        
        if aggregate_id:
            self.event_store.append(event, aggregate_id)
        
        logger.debug(f"Published: {event.event_type}")
    
    def publish_stock_created(
        self,
        stock_code: str,
        name: str,
        market: str
    ) -> None:
        """Publish stock created event."""
        event = StockCreatedEvent(
            stock_code=stock_code,
            name=name,
            market=market,
        )
        event.metadata = {
            "stock_code": stock_code,
            "name": name,
            "market": market,
        }
        
        self.publish(event, stock_code)
        self._integration.emit_stock_created(stock_code, name, market, stock_code)
    
    def publish_signal_generated(
        self,
        stock_code: str,
        signal_type: str,
        confidence: float,
        source: str
    ) -> None:
        """Publish signal generated event."""
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
        }
        
        self.publish(event, stock_code)
        self._integration.emit_signal_generated(
            stock_code, signal_type, confidence, source, stock_code
        )
    
    def publish_position_opened(
        self,
        stock_code: str,
        quantity: float,
        price: float
    ) -> None:
        """Publish position opened event."""
        event = PositionOpenedEvent(
            stock_code=stock_code,
            quantity=quantity,
            price=price,
        )
        event.metadata = {
            "stock_code": stock_code,
            "quantity": quantity,
            "price": price,
        }
        
        self.publish(event, stock_code)
        self._integration.emit_position_opened(stock_code, quantity, price, stock_code)
    
    def publish_position_closed(
        self,
        stock_code: str,
        quantity: float,
        pnl: float
    ) -> None:
        """Publish position closed event."""
        event = PositionClosedEvent(
            stock_code=stock_code,
            quantity=quantity,
            pnl=pnl,
        )
        event.metadata = {
            "stock_code": stock_code,
            "quantity": quantity,
            "pnl": pnl,
        }
        
        self.publish(event, stock_code)
        self._integration.emit_position_closed(stock_code, quantity, pnl, stock_code)
    
    def publish_order_submitted(
        self,
        order_id: str,
        stock_code: str,
        side: str,
        quantity: float
    ) -> None:
        """Publish order submitted event."""
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
        }
        
        self.publish(event, order_id)
        self._integration.emit_order_submitted(
            order_id, stock_code, side, quantity, order_id
        )
    
    def publish_order_filled(
        self,
        order_id: str,
        stock_code: str,
        quantity: float,
        price: float
    ) -> None:
        """Publish order filled event."""
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
        }
        
        self.publish(event, order_id)
        self._integration.emit_order_filled(order_id, stock_code, quantity, price, order_id)
    
    def get_event_history(
        self,
        aggregate_id: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """Get event history."""
        events = self.event_store.get_events(aggregate_id=aggregate_id)
        return events[-limit:]
    
    def enable(self) -> None:
        self._enabled = True
        logger.info("Event publishing enabled")
    
    def disable(self) -> None:
        self._enabled = False
        logger.info("Event publishing disabled")


_global_publisher: Optional[DomainEventPublisher] = None


def get_event_publisher() -> DomainEventPublisher:
    """Get global event publisher."""
    global _global_publisher
    if _global_publisher is None:
        _global_publisher = DomainEventPublisher()
    return _global_publisher


def emit_stock_created(stock_code: str, name: str, market: str) -> None:
    """Convenience function."""
    get_event_publisher().publish_stock_created(stock_code, name, market)


def emit_signal_generated(
    stock_code: str,
    signal_type: str,
    confidence: float,
    source: str
) -> None:
    """Convenience function."""
    get_event_publisher().publish_signal_generated(
        stock_code, signal_type, confidence, source
    )


def emit_position_opened(stock_code: str, quantity: float, price: float) -> None:
    """Convenience function."""
    get_event_publisher().publish_position_opened(stock_code, quantity, price)


def emit_position_closed(stock_code: str, quantity: float, pnl: float) -> None:
    """Convenience function."""
    get_event_publisher().publish_position_closed(stock_code, quantity, pnl)


__all__ = [
    "DomainEventPublisher",
    "get_event_publisher",
    "emit_stock_created",
    "emit_signal_generated",
    "emit_position_opened",
    "emit_position_closed",
]