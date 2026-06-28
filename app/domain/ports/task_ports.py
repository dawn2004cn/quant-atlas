from __future__ import annotations
"""Task dispatcher ports - interfaces for async task execution."""


from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any


class TaskDispatcher(ABC):
    """Port for dispatching async tasks. Abstracts task queue backend (Celery, ARQ, etc)."""

    @abstractmethod
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
        """Dispatch task, return (AsyncResult, task_id, enqueued)."""
        raise NotImplementedError

    @abstractmethod
    def get_task_label(self, task_name: str) -> str:
        """Get human-readable label for task."""
        raise NotImplementedError


class MessageStore(ABC):
    """Port for task event logging."""

    @abstractmethod
    def push(
        self,
        *,
        event: str,
        task_id: str,
        task_name: str,
        detail: str = "",
        meta: dict[str, Any] | None = None,
    ) -> str:
        """Push task event message."""
        raise NotImplementedError

    @abstractmethod
    def list_recent(self, *, limit: int = 80) -> list[dict[str, Any]]:
        """List recent messages."""
        raise NotImplementedError

    @property
    @abstractmethod
    def enabled_backend(self) -> str:
        """Backend name (redis/memory)."""
        raise NotImplementedError
