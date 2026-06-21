"""Phase 51: async task feedback API + progress store."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import werkzeug

from app.modules.system.services.system.task_feedback_service import TaskFeedbackService
from app.infrastructure.messaging.task_progress_store import TaskProgressStore


def test_task_progress_store_init_and_update(tmp_path: Path) -> None:
    store = TaskProgressStore(tmp_path / "progress")
    store.init("task-1", task_name="demo.task", steps=["A", "B", "C"])
    store.update("task-1", step_index=1, message="running")
    data = store.get("task-1")
    assert data is not None
    assert data["step_index"] == 1
    assert data["percent"] >= 33


def test_task_feedback_service_merges_progress(tmp_path: Path) -> None:
    store = TaskProgressStore(tmp_path / "progress")
    store.init("tid-99", task_name="x.y", steps=["排队", "执行", "完成"])
    store.update("tid-99", step_index=1, message="执行中")
    svc = TaskFeedbackService(progress_store=store)
    with patch(
        "app.modules.system.services.system.task_feedback_service.get_celery_task_status",
        return_value={"ok": True, "state": "STARTED", "ready": False, "successful": False, "failed": False},
    ):
        fb = svc.build_feedback("tid-99")
    assert fb["percent"] >= 40
    assert fb["steps"] == ["排队", "执行", "完成"]
    assert fb["message"]


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


def test_task_feedback_api(app_client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.config.settings.INSTANCE_DIR", tmp_path / "instance")
    (tmp_path / "instance").mkdir(exist_ok=True)
    from app.tasks.task_wiring import init_task_progress

    init_task_progress("api-task-1", task_name="demo", steps=["S1", "S2"])
    with patch(
        "app.modules.system.services.system.task_feedback_service.get_celery_task_status",
        return_value={"ok": True, "state": "PENDING", "ready": False, "successful": False, "failed": False},
    ):
        resp = app_client.get("/api/v1/system/tasks/api-task-1/feedback")
    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert data.get("task_id") == "api-task-1"
    assert data.get("steps")


def test_task_center_includes_feedback_js(app_client) -> None:
    resp = app_client.get("/task-center")
    assert resp.status_code == 200
    assert b"task_feedback.js" in resp.data
