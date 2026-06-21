# P1 Event Bus Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make EventBus handler failures visible without changing publish semantics or breaking existing subscribers.

**Architecture:** Keep the event bus non-raising by default. On handler exceptions, log with stack context and append a bounded failure record that can be inspected by tests and diagnostics. Do not add async workers, persistence, or new services.

**Tech Stack:** Python 3.12, pytest.

---

### Task 1: Record EventBus handler failures

**Files:**
- Modify: `app/core/event_bus.py`
- Modify: `tests/core/test_event_bus_priority_ttl.py`

- [ ] **Step 1: Write the failing test**

```python
def test_handler_failure_is_recorded():
    bus = EventBus()
    bus.clear()
    failures = []

    def failing(_evt: TruthDeviationEvent) -> None:
        raise RuntimeError("boom")

    bus.subscribe(TruthDeviationEvent, failing)
    bus.publish(TruthDeviationEvent(source="test", symbol="600519", market="CN", diff_pct=1.0))
    failures = bus.list_handler_failures()
    assert failures[0]["event"] == "TruthDeviationEvent"
    assert failures[0]["handler"] == "failing"
    assert failures[0]["error"] == "boom"
```

Expected: FAIL because `list_handler_failures()` does not exist.

- [ ] **Step 2: Add bounded failure storage**

```python
from collections import deque
...
cls._instance._handler_failures = deque(maxlen=100)
```

- [ ] **Step 3: Replace swallowed handler exception logging**

```python
except Exception as e:
    logger.exception("Error in event handler %s for %s", reg.handler.__name__, event_name)
    self._handler_failures.appendleft({
        "event": event_name,
        "handler": reg.handler.__name__,
        "error": str(e),
        "timestamp": datetime.now().isoformat(),
    })
```

- [ ] **Step 4: Add list method**

```python
def list_handler_failures(self, *, limit: int = 50) -> list[dict[str, Any]]:
    lim = min(max(1, limit), 100)
    return list(self._handler_failures)[:lim]
```

- [ ] **Step 5: Update clear()**

```python
self._handler_failures.clear()
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/core/test_event_bus_priority_ttl.py -q
```

Expected: PASS.

---

## Self-review checklist

- [ ] EventBus still does not raise handler exceptions to callers.
- [ ] Handler failures are logged with stack context.
- [ ] `list_handler_failures()` exposes bounded recent failures.
- [ ] Existing priority/TTL behavior remains unchanged.
- [ ] No unrelated files are modified.
