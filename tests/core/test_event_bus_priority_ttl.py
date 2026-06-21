from __future__ import annotations

import time
from datetime import datetime, timedelta

from app.core.event_bus import (
    EVENT_PRIORITY_CRITICAL,
    AnalysisStaleEvent,
    EventBus,
    TruthDeviationEvent,
)


def test_handler_priority_order() -> None:
    bus = EventBus()
    bus.clear()
    order: list[str] = []

    def low(_evt: TruthDeviationEvent) -> None:
        order.append("low")

    def high(_evt: TruthDeviationEvent) -> None:
        order.append("high")

    bus.subscribe(TruthDeviationEvent, low, priority=1)
    bus.subscribe(TruthDeviationEvent, high, priority=100)
    bus.publish(
        TruthDeviationEvent(
            source="test",
            symbol="600519",
            market="CN",
            diff_pct=1.0,
            priority=EVENT_PRIORITY_CRITICAL,
        )
    )
    assert order == ["high", "low"]


def test_expired_event_not_dispatched() -> None:
    bus = EventBus()
    bus.clear()
    received: list[str] = []

    bus.subscribe(
        AnalysisStaleEvent,
        lambda _e: received.append("hit"),
    )
    stale = AnalysisStaleEvent(
        source="test",
        symbol="000001",
        market="CN",
        reason="expired",
        timestamp=datetime.now() - timedelta(seconds=10),
        ttl_seconds=1.0,
    )
    bus.publish(stale)
    assert received == []


def test_recent_events_include_priority_and_ttl() -> None:
    bus = EventBus()
    bus.clear()
    bus.publish(
        TruthDeviationEvent(
            source="test",
            symbol="600519",
            market="CN",
            diff_pct=0.8,
            ttl_seconds=120.0,
            priority=EVENT_PRIORITY_CRITICAL,
        )
    )
    items = bus.list_recent_events(limit=1)
    assert items
    row = items[0]
    assert row["priority"] == EVENT_PRIORITY_CRITICAL
    assert row["ttl_seconds"] == 120.0
    assert row["expires_at"] is not None


def test_handler_failure_is_recorded() -> None:
    bus = EventBus()
    bus.clear()

    def failing(_evt: TruthDeviationEvent) -> None:
        raise RuntimeError("boom")

    bus.subscribe(TruthDeviationEvent, failing)
    bus.publish(
        TruthDeviationEvent(
            source="test",
            symbol="600519",
            market="CN",
            diff_pct=1.0,
        )
    )

    failures = bus.list_handler_failures()
    assert failures[0]["event"] == "TruthDeviationEvent"
    assert failures[0]["handler"] == "failing"
    assert failures[0]["error"] == "boom"
    assert failures[0]["timestamp"]
