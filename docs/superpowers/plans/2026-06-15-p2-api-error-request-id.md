# P2 API Error Request ID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add request tracing to API error responses so production incidents can be correlated without leaking exception details.

**Architecture:** Generate or preserve `X-Request-ID` for API error payloads and headers. Keep existing application-error mapping behavior. Add small compatibility mappers for existing tests.

**Tech Stack:** Python 3.12, Flask, pytest.

---

### Task 1: Add request_id to API error payloads

**Files:**
- Modify: `app/presentation/api/error_handlers.py`
- Modify: `tests/test_api_error_handlers.py`

- [ ] **Step 1: Write failing tests**

```python
def test_unexpected_error_includes_request_id():
    app = Flask(__name__)
    with app.test_request_context("/api/test", headers={"X-Request-ID": "req-1"}):
        payload, status = map_unexpected_error(RuntimeError("boom"))
    assert status == 500
    assert payload["request_id"] == "req-1"
    assert payload["error"]["details"]["request_id"] == "req-1"
```

Expected: FAIL because no `request_id` exists.

- [ ] **Step 2: Add request_id helpers**

```python
import uuid
from flask import Flask, has_request_context, jsonify, request, redirect, url_for
...
def _request_id() -> str:
    if has_request_context():
        return request.headers.get("X-Request-ID") or request.environ.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
    return str(uuid.uuid4())
```

- [ ] **Step 3: Add request_id to HTTP and unexpected payloads**

```python
rid = _request_id()
payload = {
    "status": "error",
    "request_id": rid,
    "error": {
        "code": code,
        "message": message,
        "details": {"path": request.path, "request_id": rid},
    },
}
```

- [ ] **Step 4: Add compatibility mappers**

```python
def map_application_error(error):
    return error.to_payload(), error.status_code

def map_authorization_error(error):
    return error.to_payload(), error.status_code
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_api_error_handlers.py -q
```

Expected: PASS.

---

## Self-review checklist

- [ ] Existing `X-Request-ID` is preserved.
- [ ] Missing request ID gets a generated UUID.
- [ ] 500 responses do not expose exception details.
- [ ] Existing application error mappers are available for tests.
- [ ] No unrelated UI or business logic changes are introduced.
