# P7 Event Serialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a centralized event envelope schema for local and cross-process EventBus payloads, then make EventBus publish/broadcast use it.

**Architecture:** Keep existing dataclass event classes. Add serialization helpers in `app/core/event_bus.py`: `event_to_envelope()`, `event_from_envelope()`, `event_to_json()`, `event_from_json()`, and `event_schema()`. EventBus stores serialized envelopes in `_recent_events` and broadcasts envelopes to WebSocket.

**Tech Stack:** Python dataclasses, stdlib `json`, no new dependency.

---

### Task 1: Add event envelope schema and tests

**Files:**
- Modify: `app/core/event_bus.py`
- Create: `tests/core/test_event_serialization.py`

- [ ] **Step 1: Write failing tests**

```python
from app.core.event_bus import (
    MarketRegimeChangedEvent,
    event_from_json,
    event_from_envelope,
    event_schema,
    event_to_json,
)

def test_market_regime_event_roundtrips():
    event = MarketRegimeChangedEvent(previous_regime="sideways", new_regime="bull", confidence=0.81)
    payload = event_to_json(event)
    restored = event_from_json(payload)
    assert restored.previous_regime == "sideways"
    assert restored.new_regime == "bull"
    assert restored.confidence == 0.81

def test_event_schema_lists_required_base_fields():
    schema = event_schema(MarketRegimeChangedEvent)
    assert schema["event"] == "MarketRegimeChangedEvent"
    assert "previous_regime" in schema["data"]
```

Expected: FAIL because helpers do not exist.

- [ ] **Step 2: Add event registry**

```python
_EVENT_TYPES: dict[str, type[Event]] = {cls.__name__: cls for cls in (Event, ...)}
```

- [ ] **Step 3: Add envelope helpers**

```python
@dataclass
class EventEnvelope:
    event: str
    timestamp: str
    source: str
    priority: int
    ttl_seconds: float | None
    expires_at: str | None
    data: dict[str, Any]
```

- [ ] **Step 4: Update EventBus**

- `publish()` calls `_event_to_dict(event)` as before, now returning envelope fields.
- `_broadcast_to_websocket()` calls `event_to_envelope(event)` and passes the envelope payload.
- WebSocket failure logs with `logger.exception(...)`.

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/core/test_event_serialization.py -q
```

Expected: PASS.

---

## Self-review checklist

- [ ] Unknown event names raise `EventSchemaError` on deserialize.
- [ ] Missing required envelope fields raise `EventSchemaError`.
- [ ] `Event.timestamp` round-trips as ISO string.
- [ ] WebSocket broadcast failure logs stacktrace.
- [ ] No new dependency introduced.
