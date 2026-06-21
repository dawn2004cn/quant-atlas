"""Tests for ApplicationEventForwardedEvent serialization."""

from __future__ import annotations

from app.core.event_bus import ApplicationEventForwardedEvent, event_from_envelope, event_to_envelope


def test_application_event_forwarded_roundtrip():
    evt = ApplicationEventForwardedEvent(
        app_event_type="scan_completed",
        payload={"symbol": "600519", "hits": 2},
        source="scanner",
    )
    envelope = event_to_envelope(evt).to_dict()
    restored = event_from_envelope(envelope)
    assert isinstance(restored, ApplicationEventForwardedEvent)
    assert restored.app_event_type == "scan_completed"
    assert restored.payload["hits"] == 2
