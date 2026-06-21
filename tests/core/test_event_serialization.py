from __future__ import annotations

import json

import pytest

from app.core.event_bus import (
    EventSchemaError,
    MarketRegimeChangedEvent,
    TradeExecutedEvent,
    event_from_envelope,
    event_from_json,
    event_schema,
    event_to_json,
)


def test_market_regime_event_roundtrips() -> None:
    event = MarketRegimeChangedEvent(
        previous_regime="sideways",
        new_regime="bull",
        confidence=0.81,
        trigger_reason="score_crossed_threshold",
    )

    payload = event_to_json(event)
    restored = event_from_json(payload)

    assert isinstance(restored, MarketRegimeChangedEvent)
    assert restored.previous_regime == "sideways"
    assert restored.new_regime == "bull"
    assert restored.confidence == 0.81
    assert restored.trigger_reason == "score_crossed_threshold"


def test_trade_event_requires_provenance_only_when_publishing_not_serializing() -> None:
    event = TradeExecutedEvent(
        user_id="u1",
        symbol="000001",
        action="buy",
        quantity=100,
        price=12.34,
        provenance_id="p1",
    )

    restored = event_from_envelope(json.loads(event_to_json(event)))

    assert restored.quantity == 100
    assert restored.price == 12.34
    assert restored.provenance_id == "p1"


def test_event_schema_lists_base_and_domain_fields() -> None:
    schema = event_schema(MarketRegimeChangedEvent)

    assert schema["event"] == "MarketRegimeChangedEvent"
    assert "timestamp" in schema
    assert "previous_regime" in schema["data"]
    assert "new_regime" in schema["data"]
    assert "confidence" in schema["data"]


def test_unknown_event_name_raises_schema_error() -> None:
    with pytest.raises(EventSchemaError):
        event_from_envelope({"event": "UnknownEvent", "data": {}})


def test_missing_required_envelope_fields_raises_schema_error() -> None:
    with pytest.raises(EventSchemaError):
        event_from_envelope({"event": "MarketRegimeChangedEvent"})
