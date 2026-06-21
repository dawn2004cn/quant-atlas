"""Phase 57: SSE task push stream (replaces polling when supported)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import werkzeug

from app.modules.system.services.system.task_stream_service import TaskStreamService
from app.infrastructure.messaging.task_event_hub import TaskEventHub


def test_task_event_hub_publish_subscribe() -> None:
    hub = TaskEventHub()
    q = hub.subscribe("task-a")
    hub.publish("task-a", {"event": "task_started", "task_id": "task-a"})
    msg = q.get(timeout=1.0)
    assert msg["event"] == "task_started"
    hub.unsubscribe("task-a", q)


def test_task_stream_service_emits_ready_when_terminal() -> None:
    hub = TaskEventHub()
    with patch(
        "app.modules.system.services.system.task_stream_service.get_task_event_hub",
        return_value=hub,
    ):
        with patch(
            "app.modules.system.services.system.task_feedback_service.get_celery_task_status",
            side_effect=[
                {"ok": True, "state": "STARTED", "ready": False, "successful": False, "failed": False},
                {"ok": True, "state": "SUCCESS", "ready": True, "successful": True, "failed": False},
            ],
        ):
            svc = TaskStreamService()
            chunks = list(svc.iter_sse("tid-stream", timeout_sec=2.0, heartbeat_sec=0.05))
    assert chunks
    last_payload = json.loads(chunks[-1].replace("data: ", "").strip())
    assert last_payload.get("done") is True
    assert last_payload["feedback"]["state"] == "SUCCESS"


def test_task_stream_service_reacts_to_hub_event() -> None:
    import threading
    import time

    hub = TaskEventHub()
    with patch(
        "app.modules.system.services.system.task_stream_service.get_task_event_hub",
        return_value=hub,
    ):
        with patch(
            "app.modules.system.services.system.task_feedback_service.get_celery_task_status",
            return_value={"ok": True, "state": "STARTED", "ready": False, "successful": False, "failed": False},
        ):
            svc = TaskStreamService()
            gen = svc.iter_sse("tid-hub", timeout_sec=2.0, heartbeat_sec=1.0)
            first = next(gen)
            assert "data:" in first

            def publish_later() -> None:
                time.sleep(0.05)
                hub.publish("tid-hub", {"event": "task_succeeded", "task_id": "tid-hub"})

            threading.Thread(target=publish_later, daemon=True).start()
            second = next(gen)
            payload = json.loads(second.replace("data: ", "").strip())
            assert payload.get("event") == "task_succeeded"
            assert payload.get("done") is True


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    monkeypatch.setenv("ENABLE_BASIC_DATA_SCHEDULER", "0")
    monkeypatch.setenv("ENABLE_CELERY", "0")
    monkeypatch.setenv("ENABLE_QLIB", "0")
    monkeypatch.setenv("ENABLE_RD_AGENT", "0")
    monkeypatch.setenv("TASK_MESSAGE_REDIS_URL", "memory://")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)

    instance = tmp_path / "instance"
    instance.mkdir()
    monkeypatch.setattr("app.config.settings.INSTANCE_DIR", instance)

    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert login.status_code in (302, 303)
    return client


def test_task_stream_api(app_client) -> None:
    with patch(
        "app.modules.system.services.system.task_feedback_service.get_celery_task_status",
        return_value={"ok": True, "state": "SUCCESS", "ready": True, "successful": True, "failed": False},
    ):
        resp = app_client.get("/api/v1/system/tasks/done-task/stream")
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    assert b"done" in resp.data
