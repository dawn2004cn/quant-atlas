from __future__ import annotations

"""Aggregate Celery status, task messages and phase progress for UI feedback."""

from typing import Any

from app.modules.system.services.helpers.task_message_access import get_task_message_store
from app.modules.system.services.helpers.task_ops_access import get_celery_task_status
from app.modules.system.services.system.task_phase_plan_service import TaskPhasePlanService
from app.infrastructure.messaging.task_progress_store import TaskProgressStore

_TERMINAL_STATES = frozenset({"SUCCESS", "FAILURE", "REVOKED"})


class TaskFeedbackService:
    """Build a poll-friendly feedback dict for async task UIs."""

    def __init__(
        self,
        *,
        progress_store: TaskProgressStore | None = None,
        message_store_factory: Any | None = None,
        phase_plan_service: TaskPhasePlanService | None = None,
    ) -> None:
        self._progress = progress_store or TaskProgressStore()
        self._message_store_factory = message_store_factory or get_task_message_store
        self._phase_plan = phase_plan_service or TaskPhasePlanService()

    def build_feedback(
        self,
        task_id: str,
        *,
        task_name: str | None = None,
        estimated_steps: list[str] | None = None,
    ) -> dict[str, Any]:
        tid = (task_id or "").strip()
        celery = get_celery_task_status(tid) if tid else {"ok": False, "state": "UNKNOWN"}
        state = str(celery.get("state") or "PENDING").upper()
        progress = self._progress.get(tid) or {}
        events = self._events_for_task(tid)
        resolved_task_name = task_name or progress.get("task_name") or celery.get("name")

        phase_progress = self._phase_plan.build_progress(
            task_name=resolved_task_name,
            estimated_steps=estimated_steps,
            progress=progress,
            state=state,
        )

        ready = bool(celery.get("ready")) or state in _TERMINAL_STATES
        successful = bool(celery.get("successful")) if celery.get("ready") else state == "SUCCESS"
        message = str(progress.get("message") or self._default_message(state, events))

        result_preview = None
        if ready and celery.get("result") is not None:
            result_preview = celery.get("result")

        return {
            "task_id": tid,
            "task_name": resolved_task_name,
            "state": state,
            "ready": ready,
            "successful": successful,
            "failed": bool(celery.get("failed")) if celery.get("ready") else state == "FAILURE",
            "percent": phase_progress["percent"],
            "step_index": phase_progress["step_index"],
            "steps": phase_progress["steps"],
            "step_details": phase_progress["step_details"],
            "current_step": phase_progress["current_step"],
            "current_step_key": phase_progress["current_step_key"],
            "next_step": phase_progress["next_step"],
            "phase_source": phase_progress["phase_source"],
            "message": message,
            "events": events[:20],
            "result_preview": result_preview,
        }

    def _events_for_task(self, task_id: str) -> list[dict[str, Any]]:
        if not task_id:
            return []
        try:
            store = self._message_store_factory()
            rows = store.list_recent(limit=200)
        except Exception:
            return []
        return [row for row in rows if str(row.get("task_id") or "") == task_id]

    @staticmethod
    def _default_message(state: str, events: list[dict[str, Any]]) -> str:
        if events:
            detail = str(events[0].get("detail") or "").strip()
            if detail:
                return detail
        mapping = {
            "PENDING": "Task is queued.",
            "STARTED": "Task is running.",
            "PROGRESS": "Task is processing.",
            "SUCCESS": "Task completed.",
            "FAILURE": "Task failed.",
            "REVOKED": "Task was revoked.",
        }
        return mapping.get(state, "Waiting for worker response.")
