"""Tests for Event System.

Run with: python -m pytest tests/test_events.py -v
"""

from __future__ import annotations

import pytest
from datetime import datetime
from app.domain.events.handlers import (
    DomainEvent,
    EventBus,
    EventHandler,
    EventPriority,
    get_event_bus,
    publish_event,
)
from app.domain.events.handlers import (
    StockCreatedEvent,
    SignalGeneratedEvent,
    PositionOpenedEvent,
    PositionClosedEvent,
)
from app.infrastructure.events.event_store import EventStore, InMemoryEventStore


class TestEventHandler(EventHandler):
    """Test event handler."""
    
    def __init__(self):
        self.events = []
    
    @property
    def priority(self) -> EventPriority:
        return EventPriority.NORMAL
    
    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)


class TestEventBus:
    """Tests for event bus."""
    
    def test_publish_event(self):
        """Test publishing event."""
        bus = EventBus()
        handler = TestEventHandler()
        bus.subscribe(handler)
        
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        bus.publish(event)
        
        assert len(handler.events) == 1
    
    def test_subscribe_handler(self):
        """Test subscribing handler."""
        bus = EventBus()
        handler = TestEventHandler()
        
        bus.subscribe(handler)
        
        assert len(bus._handlers) == 1
    
    def test_listen_event_type(self):
        """Test listening for specific event."""
        bus = EventBus()
        events = []
        
        def callback(event):
            events.append(event)
        
        bus.listen("StockCreatedEvent", callback)
        
        event = StockCreatedEvent(stock_code="600000", name="Test", market="A")
        bus.publish(event)
        
        assert len(events) == 1
    
    def test_get_history(self):
        """Test getting history."""
        bus = EventBus()
        
        event1 = StockCreatedEvent(stock_code="600000", name="Test1", market="A")
        event2 = StockCreatedEvent(stock_code="600001", name="Test2", market="A")
        
        bus.publish(event1)
        bus.publish(event2)
        
        history = bus.get_history(limit=10)
        
        assert len(history) == 2
    
    def test_clear_history(self):
        """Test clearing history."""
        bus = EventBus()
        
        event = StockCreatedEvent(stock_code="600000", name="Test", market="A")
        bus.publish(event)
        
        bus.clear_history()
        
        assert bus.event_count == 0
    
    def test_priority_ordering(self):
        """Test priority ordering."""
        bus = EventBus()
        handler = TestEventHandler()
        
        bus.subscribe(handler)
        
        assert handler.priority == EventPriority.NORMAL


class TestDomainEvents:
    """Tests for domain events."""
    
    def test_stock_created_event(self):
        """Test stock created event."""
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        assert event.stock_code == "600000"
        assert event.event_type == "StockCreatedEvent"
    
    def test_signal_generated_event(self):
        """Test signal generated event."""
        event = SignalGeneratedEvent(
            stock_code="600000",
            signal_type="buy",
            confidence=0.8,
            source="test"
        )
        
        assert event.signal_type == "buy"
    
    def test_position_opened_event(self):
        """Test position opened event."""
        event = PositionOpenedEvent(
            stock_code="600000",
            quantity=100,
            price=10
        )
        
        assert event.quantity == 100
    
    def test_event_metadata(self):
        """Test event metadata."""
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        assert event.event_id is not None
        assert event.occurred_at is not None


class TestEventStore:
    """Tests for event store."""
    
    def test_append_event(self):
        """Test appending event."""
        store = InMemoryEventStore()
        
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        store.append(event, "600000")
        
        assert store.get_event_count() == 1
    
    def test_get_events_by_aggregate(self):
        """Test getting events by aggregate."""
        store = InMemoryEventStore()
        
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        store.append(event, "600000")
        
        events = store.get_events(aggregate_id="600000")
        
        assert len(events) == 1
    
    def test_get_events_by_type(self):
        """Test getting events by type."""
        store = InMemoryEventStore()
        
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        store.append(event)
        
        events = store.get_events(event_type="StockCreatedEvent")
        
        assert len(events) == 1
    
    def test_subscribe(self):
        """Test subscribing to events."""
        store = InMemoryEventStore()
        received = []
        
        def callback(event):
            received.append(event)
        
        store.subscribe("StockCreatedEvent", callback)
        
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        store.append(event)
        
        assert len(received) == 1
    
    def test_clear(self):
        """Test clearing store."""
        store = InMemoryEventStore()
        
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        store.append(event)
        store.clear()
        
        assert store.get_event_count() == 0
    
    def test_export_import(self):
        """Test export/import."""
        store = InMemoryEventStore()
        
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        store.append(event)
        
        exported = store.export()
        
        assert len(exported) == 1
        
        store2 = InMemoryEventStore()
        store2.import_events(exported)
        
        assert store2.get_event_count() == 1


class TestGlobalEventBus:
    """Tests for global event bus."""
    
    def test_get_event_bus(self):
        """Test getting global event bus."""
        bus = get_event_bus()
        
        assert bus is not None
    
    def test_publish_event(self):
        """Test publishing to global bus."""
        event = StockCreatedEvent(
            stock_code="600000",
            name="Test",
            market="A"
        )
        
        publish_event(event)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])