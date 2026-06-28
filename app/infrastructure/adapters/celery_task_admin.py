from __future__ import annotations
"""Celery inspect / AsyncResult / revoke，供消息中心与运维 API 使用。"""


from typing import Any


from ...core.logger import get_logger


logger = get_logger(__name__)


def _app() -> Any:
    try:
        from app.celery_app import celery as app

        return app
    except ImportError:
        return None


def celery_available() -> bool:
    app = _app()
    return app is not None


def inspect_snapshot(*, timeout: float = 2.0) -> dict[str, Any]:
    """聚合 ``active`` / ``reserved`` / ``scheduled`` / ``stats``；无 Worker 应答时 ``ok`` 为 False。"""
    app = _app()
    if app is None:
        return {
            "ok": False,
            "error": "celery_not_installed",
            "active_by_worker": {},
            "reserved_by_worker": {},
            "scheduled_by_worker": {},
            "stats": {},
            "active_tasks_flat": [],
            "ping": {},
        }
    insp = app.control.inspect(timeout=timeout)
    if insp is None:
        return {
            "ok": False,
            "error": "no_workers_responded",
            "active_by_worker": {},
            "reserved_by_worker": {},
            "scheduled_by_worker": {},
            "stats": {},
            "active_tasks_flat": [],
            "ping": {},
        }
    active = insp.active() or {}
    reserved = insp.reserved() or {}
    scheduled = insp.scheduled() or {}
    stats = insp.stats() or {}
    ping: dict[str, Any] = {}
    try:
        ping = app.control.ping(timeout=min(timeout, 1.0)) or {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("celery ping skipped: %s", exc)

    flat: list[dict[str, Any]] = []
    for worker, tlist in active.items():
        for t in tlist or []:
            flat.append(
                {
                    "worker": worker,
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "args": str(t.get("args", ""))[:400],
                    "kwargs": str(t.get("kwargs", ""))[:400],
                    "time_start": t.get("time_start"),
                    "acknowledged": t.get("acknowledged"),
                }
            )

    return {
        "ok": True,
        "error": None,
        "active_by_worker": active,
        "reserved_by_worker": reserved,
        "scheduled_by_worker": scheduled,
        "stats": stats,
        "active_tasks_flat": flat,
        "ping": ping,
    }


def _serialize_result(raw: Any, *, max_len: int = 2000) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (bool, int, float, str)):
        s = str(raw)
        return s if len(s) <= max_len else s[: max_len - 3] + "..."
    if isinstance(raw, dict):
        try:
            import json

            s = json.dumps(raw, ensure_ascii=False, default=str)
        except TypeError:
            s = str(raw)
        return s if len(s) <= max_len else s[: max_len - 3] + "..."
    s = str(raw)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


def task_status(task_id: str) -> dict[str, Any]:
    """``AsyncResult`` 状态；未知 id 多为 PENDING。"""
    app = _app()
    if app is None:
        return {"ok": False, "error": "celery_not_installed", "task_id": task_id}
    tid = (task_id or "").strip()
    if not tid:
        return {"ok": False, "error": "task_id_required", "task_id": tid}
    try:
        from celery.result import AsyncResult
    except ImportError:
        return {"ok": False, "error": "celery_not_installed", "task_id": tid}

    r = AsyncResult(tid, app=app)
    out: dict[str, Any] = {
        "ok": True,
        "task_id": tid,
        "state": r.state,
        "ready": r.ready(),
        "successful": r.successful() if r.ready() else False,
        "failed": r.failed() if r.ready() else False,
    }
    if r.ready():
        try:
            if r.successful():
                out["result"] = _serialize_result(r.result)
            else:
                out["result"] = _serialize_result(getattr(r, "result", None))
            tb = getattr(r, "traceback", None)
            if tb:
                out["traceback"] = str(tb)[-8000:]
        except Exception as exc:  # noqa: BLE001
            out["result_error"] = str(exc)[:500]
    return out


def revoke_task(task_id: str, *, terminate: bool = False) -> dict[str, Any]:
    """``revoke``；``terminate=True`` 时向 Worker 发 SIGTERM（Windows 上行为因池而异）。"""
    app = _app()
    if app is None:
        return {"ok": False, "error": "celery_not_installed"}
    tid = (task_id or "").strip()
    if not tid:
        return {"ok": False, "error": "task_id_required"}
    try:
        if terminate:
            app.control.revoke(tid, terminate=True)
        else:
            app.control.revoke(tid, terminate=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("celery revoke failed: %s", exc)
        return {"ok": False, "error": str(exc)[:800], "task_id": tid}
    return {"ok": True, "task_id": tid, "terminate": bool(terminate)}
