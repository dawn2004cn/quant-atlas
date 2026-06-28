"""OHLCV sync and reconciliation admin routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.core.logger import get_logger
from app.presentation.api.common import ok_response, require_data_ingestion_role
from app.presentation.api.v1.task_ops.runtime import TaskOpsRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def register_task_ops_sync_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TaskOpsRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.post("/system/questdb-ohlcv-sync")
    @login_required
    def system_questdb_ohlcv_sync():
        require_data_ingestion_role()
        from app.modules.data.services.timeseries_ohlcv_sync_service import run_timeseries_ohlcv_sync

        body = request.get_json(silent=True) or {}
        limit = body.get("limit")
        symbols = body.get("symbols")
        lookback = body.get("lookback_days")
        targets = body.get("targets")
        out = run_timeseries_ohlcv_sync(
            limit=int(limit) if limit is not None else None,
            symbols=symbols if isinstance(symbols, list) else None,
            lookback_days=int(lookback) if lookback is not None else None,
            targets=targets if isinstance(targets, list) else None,
        )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/timeseries-ohlcv-sync")
    @login_required
    def system_timeseries_ohlcv_sync():
        require_data_ingestion_role()
        from app.modules.data.services.timeseries_ohlcv_sync_service import (
            run_timeseries_ohlcv_backfill,
            run_timeseries_ohlcv_sync,
        )

        body = request.get_json(silent=True) or {}
        force = bool(body.get("force"))
        full = bool(body.get("full"))
        common = {
            "limit": int(body["limit"]) if body.get("limit") is not None else None,
            "symbols": body.get("symbols") if isinstance(body.get("symbols"), list) else None,
            "lookback_days": int(body["lookback_days"]) if body.get("lookback_days") is not None else None,
            "targets": body.get("targets") if isinstance(body.get("targets"), list) else None,
            "offset": int(body.get("offset") or 0),
            "skip_existing": not force,
            "workers": int(body["workers"]) if body.get("workers") is not None else None,
            "max_symbols_cap": 50_000,
        }
        if full:
            out = run_timeseries_ohlcv_backfill(
                batch_size=int(body["batch_size"]) if body.get("batch_size") is not None else None,
                max_batches=int(body["max_batches"]) if body.get("max_batches") is not None else None,
                **{k: v for k, v in common.items() if k != "limit"},
            )
        else:
            out = run_timeseries_ohlcv_sync(**common)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/data/timeseries-backfill-status")
    @login_required
    def data_timeseries_backfill_status():
        from app.infrastructure.timeseries.sync_snapshot import describe_timeseries_backfill_status

        return ok_response(
            data=describe_timeseries_backfill_status(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/system/timeseries-ohlcv-backfill")
    @login_required
    def system_timeseries_ohlcv_backfill():
        require_data_ingestion_role()
        from app.tasks.questdb_sync_tasks import run_full_market_timeseries_backfill

        body = request.get_json(silent=True) or {}
        sync = bool(body.get("sync"))
        common = {
            "batch_size": int(body["batch_size"]) if body.get("batch_size") is not None else None,
            "max_batches": int(body["max_batches"]) if body.get("max_batches") is not None else None,
            "offset": int(body.get("offset") or 0),
            "lookback_days": int(body["lookback_days"]) if body.get("lookback_days") is not None else None,
            "truncate_first": bool(body.get("truncate_first")),
            "workers": int(body["workers"]) if body.get("workers") is not None else None,
        }
        task_name = "app.tasks.questdb_sync_tasks.timeseries_ohlcv_full_backfill"

        if runtime.ctx.enable_celery and not sync:
            try:
                from app.celery_app import celery as _celery
                from app.tasks.questdb_sync_tasks import timeseries_ohlcv_full_backfill

                if (
                    _celery is not None
                    and timeseries_ohlcv_full_backfill is not None
                    and hasattr(timeseries_ohlcv_full_backfill, "delay")
                    and runtime.ctx.task_dispatcher is not None
                ):
                    _, task_id, enqueued = runtime.ctx.task_dispatcher.dispatch(
                        timeseries_ohlcv_full_backfill,
                        task_name=task_name,
                        kwargs=common,
                        bucket_seconds=600,
                        ttl_seconds=7200,
                    )
                    if runtime.ctx.task_message_store is not None:
                        runtime.ctx.task_message_store.push(
                            event="task_queued",
                            task_id=task_id,
                            task_name=task_name,
                            detail="全市场 QuestDB/ClickHouse OHLCV backfill 已投递",
                            meta=common,
                        )
                    return ok_response(
                        data={
                            "mode": "async",
                            "task_id": task_id,
                            "deduplicated": not enqueued,
                            "label": runtime.ctx.task_dispatcher.get_task_label(task_name),
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
            except Exception as exc:
                logger.warning("timeseries backfill async enqueue failed, sync fallback: %s", exc)

        out = run_full_market_timeseries_backfill(**common)
        return ok_response(data={**out, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/tdx-timescale-sync")
    @login_required
    def system_tdx_timescale_sync():
        require_data_ingestion_role()
        from app.modules.data.services.tdx_timescale_sync_service import (
            run_tdx_timescale_backfill,
            run_tdx_timescale_sync,
        )

        body = request.get_json(silent=True) or {}
        full = bool(body.get("full"))
        common = {
            "limit": int(body["limit"]) if body.get("limit") is not None else None,
            "offset": int(body.get("offset") or 0),
            "mode": str(body.get("mode") or "full"),
            "start_date": body.get("start_date"),
            "dump_max_workers": int(body["workers"]) if body.get("workers") is not None else None,
        }
        if full:
            out = run_tdx_timescale_backfill(
                batch_size=int(body["batch_size"]) if body.get("batch_size") is not None else None,
                max_batches=int(body["max_batches"]) if body.get("max_batches") is not None else None,
                offset=common["offset"],
            )
        else:
            out = run_tdx_timescale_sync(**common)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/system/ohlcv-reconciliation")
    @login_required
    def system_ohlcv_reconciliation():
        require_data_ingestion_role()
        from app.modules.data.services.ohlcv_reconciliation_service import run_ohlcv_reconciliation

        body = request.get_json(silent=True) or {}
        sample = body.get("sample_size")
        out = run_ohlcv_reconciliation(
            sample_size=int(sample) if sample is not None else None,
        )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)
