from __future__ import annotations

"""Recover active async jobs from task message history."""

from typing import Any

from app.modules.system.services.system.task_feedback_service import TaskFeedbackService

_TERMINAL_EVENTS = {
    "task_succeeded",
    "task_failed",
    "task_revoked",
    "task_completed",
    "task_success",
}


class ActiveJobTrackerService:
    """List non-terminal jobs so refreshed pages can resume progress UI."""

    def __init__(
        self,
        *,
        task_message_store: Any = None,
        task_feedback_service: TaskFeedbackService | None = None,
    ) -> None:
        self._task_message_store = task_message_store
        self._feedback = task_feedback_service or TaskFeedbackService()

    def list_active_jobs(self, *, user_id: str | int | None = None, limit: int = 20) -> dict[str, Any]:
        rows = self._recent_messages(limit=max(limit * 10, 80))
        latest_by_task: dict[str, dict[str, Any]] = {}
        for row in rows:
            task_id = str(row.get("task_id") or "").strip()
            if not task_id:
                continue
            if user_id is not None:
                meta_user = (row.get("meta") or {}).get("user_id")
                if meta_user is not None and str(meta_user) != str(user_id):
                    continue
            latest_by_task.setdefault(task_id, row)

        active = []
        for task_id, row in latest_by_task.items():
            event = str(row.get("event") or "").lower()
            if event in _TERMINAL_EVENTS:
                continue
            feedback = self._feedback.build_feedback(
                task_id,
                task_name=row.get("task_name"),
            )
            if feedback.get("ready"):
                continue
            active.append(
                {
                    "task_id": task_id,
                    "task_name": row.get("task_name"),
                    "label": row.get("label"),
                    "last_event": row.get("event"),
                    "last_detail": row.get("detail"),
                    "last_seen_at": row.get("ts"),
                    "feedback": feedback,
                }
            )
            if len(active) >= limit:
                break
        return {"items": active, "count": len(active)}

    def _recent_messages(self, *, limit: int) -> list[dict[str, Any]]:
        if self._task_message_store is None:
            return []
        try:
            return self._task_message_store.list_recent(limit=limit)
        except Exception:
            return []


__all__ = ["ActiveJobTrackerService"]
