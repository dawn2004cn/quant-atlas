"""Tests for core celery infrastructure components.

Covers:
- BeatRegistry: declarative beat schedule registry
- celery_reliability: idempotent enqueue, claim/release keys
- TaskProgressStore: progress persistence (memory/file)
- TaskMessageStore: message push/list (memory backend)
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest


# -- BeatRegistry tests ------------------------------------------------

class TestBeatRegistry:
    """BeatRegistry: declarative beat schedule with runtime metadata."""

    def _import(self):
        from app.core.celery_ext import BeatRegistry
        BeatRegistry.clear()
        return BeatRegistry

    def test_register_and_list(self):
        Registry = self._import()
        from celery.schedules import crontab
        Registry.register("test-task", "app.tasks.test.run", crontab(minute="*/5"),
                          description="Test task", queue="high")
        tasks = Registry.list_tasks()
        names = [t["name"] for t in tasks]
        assert "test-task" in names
        task = Registry.get_task("test-task")
        assert task is not None
        assert task.task_path == "app.tasks.test.run"
        assert task.queue == "high"

    def test_build_schedule_respects_enabled_flag(self):
        Registry = self._import()
        from celery.schedules import crontab
        Registry.clear()
        Registry.register("enabled-task", "app.tasks.enabled.run", crontab(minute="*"), enabled=True)
        Registry.register("disabled-task", "app.tasks.disabled.run", crontab(minute="*"), enabled=False)
        schedule = Registry.build_schedule()
        assert "enabled-task" in schedule
        assert "disabled-task" not in schedule

    def test_enable_disable(self):
        Registry = self._import()
        from celery.schedules import crontab
        Registry.clear()
        Registry.register("togglable", "app.tasks.toggle.run", crontab(minute="*"), enabled=False)
        assert Registry.get_task("togglable").enabled is False
        Registry.enable("togglable", True)
        assert Registry.get_task("togglable").enabled is True

    def test_record_run_updates_metrics(self):
        Registry = self._import()
        from celery.schedules import crontab
        Registry.clear()
        Registry.register("metrics-task", "app.tasks.metrics.run", crontab(minute="*"))
        Registry.record_run("metrics-task", success=True, duration_ms=150.0)
        task = Registry.get_task("metrics-task")
        assert task.run_count == 1
        assert task.last_success is True
        assert task.last_duration_ms == 150.0

    def test_record_failure_increments_fail_count(self):
        Registry = self._import()
        from celery.schedules import crontab
        Registry.clear()
        Registry.register("fail-task", "app.tasks.fail.run", crontab(minute="*"))
        Registry.record_run("fail-task", success=False)
        task = Registry.get_task("fail-task")
        assert task.run_count == 1
        assert task.fail_count == 1

    def test_clear_removes_all_tasks(self):
        Registry = self._import()
        from celery.schedules import crontab
        Registry.clear()
        Registry.register("clear-test", "app.tasks.clear.run", crontab(minute="*"))
        assert len(Registry.list_tasks()) == 1
        Registry.clear()
        assert len(Registry.list_tasks()) == 0

    def test_as_beat_entry_has_expected_structure(self):
        Registry = self._import()
        from celery.schedules import crontab
        Registry.clear()
        Registry.register("entry-test", "app.tasks.entry.run", crontab(minute="*/10"),
                          queue="low", key="val")
        entry = Registry.get_task("entry-test").as_beat_entry
        assert entry["task"] == "app.tasks.entry.run"
        assert entry["options"]["queue"] == "low"
        assert entry["kwargs"]["key"] == "val"

    def test_thread_safety(self):
        Registry = self._import()
        from celery.schedules import crontab
        import threading
        Registry.clear()

        def _register(i: int):
            Registry.register(f"thread-task-{i}", f"app.tasks.thread.{i}", crontab(minute="*"))

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        tasks = Registry.list_tasks()
        assert len(tasks) == 20


# -- celery_reliability tests (memory fallback) ------------------------

class TestCeleryReliability:
    """celery_reliability: idempotency key and task ID building."""

    def test_build_idempotency_task_id_consistent(self):
        from app.infrastructure.messaging.celery_reliability import build_idempotency_task_id
        id1 = build_idempotency_task_id(task_name="app.tasks.test.run", args=("AAPL",), kwargs={"force": True})
        id2 = build_idempotency_task_id(task_name="app.tasks.test.run", args=("AAPL",), kwargs={"force": True})
        assert id1 == id2
        assert id1.startswith("idem-")

    def test_build_idempotency_task_id_different_args(self):
        from app.infrastructure.messaging.celery_reliability import build_idempotency_task_id
        id1 = build_idempotency_task_id(task_name="app.tasks.test.run", args=("AAPL",))
        id2 = build_idempotency_task_id(task_name="app.tasks.test.run", args=("MSFT",))
        assert id1 != id2

    def test_memory_claim_success(self):
        from app.infrastructure.messaging.celery_reliability import claim_idempotency_key
        assert claim_idempotency_key("test:key:1", ttl_seconds=10) is True

    def test_memory_claim_duplicate(self):
        from app.infrastructure.messaging.celery_reliability import claim_idempotency_key, release_idempotency_key
        release_idempotency_key("test:key:dup")
        assert claim_idempotency_key("test:key:dup", ttl_seconds=10) is True
        assert claim_idempotency_key("test:key:dup", ttl_seconds=10) is False

    def test_memory_release(self):
        from app.infrastructure.messaging.celery_reliability import claim_idempotency_key, release_idempotency_key
        release_idempotency_key("test:key:release")
        assert claim_idempotency_key("test:key:release", ttl_seconds=10) is True
        release_idempotency_key("test:key:release")
        assert claim_idempotency_key("test:key:release", ttl_seconds=10) is True

    def test_enqueue_idempotent_rejects_non_task(self):
        from app.infrastructure.messaging.celery_reliability import enqueue_task_idempotent
        with pytest.raises(TypeError, match="not a Celery task"):
            enqueue_task_idempotent("not_a_task", task_name="test")


# -- TaskProgressStore tests -------------------------------------------

class TestTaskProgressStore:
    """TaskProgressStore with memory/file backends."""

    @pytest.fixture
    def store(self):
        import tempfile
        from pathlib import Path
        from app.infrastructure.messaging.task_progress_store import TaskProgressStore
        _tmp = Path(tempfile.mkdtemp())
        return TaskProgressStore(root=_tmp, redis_url=None)

    def test_init_creates_payload(self, store):
        payload = store.init("task-1", task_name="test task", steps=["A", "B", "C"])
        assert payload["task_id"] == "task-1"
        assert payload["percent"] == 0

    def test_update_percent(self, store):
        store.init("task-2")
        updated = store.update("task-2", percent=50)
        assert updated["percent"] == 50.0

    def test_update_step_index(self, store):
        store.init("task-3", steps=["A", "B", "C"])
        updated = store.update("task-3", step_index=1, message="doing B")
        assert updated["step_index"] == 1

    def test_update_auto_percent(self, store):
        store.init("task-4", steps=["A", "B", "C", "D"])
        updated = store.update("task-4", step_index=2)
        assert updated["percent"] == 75.0

    def test_get_on_empty_returns_none(self, store):
        assert store.get("nonexistent") is None

    def test_get_returns_saved(self, store):
        store.init("task-get", task_name="get_test")
        result = store.get("task-get")
        assert result is not None
        assert result["task_name"] == "get_test"

    def test_persistence_across_instances(self):
        import tempfile
        from pathlib import Path
        from app.infrastructure.messaging.task_progress_store import TaskProgressStore
        _tmp = Path(tempfile.mkdtemp())
        s1 = TaskProgressStore(root=_tmp)
        s1.init("task-persist", task_name="persist_test")
        s1.update("task-persist", percent=100)
        s2 = TaskProgressStore(root=_tmp)
        result = s2.get("task-persist")
        assert result["percent"] == 100.0


# -- TaskMessageStore tests (memory backend) ---------------------------

class TestTaskMessageStore:
    """TaskMessageStore with memory backend."""

    @pytest.fixture
    def store(self):
        from app.infrastructure.messaging.task_message_store import TaskMessageStore
        return TaskMessageStore("memory://")

    def test_push_returns_id(self, store):
        msg_id = store.push(event="task_started", task_id="t1", task_name="app.tasks.test.run")
        assert isinstance(msg_id, str)
        assert len(msg_id) > 0

    def test_list_recent_returns_recent_first(self, store):
        store.push(event="task_started", task_id="t1", task_name="task.A")
        store.push(event="task_succeeded", task_id="t2", task_name="task.B")
        items = store.list_recent(limit=10)
        assert items[0]["task_id"] == "t2"

    def test_list_recent_respects_limit(self, store):
        for i in range(10):
            store.push(event="task_started", task_id=f"t{i}", task_name=f"task.{i}")
        items = store.list_recent(limit=3)
        assert len(items) == 3

    def test_list_recent_empty(self, store):
        items = store.list_recent(limit=10)
        assert items == []

    def test_enabled_backend(self, store):
        assert store.enabled_backend == "memory"

    def test_push_metadata(self, store):
        store.push(event="task_failed", task_id="t-fail", task_name="task.fail",
                   detail="error msg", meta={"key": "val"})
        items = store.list_recent(limit=10)
        match = [m for m in items if m["task_id"] == "t-fail"]
        assert match[0]["event"] == "task_failed"
        assert match[0]["meta"]["key"] == "val"
