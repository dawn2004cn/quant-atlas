"""Signal-flag historical backfill route."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.logger import get_logger
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_bool_param, parse_int_param
from app.presentation.api.v1.signal_flag._helpers import parse_signal_flag_max_stocks
from app.presentation.api.v1.signal_flag.runtime import SignalFlagRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def register_signal_flag_backfill_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: SignalFlagRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.post("/signal-flag/backfill")
    @login_required
    def signal_flag_backfill():
        """信号旗历史回填：从 start_date 起按交易日逐日扫描并入库（建议走 Celery）。"""
        body = request.get_json(silent=True) or {}
        start = (body.get("start_date") or "2020-01-01").strip()[:10]
        end = (body.get("end_date") or "").strip()[:10] or None
        max_stocks = parse_signal_flag_max_stocks(body)
        lookback = parse_int_param(body.get("lookback_days"), name="lookback_days", default=160, min_value=40)
        lookback = min(lookback, 500)
        limit_days = parse_int_param(body.get("limit_days"), name="limit_days", default=0, min_value=0)
        limit_days = min(limit_days, 6000)
        sync = parse_bool_param(request.args.get("sync"), name="sync", default=False)

        task_dispatcher = runtime.task_dispatcher
        task_message_store = runtime.task_message_store

        if runtime.enable_celery and not sync and task_dispatcher is not None:
            try:
                from app.celery_app import celery as _celery
                from app.tasks.signal_flag_tasks import signal_flag_pool_backfill

                if (
                    _celery is not None
                    and signal_flag_pool_backfill is not None
                    and hasattr(signal_flag_pool_backfill, "delay")
                ):
                    _, task_id, enqueued = task_dispatcher.dispatch(
                        signal_flag_pool_backfill,
                        task_name="app.tasks.signal_flag_tasks.signal_flag_pool_backfill",
                        kwargs={
                            "start_date": start,
                            "end_date": end,
                            "max_stocks": int(max_stocks),
                            "lookback_days": int(lookback),
                            "limit_days": int(limit_days),
                        },
                        bucket_seconds=300,
                        ttl_seconds=1800,
                    )
                    if not enqueued:
                        return ok_response(
                            data={
                                "mode": "async",
                                "task_id": task_id,
                                "deduplicated": True,
                                "label": task_dispatcher.get_task_label(
                                    "app.tasks.signal_flag_tasks.signal_flag_pool_backfill"
                                ),
                            },
                            legacy_alias_key=None,
                            enable_legacy_alias=legacy,
                        )
                    if task_message_store is not None:
                        task_message_store.push(
                            event="task_queued",
                            task_id=task_id,
                            task_name="app.tasks.signal_flag_tasks.signal_flag_pool_backfill",
                            detail=f"已投递信号旗历史回填（{start} → {end or 'today'}）",
                            meta={
                                "start_date": start,
                                "end_date": end or "",
                                "max_stocks": int(max_stocks),
                                "lookback_days": int(lookback),
                                "limit_days": int(limit_days),
                            },
                        )
                    return ok_response(
                        data={
                            "mode": "async",
                            "task_id": task_id,
                            "label": task_dispatcher.get_task_label(
                                "app.tasks.signal_flag_tasks.signal_flag_pool_backfill"
                            ),
                            "message": "任务已提交，完成后可在消息中心查看，并在信号旗页切换日期查看池。",
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as exc:  # noqa: BLE001
                logger.warning("signal_flag backfill celery enqueue failed, sync fallback: %s", exc)

        raise ValidationError(
            "signal_flag backfill requires celery; start worker/beat or call with ENABLE_CELERY=1"
        )
