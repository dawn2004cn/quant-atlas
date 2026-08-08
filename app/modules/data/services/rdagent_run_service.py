"""RD-Agent run service - job submission, status query, artifact listing."""

from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

from app.modules.system.services.helpers.rdagent_access import (
    create_rdagent_artifact_registry,
    create_rdagent_job_store,
    get_rdagent_validation_port,
)
from app.config import BASE_DIR
from app.core.logger import get_logger
from app.core.registry import register_service
from app.domain.ports.task_ports import TaskDispatcher
from app.domain.services.rdagent_config import parse_rdagent_loop_params

logger = get_logger(__name__)


def _log_summary_from_job(row: dict[str, Any], max_len: int = 4000) -> str:
    res = row.get("result")
    if not isinstance(res, dict):
        return ""
    rep = res.get("report") or {}
    rounds = rep.get("rounds") or []
    if not rounds:
        return ""
    last = rounds[-1]
    parts: list[str] = []
    obs = last.get("observations") or ""
    if obs:
        parts.append(f"observations: {obs[: max_len // 2]}")
    ev = last.get("hypothesis_evaluation") or ""
    if ev:
        parts.append(f"evaluation: {ev[: max_len // 2]}")
    out = "\n".join(parts)
    return out[:max_len]


@register_service(name="rdagent_run_service")
class RDAgentRunService:
    def __init__(
        self,
        base_dir: Path | None = None,
        task_dispatcher: TaskDispatcher | None = None,
    ) -> None:
        self._base = Path(base_dir or BASE_DIR)
        self._store = create_rdagent_job_store(self._base)
        self._registry = create_rdagent_artifact_registry(self._base)
        self._task_dispatcher = task_dispatcher

    def submit_run(self, body: dict[str, Any]) -> dict[str, Any]:
        """Map roadmap request body to task params and execute async."""
        get_rdagent_validation_port().validate_submission(body, base_dir=self._base)
        ds = body.get("data_scope") if isinstance(body.get("data_scope"), dict) else {}
        budget = body.get("budget") if isinstance(body.get("budget"), dict) else {}
        summary = {
            "loop_n": body.get("loop_n") if body.get("loop_n") is not None else budget.get("max_loops"),
            "market": ds.get("market") or body.get("market"),
            "provider_uri": ds.get("provider_uri") or body.get("provider_uri"),
            "search_space": body.get("search_space"),
        }
        job_id = self._store.create(params_summary={k: v for k, v in summary.items() if v is not None})

        task_params = self._body_to_loop_params(body)
        task_params["_job_id"] = job_id
        payload = copy.deepcopy(task_params)

        if self._task_dispatcher is not None:
            from app.tasks.rdagent_tasks import celery_rdagent_enabled, run_rdagent_factor_generation

            if not celery_rdagent_enabled():
                raise RuntimeError("Celery broker not configured. Set CELERY_BROKER_URL in environment.")

            task = run_rdagent_factor_generation
            if not callable(getattr(task, "apply_async", None)):
                raise TypeError(
                    f"Task is not a Celery task (got {type(task).__name__}). "
                    f"This may indicate Celery initialization order issue."
                )

            self._task_dispatcher.dispatch(
                task,
                task_name="app.tasks.rdagent_tasks.run_rdagent_factor_generation",
                args=[{**payload, "_job_id": job_id}],
            )
            mode = "dispatcher"
        else:
            from app.tasks.rdagent_tasks import run_rdagent_factor_generation

            def _worker() -> None:
                run_rdagent_factor_generation({**payload, "_job_id": job_id})

            threading.Thread(target=_worker, daemon=True).start()
            mode = "thread"

        return {
            "run_id": job_id,
            "task_id": job_id,
            "progress": 0,
            "status": "queued",
            "execution_mode": mode,
        }

    @staticmethod
    def _body_to_loop_params(body: dict[str, Any]) -> dict[str, Any]:
        """Map roadmap data_scope/budget/search_space to factor loop params."""
        return parse_rdagent_loop_params(body)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._store.get(run_id)
        if row is None:
            return None
        data = dict(row)
        data["log_summary"] = _log_summary_from_job(row)
        err = data.get("error")
        if err:
            data["error_message"] = err
        return data

    def get_artifacts(self, run_id: str) -> dict[str, Any]:
        bundle = self._registry.get_run_bundle(run_id)
        if bundle is None:
            return {
                "run_id": run_id,
                "artifacts": [],
                "note": "no artifacts registered yet (job running or failed before registration)",
            }
        return {
            "run_id": run_id,
            "registered_at": bundle.get("registered_at"),
            "artifacts": bundle.get("artifacts") or [],
            "metrics_context": {
                "provider_uri": bundle.get("provider_uri"),
                "market": bundle.get("market"),
                "benchmark": bundle.get("benchmark"),
                "loop_n": bundle.get("loop_n"),
                "round_count": bundle.get("round_count"),
            },
        }

    def list_recent_runs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return self._registry.list_registry_index(limit=limit)


def create_default_rdagent_run_service() -> RDAgentRunService:
    return RDAgentRunService(base_dir=BASE_DIR)
