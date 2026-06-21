"""任务消息存储（内存回退）。"""

from __future__ import annotations

from app.infrastructure.messaging.task_message_store import TaskMessageStore, configure_task_message_store


def test_memory_store_push_and_list() -> None:
    configure_task_message_store("memory://")
    s = TaskMessageStore("memory://")
    mid = s.push(
        event="task_queued",
        task_id="t-1",
        task_name="app.tasks.market_tasks.refresh_basic_market_data",
        detail="test",
    )
    assert mid
    rows = s.list_recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["event"] == "task_queued"
    assert rows[0]["label"] == "基础数据·手动刷新"
