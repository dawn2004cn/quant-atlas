"""Basic market data refresh route (longhu / yanbao ingest)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from flask import Blueprint, request
from flask_login import login_required

from app.core.logger import get_logger
from app.presentation.api.common import ok_response, require_data_ingestion_role
from app.presentation.api.request_parsers import parse_bool_param
from app.presentation.api.v1.market_aux.runtime import MarketAuxRuntime
from app.presentation.api.v1_context import ApiV1Context

from ...decorators import service_fallback

logger = get_logger(__name__)


def register_market_aux_refresh_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: MarketAuxRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.post("/market/basic-data/refresh")
    @login_required
    @service_fallback("basic_market_data_service")
    def market_basic_data_refresh():
        """手动触发龙虎榜/研报入库。``ENABLE_CELERY=1`` 时默认走异步队列并写入消息中心。"""
        basic_market_data_service = getattr(ctx, "basic_market_data_service", None)
        require_data_ingestion_role()
        body = request.get_json(silent=True) or {}
        kind = str(body.get("kind") or "all").strip().lower()
        sync = parse_bool_param(request.args.get("sync"), name="sync", default=False)
        if runtime.enable_celery and not sync:
            try:
                from app.celery_app import celery as _celery_client
                from app.tasks.market_tasks import refresh_basic_market_data

                if (
                    _celery_client is not None
                    and refresh_basic_market_data is not None
                    and hasattr(refresh_basic_market_data, "delay")
                ):
                    _, task_id, enqueued = runtime.task_dispatcher.dispatch(
                        refresh_basic_market_data,
                        task_name="app.tasks.market_tasks.refresh_basic_market_data",
                        args=[kind],
                        kwargs={},
                        bucket_seconds=60,
                        ttl_seconds=600,
                    )
                    if not enqueued:
                        return ok_response(
                            data={
                                "mode": "async",
                                "task_id": task_id,
                                "kind": kind,
                                "deduplicated": True,
                                "label": runtime.task_dispatcher.get_task_label(
                                    "app.tasks.market_tasks.refresh_basic_market_data"
                                ),
                            },
                            legacy_alias_key=None,
                            enable_legacy_alias=legacy,
                        )
                    if runtime.task_message_store is not None:
                        runtime.task_message_store.push(
                            event="task_queued",
                            task_id=task_id,
                            task_name="app.tasks.market_tasks.refresh_basic_market_data",
                            detail=f"已投递 Celery 队列（kind={kind}）",
                            meta={"kind": kind},
                        )
                    return ok_response(
                        data={
                            "mode": "async",
                            "task_id": task_id,
                            "kind": kind,
                            "label": runtime.task_dispatcher.get_task_label(
                                "app.tasks.market_tasks.refresh_basic_market_data"
                            ),
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as exc:
                logger.warning("celery enqueue failed, falling back to sync: %s", exc)

        out: dict = {}
        if kind in ("all", "longhu"):
            out["longhu"] = basic_market_data_service.ingest_longhu_em(lookback_calendar_days=14)
        if kind in ("all", "yanbao"):
            end = datetime.now()
            begin = end - timedelta(days=30)
            out["yanbao"] = basic_market_data_service.ingest_yanbao_eastmoney_api(
                begin=begin.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                page_size=200,
                max_pages=20,
                sleep_sec=0.2,
            )
        if runtime.task_message_store is not None:
            runtime.task_message_store.push(
                event="task_succeeded",
                task_id=f"sync-{uuid.uuid4().hex[:12]}",
                task_name="inline.basic_data_refresh",
                detail=f"同步执行完成 kind={kind}",
                meta={"kind": kind, "mode": "sync"},
            )
        return ok_response(
            data={**out, "mode": "sync"},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
