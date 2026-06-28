from __future__ import annotations

"""In-process pub/sub for Celery task lifecycle events (SSE push)."""

import logging
import queue
import threading
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)



class TaskEventHub:
    """Broadcast task events to SSE subscribers in the same process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: dict[str, list[queue.Queue[dict[str, Any]]]] = defaultdict(list)

    def publish(self, task_id: str, payload: dict[str, Any]) -> None:
        tid = (task_id or "").strip()
        if not tid:
            return
        with self._lock:
            targets = list(self._subs.get(tid, []))
        for target in targets:
            try:
                target.put_nowait(dict(payload))
            except queue.Full:
                logger.warning("Suppressed exception", exc_info=True)
                pass

    def subscribe(self, task_id: str) -> queue.Queue[dict[str, Any]]:
        tid = (task_id or "").strip()
        target: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=32)
        with self._lock:
            self._subs[tid].append(target)
        return target

    def unsubscribe(self, task_id: str, target: queue.Queue[dict[str, Any]]) -> None:
        tid = (task_id or "").strip()
        with self._lock:
            subs = self._subs.get(tid, [])
            if target in subs:
                subs.remove(target)
            if not subs and tid in self._subs:
                del self._subs[tid]


_hub: TaskEventHub | None = None
_hub_lock = threading.Lock()


def get_task_event_hub() -> TaskEventHub:
    global _hub
    with _hub_lock:
        if _hub is None:
            _hub = TaskEventHub()
        return _hub


__all__ = ["TaskEventHub", "get_task_event_hub"]
