"""Tests for application -> core event bus bridge semantics."""

from __future__ import annotations

from datetime import datetime

from app.application.events.bridge import EVENT_TYPE_MAPPING, forward_event
from app.application.events.event_bus import Event, EventType
from app.core.event_bus import (
    ApplicationEventForwardedEvent,
    MarketRegimeChangedEvent,
    MarketDataUpdatedEvent,
)


class _RecordingBus:
    def __init__(self) -> None:
        self.published: list[object] = []

    def publish(self, event: object) -> None:
        self.published.append(event)


def test_quote_updated_maps_to_market_data(monkeypatch):
    bus = _RecordingBus()
    monkeypatch.setattr("app.application.events.bridge._get_core_bus", lambda: bus)

    forward_event(
        Event(
            type=EventType.QUOTE_UPDATED,
            payload={"symbol": "600519", "market": "CN"},
            source="test",
            timestamp=datetime.now(),
        )
    )

    assert len(bus.published) == 1
    assert isinstance(bus.published[0], MarketDataUpdatedEvent)
    assert bus.published[0].symbol == "600519"


def test_scan_completed_preserves_payload(monkeypatch):
    bus = _RecordingBus()
    monkeypatch.setattr("app.application.events.bridge._get_core_bus", lambda: bus)

    forward_event(
        Event(
            type=EventType.SCAN_COMPLETED,
            payload={"symbol": "000001", "hits": 3},
            source="scanner",
            timestamp=datetime.now(),
        )
    )

    assert len(bus.published) == 1
    evt = bus.published[0]
    assert isinstance(evt, ApplicationEventForwardedEvent)
    assert evt.app_event_type == EventType.SCAN_COMPLETED.value
    assert evt.payload["hits"] == 3


def test_regime_changed_maps_specialized_event(monkeypatch):
    bus = _RecordingBus()
    monkeypatch.setattr("app.application.events.bridge._get_core_bus", lambda: bus)

    forward_event(
        Event(
            type=EventType.MARKET_REGIME_CHANGED,
            payload={"new_regime": "bull", "confidence": 0.8, "market": "CN"},
            source="regime_svc",
            timestamp=datetime.now(),
        )
    )

    assert isinstance(bus.published[0], MarketRegimeChangedEvent)
    assert bus.published[0].new_regime == "bull"


def test_mapping_covers_key_event_types():
    assert EventType.MARKET_REGIME_CHANGED in EVENT_TYPE_MAPPING
    assert EventType.SCAN_COMPLETED in EVENT_TYPE_MAPPING
    assert EventType.SIGNALS_BATCH_PROCESSED in EVENT_TYPE_MAPPING
