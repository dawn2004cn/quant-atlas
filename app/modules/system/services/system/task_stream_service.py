from __future__ import annotations

"""Server-Sent Events stream for async task feedback (Phase 57)."""

import json
import queue
import time
from collections.abc import Iterator
from typing import Any

from app.infrastructure.messaging.task_event_hub import get_task_event_hub
from app.modules.system.services.system.task_feedback_service import TaskFeedbackService

_TERMINAL_EVENTS = frozenset({"task_succeeded", "task_failed", "task_revoked"})


class TaskStreamService:
    """Push task feedback over SSE; complements poll-based ``TaskFeedbackService``."""

    def __init__(self, *, feedback_service: TaskFeedbackService | None = None) -> None:
        self._feedback = feedback_service or TaskFeedbackService()

    def iter_sse(
        self,
        task_id: str,
        *,
        task_name: str | None = None,
        estimated_steps: list[str] | None = None,
        timeout_sec: float = 120.0,
        heartbeat_sec: float = 15.0,
    ) -> Iterator[str]:
        tid = (task_id or "").strip()
        if not tid:
            yield self._format({"feedback": {"task_id": "", "ready": True}, "done": True})
            return

        feedback = self._build(tid, task_name=task_name, estimated_steps=estimated_steps)
        yield self._format({"feedback": feedback, "done": bool(feedback.get("ready"))})
        if feedback.get("ready"):
            return

        hub = get_task_event_hub()
        sub = hub.subscribe(tid)
        deadline = time.monotonic() + max(timeout_sec, 5.0)
        try:
            while time.monotonic() < deadline:
                try:
                    evt = sub.get(timeout=heartbeat_sec)
                except queue.Empty:
                    feedback = self._build(tid, task_name=task_name, estimated_steps=estimated_steps)
                    done = bool(feedback.get("ready"))
                    yield self._format({"feedback": feedback, "done": done})
                    if done:
                        return
                    yield ": heartbeat\n\n"
                    continue

                feedback = self._build(tid, task_name=task_name, estimated_steps=estimated_steps)
                done = bool(feedback.get("ready")) or str(evt.get("event") or "") in _TERMINAL_EVENTS
                yield self._format({"feedback": feedback, "event": evt.get("event"), "done": done})
                if done:
                    return
        finally:
            hub.unsubscribe(tid, sub)

    def _build(
        self,
        task_id: str,
        *,
        task_name: str | None,
        estimated_steps: list[str] | None,
    ) -> dict[str, Any]:
        return self._feedback.build_feedback(
            task_id,
            task_name=task_name,
            estimated_steps=estimated_steps,
        )

    @staticmethod
    def _format(payload: dict[str, Any]) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


__all__ = ["TaskStreamService"]
