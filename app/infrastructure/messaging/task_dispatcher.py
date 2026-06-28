from __future__ import annotations

"""Task dispatcher implementations wrapping existing infrastructure."""


from collections.abc import Mapping, Sequence
from typing import Any

from ...core.logger import get_logger
from ...infrastructure.messaging.celery_reliability import enqueue_task_idempotent
from ...infrastructure.messaging.task_message_store import TaskMessageStore, task_label

logger = get_logger(__name__)


from app.domain.ports.task_ports import TaskDispatcher


class CeleryTaskDispatcher(TaskDispatcher):
    """Celery-based task dispatcher implementation."""

    def dispatch(
        self,
        task: Any,
        *,
        task_name: str,
        args: Sequence[Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
        bucket_seconds: int | None = None,
        ttl_seconds: int | None = None,
    ) -> tuple[Any | None, str, bool]:
        return enqueue_task_idempotent(
            task,
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            bucket_seconds=bucket_seconds,
            ttl_seconds=ttl_seconds,
        )

    def get_task_label(self, task_name: str) -> str:
        return task_label(task_name)


class TaskMessageStoreAdapter:
    """Adapter wrapping TaskMessageStore as MessageStore port."""

    def __init__(self, delegate: TaskMessageStore) -> None:
        self._delegate = delegate

    def push(
        self,
        *,
        event: str,
        task_id: str,
        task_name: str,
        detail: str = "",
        meta: dict[str, Any] | None = None,
    ) -> str:
        return self._delegate.push(
            event=event,
            task_id=task_id,
            task_name=task_name,
            detail=detail,
            meta=meta,
        )

    def list_recent(self, *, limit: int = 80) -> list[dict[str, Any]]:
        return self._delegate.list_recent(limit=limit)

    @property
    def enabled_backend(self) -> str:
        return self._delegate.enabled_backend
