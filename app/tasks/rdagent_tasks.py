from __future__ import annotations

"""RD-Agent 因子挖掘 Celery 任务；无 broker 时退化为可同步调用的函数。"""


import copy
import json
from typing import Any

from ..celery_app import celery as _celery
from ..config import BASE_DIR
from ..core.logger import get_logger
from ..core.runtime_config import get_runtime
from .task_wiring import (
    append_rdagent_factor_tasks_from_bundle,
    create_rdagent_artifact_registry,
    create_rdagent_job_store,
    execute_rdagent_qlib_gate,
    get_task_message_store,
    run_rdagent_factor_mining_loop,
)

logger = get_logger(__name__)


def _push_task_message(
    *,
    job_id: str,
    event: str,
    detail: str,
    meta: dict[str, Any] | None = None,
) -> None:
    if not job_id:
        return
    try:
        get_task_message_store().push(
            event=event,
            task_id=job_id,
            task_name="rdagent.run_factor_generation",
            detail=detail[:2000],
            meta=meta or {},
        )
    except Exception as exc:
        logger.debug("rdagent task message push skipped: %s", exc)


def _notify_webhook(job_id: str, result: dict[str, Any]) -> None:
    url = (get_runtime("RDAGENT_WEBHOOK_URL", "") or "").strip()
    if not url:
        return
    try:
        import urllib.request

        payload = json.dumps({"run_id": job_id, "ok": result.get("ok"), "result": result}, ensure_ascii=False).encode(
            "utf-8"
        )
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("rdagent webhook %s -> %s", url, resp.status)
    except Exception as exc:
        logger.warning("rdagent webhook failed: %s", exc)


def _strip_internal_keys(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if not str(k).startswith("_")}


def _run_with_job_store(task_params: dict[str, Any]) -> dict[str, Any]:
    job_id = task_params.get("_job_id")
    store = create_rdagent_job_store(BASE_DIR)
    params = _strip_internal_keys(task_params)

    def _progress(pct: int, msg: str) -> None:
        if job_id:
            store.update(job_id, progress=pct, message=msg, status="running")
            from app.infrastructure.realtime.sse_progress import publish_progress
            publish_progress(job_id, pct, msg)

    if job_id:
        store.update(job_id, status="running", progress=2, message="starting factor loop")

    try:
        result = run_rdagent_factor_mining_loop(params, progress=_progress if job_id else None)
    except Exception as exc:
        logger.exception("run_rdagent_factor_generation failed")
        if job_id:
            store.update(job_id, status="failed", progress=100, error=str(exc), message="failed")
            if not celery_rdagent_enabled():
                _push_task_message(
                    job_id=job_id,
                    event="task_failed",
                    detail=str(exc)[:1500],
                    meta={"phase": "run_factor_mining_loop"},
                )
        raise

    if job_id:
        store.update(
            job_id,
            status="completed",
            progress=100,
            message="done",
            result=result,
        )
        if result.get("ok"):
            try:
                create_rdagent_artifact_registry(BASE_DIR).register_from_result(job_id, result)
            except Exception as reg_exc:
                logger.warning("artifact registry failed for %s: %s", job_id, reg_exc)
            else:
                try:
                    exp = append_rdagent_factor_tasks_from_bundle(base_dir=BASE_DIR, run_id=job_id)
                    if exp.get("appended"):
                        logger.info("factor_catalog_export %s", exp)
                except Exception as exp_exc:
                    logger.warning("factor_catalog_export failed for %s: %s", job_id, exp_exc)
            try:
                execute_rdagent_qlib_gate(job_id, base_dir=BASE_DIR)
            except Exception as gate_exc:
                logger.warning("qlib gate failed for %s: %s", job_id, gate_exc)
            _notify_webhook(job_id, result)
            rep = result.get("report") or {}
            _push_task_message(
                job_id=job_id,
                event="task_succeeded",
                detail="RD-Agent 因子循环完成，产物已注册",
                meta={
                    "ok": True,
                    "round_count": rep.get("round_count"),
                    "provider_uri": result.get("provider_uri"),
                },
            )
        else:
            _push_task_message(
                job_id=job_id,
                event="task_succeeded",
                detail=f"RD-Agent 结束但未成功: {result.get('error', '')} {result.get('message', '')}"[:2000],
                meta={"ok": False, "error": result.get("error")},
            )

    if isinstance(result, dict):
        result["_suppress_default_task_message"] = True
    return result


if _celery is not None:

    @_celery.task(bind=True, name="rdagent.run_factor_generation")
    def run_rdagent_factor_generation(self, task_params: dict[str, Any]) -> dict[str, Any]:
        try:
            self.update_state(state="PROGRESS", meta={"progress": 5, "message": "queued to worker"})
        except Exception as e:
            logger.warning("rdagent_tasks.py.run_rdagent_factor_generation: %s", e)
        return _run_with_job_store(copy.deepcopy(task_params or {}))

else:

    def run_rdagent_factor_generation(task_params: dict[str, Any]) -> dict[str, Any]:
        """Celery 未配置 ``CELERY_BROKER_URL`` 时的同步入口（测试或线程内调用）。"""
        return _run_with_job_store(copy.deepcopy(task_params or {}))


def celery_rdagent_enabled() -> bool:
    return _celery is not None
