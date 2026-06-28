from __future__ import annotations

"""Market data Celery tasks (longhu, yanbao, indices)."""

from datetime import datetime, timedelta
from typing import Any

from ..celery_app import celery as _celery
from ..core.logger import get_logger
from .task_wiring import create_basic_market_data_service

logger = get_logger(__name__)

_TASK_NAME = "app.tasks.market_tasks.refresh_basic_market_data"


def _service():
    return create_basic_market_data_service(with_longhu_adapter=True)


def _refresh_steps(kind: str) -> list[str]:
    k = str(kind or "all").strip().lower()
    steps: list[str] = []
    if k in ("all", "longhu"):
        steps.append("龙虎榜入库")
    if k in ("all", "yanbao"):
        steps.append("研报入库")
    steps.append("完成")
    return steps or ["执行", "完成"]


def _run_refresh(kind: str, *, task_id: str | None = None) -> dict[str, Any]:
    k = str(kind or "all").strip().lower()
    out: dict[str, Any] = {}
    svc = _service()
    steps = _refresh_steps(k)
    step_idx = 0

    if task_id:
        try:
            from app.tasks.task_wiring import init_task_progress, report_task_progress

            init_task_progress(task_id, task_name=_TASK_NAME, steps=steps)
            report_task_progress(task_id, step_index=step_idx, message=steps[step_idx])
        except Exception as exc:
            logger.debug("refresh_basic_market_data progress init: %s", exc)

    if k in ("all", "longhu"):
        if task_id:
            try:
                from app.tasks.task_wiring import report_task_progress

                report_task_progress(task_id, step_index=step_idx, message="正在拉取龙虎榜…")
            except Exception as exc:
                logger.debug("refresh progress longhu: %s", exc)
        out["longhu"] = svc.ingest_longhu_em(lookback_calendar_days=14)
        step_idx += 1
        if task_id and step_idx < len(steps):
            try:
                from app.tasks.task_wiring import report_task_progress

                report_task_progress(
                    task_id,
                    step_index=min(step_idx, len(steps) - 1),
                    message=f"龙虎榜完成，下一步：{steps[step_idx]}",
                )
            except Exception as exc:
                logger.debug("refresh progress after longhu: %s", exc)

    if k in ("all", "yanbao"):
        if task_id:
            try:
                from app.tasks.task_wiring import report_task_progress

                report_task_progress(
                    task_id,
                    step_index=min(step_idx, len(steps) - 1),
                    message="正在拉取研报…",
                )
            except Exception as exc:
                logger.debug("refresh progress yanbao: %s", exc)
        end = datetime.now()
        begin = end - timedelta(days=30)
        out["yanbao"] = svc.ingest_yanbao_eastmoney_api(
            begin=begin.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            page_size=200,
            max_pages=20,
            sleep_sec=0.2,
        )
        step_idx += 1

    if task_id:
        try:
            from app.tasks.task_wiring import report_task_progress

            report_task_progress(
                task_id,
                step_index=max(len(steps) - 1, 0),
                message="基础市场数据刷新完成",
                percent=100,
            )
        except Exception as exc:
            logger.debug("refresh progress finalize: %s", exc)

    return out


if _celery is not None:

    @_celery.task(name=_TASK_NAME, bind=True)
    def refresh_basic_market_data(self, kind: str = "all") -> dict[str, Any]:
        task_id = getattr(getattr(self, "request", None), "id", None)
        return _run_refresh(kind, task_id=str(task_id) if task_id else None)

    @_celery.task(name="app.tasks.market_tasks.scheduled_indices_sync")
    def scheduled_indices_sync() -> dict[str, Any]:
        """Daily index backfill (CSI300, SSE, ChiNext, etc.)."""
        from scripts.backfill_all_indices import backfill_all_indices

        logger.info("Starting scheduled_indices_sync...")
        try:
            backfill_all_indices()
            return {"ok": True}
        except Exception as e:
            logger.exception("scheduled_indices_sync failed")
            return {"ok": False, "error": str(e)}

    @_celery.task(name="app.tasks.market_tasks.scheduled_longhu")
    def scheduled_longhu() -> dict[str, Any]:
        return _service().ingest_longhu_em(lookback_calendar_days=14)

    @_celery.task(name="app.tasks.market_tasks.scheduled_yanbao")
    def scheduled_yanbao() -> dict[str, Any]:
        end = datetime.now()
        begin = end - timedelta(days=30)
        return _service().ingest_yanbao_eastmoney_api(
            begin=begin.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            page_size=200,
            max_pages=20,
            sleep_sec=0.2,
        )

else:
    refresh_basic_market_data = None  # type: ignore[misc, assignment]
    scheduled_longhu = None  # type: ignore[misc, assignment]
    scheduled_yanbao = None  # type: ignore[misc, assignment]
