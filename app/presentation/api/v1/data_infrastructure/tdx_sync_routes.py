from __future__ import annotations

from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.core.runtime_config import get_runtime
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import require_role
from app.presentation.api.request_parsers import parse_int_param


def register_data_tdx_sync_routes(
    blueprint: Blueprint,
    *,
    legacy: bool,
    task_dispatcher: Any,
    task_message_store: Any,
) -> None:
    @blueprint.get("/data/tdx-gpcw/stats")
    @login_required
    def tdx_gpcw_stats():
        from app.modules.data.services.gpcw_service import get_gpcw_service

        service = get_gpcw_service()
        return ok_response(
            data={
                "total_rows": service.count_rows(),
                "total_stocks": service.count_stocks(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @blueprint.post("/data/tdx-gpcw/backfill")
    @login_required
    @require_role("can_manage_users")
    def tdx_gpcw_backfill():
        from app.tasks.tdx_gpcw_tasks import backfill_tdx_gpcw_full

        body = request.get_json(silent=True) or {}
        stock_filter_csv = body.get("stock_filter_csv", "")
        max_files = parse_int_param(body.get("max_files"), name="max_files", default=0, min_value=0)

        if task_dispatcher is not None and backfill_tdx_gpcw_full is not None:
            _, task_id, enqueued = task_dispatcher.dispatch(
                backfill_tdx_gpcw_full,
                task_name="app.tasks.tdx_gpcw_tasks.backfill_tdx_gpcw_full",
                kwargs={"stock_filter_csv": stock_filter_csv, "max_files": max_files},
                bucket_seconds=300,
                ttl_seconds=7200,
            )
            if not enqueued:
                return ok_response(
                    data={"mode": "async", "task_id": task_id, "deduplicated": True},
                    legacy_alias_key=None,
                    enable_legacy_alias=False,
                )
            if task_message_store is not None:
                task_message_store.push(
                    event="task.enqueued",
                    task_id=task_id,
                    task_name="app.tasks.tdx_gpcw_tasks.backfill_tdx_gpcw_full",
                    detail=f"TDX gpcw backfill requested (filter={stock_filter_csv or 'all'}, max_files={max_files})",
                )
            return ok_response(
                data={
                    "mode": "async",
                    "task_id": task_id,
                    "label": task_dispatcher.get_task_label("app.tasks.tdx_gpcw_tasks.backfill_tdx_gpcw_full"),
                },
                legacy_alias_key=None,
                enable_legacy_alias=False,
            )

        return ok_response(
            data={"mode": "inline", "result": backfill_tdx_gpcw_full(stock_filter_csv=stock_filter_csv, max_files=max_files)},
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @blueprint.post("/data/tdx-gpcw/import-latest")
    @login_required
    @require_role("can_manage_users")
    def tdx_gpcw_import_latest():
        from app.tasks.tdx_gpcw_tasks import import_tdx_gpcw_latest

        body = request.get_json(silent=True) or {}
        stock_filter_csv = body.get("stock_filter_csv", "")
        target_date = parse_int_param(body.get("target_date"), name="target_date", default=0, min_value=0)

        if task_dispatcher is not None and import_tdx_gpcw_latest is not None:
            _, task_id, enqueued = task_dispatcher.dispatch(
                import_tdx_gpcw_latest,
                task_name="app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_latest",
                kwargs={"stock_filter_csv": stock_filter_csv, "target_date": target_date},
                bucket_seconds=300,
                ttl_seconds=3600,
            )
            if not enqueued:
                return ok_response(
                    data={"mode": "async", "task_id": task_id, "deduplicated": True},
                    legacy_alias_key=None,
                    enable_legacy_alias=False,
                )
            if task_message_store is not None:
                task_message_store.push(
                    event="task.enqueued",
                    task_id=task_id,
                    task_name="app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_latest",
                    detail=f"TDX gpcw latest import (target_date={target_date})",
                )
            return ok_response(
                data={
                    "mode": "async",
                    "task_id": task_id,
                    "label": task_dispatcher.get_task_label("app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_latest"),
                },
                legacy_alias_key=None,
                enable_legacy_alias=False,
            )

        return ok_response(
            data={"mode": "inline", "result": import_tdx_gpcw_latest(stock_filter_csv=stock_filter_csv, target_date=target_date)},
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @blueprint.post("/data/tdx-gpcw/import-stock")
    @login_required
    @require_role("can_manage_users")
    def tdx_gpcw_import_stock():
        from app.tasks.tdx_gpcw_tasks import import_tdx_gpcw_for_stock

        body = request.get_json(silent=True) or {}
        code = (body.get("code") or "").strip()
        if not code:
            raise ValidationError("code_required")

        result = import_tdx_gpcw_for_stock(code=code)
        return ok_response(
            data=result,
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @blueprint.post("/data/tdx-dayk/full-sync")
    @login_required
    @require_role("can_manage_users")
    def tdx_dayk_full_sync():
        from app.infrastructure.repositories.deps import create_tdx_dayk_sync_service

        body = request.get_json(silent=True) or {}
        limit = parse_int_param(body.get("limit"), name="limit", default=None, min_value=1)
        sync = body.get("sync", False)
        enable_celery = get_runtime("ENABLE_CELERY", False)

        if enable_celery and not sync:
            from app.celery_app import celery as _c

            from app.tasks.data_backfill_tasks import backfill_all_history_tdx

            if _c is not None and backfill_all_history_tdx is not None and hasattr(backfill_all_history_tdx, "delay"):
                _, task_id, _enqueued = task_dispatcher.dispatch(
                    backfill_all_history_tdx,
                    task_name="app.tasks.data_backfill_tasks.backfill_all_history_tdx",
                    kwargs={"limit": limit},
                    bucket_seconds=300,
                )
                return ok_response(
                    data={
                        "mode": "async",
                        "task_id": task_id,
                        "task_name": "backfill_all_history_tdx",
                        "limit": limit,
                    },
                    legacy_alias_key=None,
                    enable_legacy_alias=legacy,
                )
            raise ExternalServiceError("celery_not_available")

        result = create_tdx_dayk_sync_service().full_sync_from_tdx_dayk(limit=limit)
        return ok_response(data={**result, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/data/tdx-dayk/incremental-sync")
    @login_required
    @require_role("can_manage_users")
    def tdx_dayk_incremental_sync():
        from app.infrastructure.repositories.deps import create_tdx_dayk_sync_service

        body = request.get_json(silent=True) or {}
        limit = parse_int_param(body.get("limit"), name="limit", default=None, min_value=1)
        sync = body.get("sync", False)
        enable_celery = get_runtime("ENABLE_CELERY", False)

        if enable_celery and not sync:
            from app.celery_app import celery as _c

            from app.tasks.data_backfill_tasks import sync_incremental_tdx

            if _c is not None and sync_incremental_tdx is not None and hasattr(sync_incremental_tdx, "delay"):
                _, task_id, _enqueued = task_dispatcher.dispatch(
                    sync_incremental_tdx,
                    task_name="app.tasks.data_backfill_tasks.sync_incremental_tdx",
                    kwargs={"limit": limit},
                    bucket_seconds=300,
                )
                return ok_response(
                    data={
                        "mode": "async",
                        "task_id": task_id,
                        "task_name": "sync_incremental_tdx",
                        "limit": limit,
                    },
                    legacy_alias_key=None,
                    enable_legacy_alias=legacy,
                )
            raise ExternalServiceError("celery_not_available")

        result = create_tdx_dayk_sync_service().incremental_sync_from_tdx_dayk(limit=limit)
        return ok_response(data={**result, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/data/qlib/export")
    @login_required
    @require_role("can_manage_users")
    def qlib_export():
        from app.tasks.qlib_data_update import qlib_full_backfill_if_empty

        body = request.get_json(silent=True) or {}
        period = str(body.get("period") or "5y").strip()
        max_workers = parse_int_param(body.get("max_workers"), name="max_workers", default=8, min_value=1)
        sync = body.get("sync", False)
        enable_celery = get_runtime("ENABLE_CELERY", False)

        if enable_celery and not sync:
            from app.celery_app import celery as _c

            if _c is not None and qlib_full_backfill_if_empty is not None and hasattr(qlib_full_backfill_if_empty, "delay"):
                _, task_id, _enqueued = task_dispatcher.dispatch(
                    qlib_full_backfill_if_empty,
                    task_name="app.tasks.qlib_data_update.qlib_full_backfill_if_empty",
                    kwargs={"period": period, "max_workers": max_workers},
                    bucket_seconds=600,
                )
                return ok_response(
                    data={
                        "mode": "async",
                        "task_id": task_id,
                        "task_name": "qlib_full_backfill_if_empty",
                        "period": period,
                    },
                    legacy_alias_key=None,
                    enable_legacy_alias=legacy,
                )
            raise ExternalServiceError("celery_not_available")

        result = qlib_full_backfill_if_empty(period=period, max_workers=max_workers)
        return ok_response(data={**result, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)
