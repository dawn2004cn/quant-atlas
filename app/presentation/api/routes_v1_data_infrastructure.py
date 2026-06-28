from __future__ import annotations
"""API v1: Data infrastructure routes - WebSocket and Data Quality."""


import logging
from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ExternalServiceError, NotFoundError, ValidationError
from .common import ok_resource, ok_response
from .route_deps import DataInfrastructureRouteDeps, build_data_infrastructure_route_deps
from .v1_context import ApiV1Context
from .request_parsers import parse_int_param
from .decorators import require_role

from app.core.runtime_config import get_runtime
from app.core.registry import register_routes

logger = logging.getLogger(__name__)


def _parse_symbols_csv(raw: str) -> list[str]:
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


@register_routes(name="data_infrastructure", context="data", description="Data infrastructure routes (WebSocket, Data Quality)")
def register_data_infrastructure_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    deps: DataInfrastructureRouteDeps | None = None,
) -> None:
    route_deps = deps or build_data_infrastructure_route_deps(ctx)
    infra_service = route_deps.data_infrastructure_service
    task_dispatcher = route_deps.task_dispatcher
    task_message_store = route_deps.task_message_store
    legacy = route_deps.enable_legacy_response_fields

    @blueprint.get("/tasks")
    @login_required
    def list_tasks():
        from app.tasks.registry import ensure_task_registry, get_tasks_by_category
        ensure_task_registry()
        tasks = get_tasks_by_category()
        return ok_response(data={"tasks": tasks}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/tasks/run")
    @login_required
    @require_role("can_manage_users")
    def run_task():
        from app.tasks.registry import ensure_task_registry, get_task_info
        ensure_task_registry()
        body = request.get_json(silent=True) or {}
        task_name = (body.get("task_name") or "").strip()
        params = body.get("params", {})
        sync = body.get("sync", False)
        enable_celery = get_runtime("ENABLE_CELERY", False)

        if not task_name:
            raise ValidationError("task_name_required")

        task_info = get_task_info(task_name)
        if not task_info:
            raise NotFoundError(
                "task_not_registered",
                details={"task_name": task_name},
            )

        task_func = task_info["func"]

        if enable_celery and not sync:
            if task_func is not None and hasattr(task_func, "delay"):
                _, task_id, enqueued = task_dispatcher.dispatch(
                    task_func,
                    task_name=task_name,
                    kwargs=params,
                    bucket_seconds=300,
                )
                steps = list(task_info.get("estimated_steps") or ["排队", "执行", "持久化", "完成"])
                try:
                    from app.tasks.task_wiring import init_task_progress

                    init_task_progress(task_id, task_name=task_name, steps=steps)
                except Exception as _exc:
                    logger.warning("routes_v1_data_infrastructure.init_task_progress: %s", _exc)
                return ok_response(
                    data={
                        "mode": "async",
                        "task_id": task_id,
                        "task_name": task_name,
                        "params": params,
                        "estimated_steps": steps,
                    },
                    legacy_alias_key=None,
                    enable_legacy_alias=legacy,
                )
            else:
                raise ExternalServiceError(
                    "task_not_callable_or_celery_unavailable",
                    details={"task_name": task_name},
                )

        try:
            result = task_func(**params)
            return ok_response(data={**result, "mode": "sync", "task_name": task_name}, legacy_alias_key=None, enable_legacy_alias=legacy)
        except Exception as exc:
            raise ValidationError(
                "task_run_failed",
                details={"task_name": task_name, "reason": str(exc)},
            ) from exc

    @blueprint.get("/data/timeseries-health")
    @login_required
    def data_timeseries_health():
        """QuestDB / ClickHouse connectivity probe (credentials from env)."""
        from app.infrastructure.timeseries.timeseries_factory import timeseries_health_probe

        return ok_response(
            data=timeseries_health_probe(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/data/timeseries-sync-history")
    @login_required
    def data_timeseries_sync_history():
        """Recent QuestDB/ClickHouse sync runs (JSONL-backed, newest first)."""
        from app.infrastructure.timeseries.sync_snapshot import get_timeseries_sync_history

        limit = parse_int_param(
            request.args.get("limit"),
            name="limit",
            default=20,
            min_value=1,
            max_value=100,
        )
        source = (request.args.get("source") or "").strip() or None
        runs = get_timeseries_sync_history(limit=limit, source=source)
        return ok_response(
            data={
                "runs": runs,
                "limit": limit,
                "source_filter": source,
                "count": len(runs),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/data/timeseries-bars")
    @login_required
    def data_timeseries_bars():
        """Sample OHLCV from QuestDB/ClickHouse (falls back through multi-source chain)."""
        from datetime import date, timedelta

        from app.domain.enums import MarketCode
        from app.infrastructure.providers.history_adapters import get_multi_source_history_provider

        symbol = request.args.get("symbol", "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")
        market = MarketCode.CN
        days = parse_int_param(request.args.get("days"), name="days", default=60, min_value=5)
        end_d = date.today()
        start_d = end_d - timedelta(days=days)
        provider = get_multi_source_history_provider()
        bars = provider.get_history(symbol, market, start_d, end_d)
        return ok_response(
            data={
                "symbol": symbol,
                "market": market.value,
                "bars": bars[-min(len(bars), 120) :],
                "count": len(bars),
                "source": provider.last_source,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/data/quality")
    @login_required
    def data_quality_check():
        """Check data quality for a symbol."""
        symbol = request.args.get("symbol", "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")

        market = request.args.get("market", "CN")
        days = parse_int_param(request.args.get("days"), name="days", default=30)

        report = infra_service.check_data_quality(symbol, market, days)

        return ok_resource(
            resource={
                "symbol": symbol,
                "market": market,
                "total_checks": report.total_checks,
                "passed": report.passed,
                "failed": report.failed,
                "coverage": report.coverage,
                "completeness": report.completeness,
                "alerts": [
                    {
                        "severity": a.severity,
                        "field": a.field,
                        "expected": str(a.expected),
                        "actual": str(a.actual),
                        "message": a.message,
                        "source": a.source,
                    }
                    for a in report.alerts
                ],
            },
            resource_key="data_quality",
            enable_legacy_alias=False,
        )

    @blueprint.get("/data/compare-sources")
    @login_required
    def data_compare_sources():
        """Compare data across multiple sources."""
        symbol = request.args.get("symbol", "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")

        market = request.args.get("market", "CN")

        comparisons = infra_service.compare_data_sources(symbol, market)

        return ok_resource(
            resource={
                "symbol": symbol,
                "comparisons": comparisons,
            },
            resource_key="source_comparison",
            enable_legacy_alias=False,
        )

    @blueprint.get("/data/websocket/status")
    @login_required
    def data_websocket_status():
        """Get WebSocket connection status."""
        from flask import current_app

        connected = infra_service.is_websocket_connected()
        realtime_meta = current_app.config.get("REALTIME_META") or {}

        return ok_resource(
            resource={
                "connected": connected,
                "socketio_enabled": bool(realtime_meta.get("socketio")),
                "quote_broadcast": bool(realtime_meta.get("quote_broadcast")),
            },
            resource_key="websocket_status",
            enable_legacy_alias=False,
        )

    @blueprint.post("/data/websocket/connect")
    @login_required
    @require_role("can_manage_users")
    def data_websocket_connect():
        """Connect to WebSocket for real-time data."""
        success = infra_service.connect_websocket()

        if success:
            return ok_resource(
                resource={"connected": True},
                resource_key="websocket",
                enable_legacy_alias=False,
            )
        raise ExternalServiceError("websocket_not_configured")

    @blueprint.post("/data/websocket/subscribe")
    @login_required
    def data_websocket_subscribe():
        """Subscribe to real-time quotes."""
        if not infra_service.is_websocket_connected():
            raise ExternalServiceError("websocket_not_connected")

        symbols = _parse_symbols_csv(request.args.get("symbols", ""))
        if not symbols:
            raise ValidationError("symbols_required")

        success = infra_service.subscribe_realtime(symbols)

        return ok_resource(
            resource={"subscribed": success, "symbols": symbols},
            resource_key="websocket_subscribe",
            enable_legacy_alias=False,
        )

    @blueprint.get("/data/lineage")
    @login_required
    def data_lineage():
        """Get data lineage for a symbol."""
        symbol = request.args.get("symbol", "").strip().upper()
        date = request.args.get("date", "")

        if not symbol or not date:
            raise ValidationError(
                "symbol_and_date_required",
                details={"required": ["symbol", "date"]},
            )

        lineage = infra_service.get_data_lineage(symbol, date)

        return ok_resource(
            resource={"symbol": symbol, "date": date, "lineage": lineage},
            resource_key="data_lineage",
            enable_legacy_alias=False,
        )

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
        from ...tasks.tdx_gpcw_tasks import backfill_tdx_gpcw_full

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
        from ...tasks.tdx_gpcw_tasks import import_tdx_gpcw_latest

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
        from ...tasks.tdx_gpcw_tasks import import_tdx_gpcw_for_stock

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
        """全量TDX日K同步：TDX日K目录 → MySQL + CSV。"""
        from ...infrastructure.repositories.deps import create_tdx_dayk_sync_service

        body = request.get_json(silent=True) or {}
        limit = parse_int_param(body.get("limit"), name="limit", default=None, min_value=1)
        sync = body.get("sync", False)
        enable_celery = get_runtime("ENABLE_CELERY", False)

        if enable_celery and not sync:
            from ...tasks.data_backfill_tasks import backfill_all_history_tdx
            from app.celery_app import celery as _c
            if _c is not None and backfill_all_history_tdx is not None and hasattr(backfill_all_history_tdx, "delay"):
                _, task_id, enqueued = task_dispatcher.dispatch(
                    backfill_all_history_tdx,
                    task_name="app.tasks.data_backfill_tasks.backfill_all_history_tdx",
                    kwargs={"limit": limit},
                    bucket_seconds=300,
                )
                return ok_response(data={
                    "mode": "async",
                    "task_id": task_id,
                    "task_name": "backfill_all_history_tdx",
                    "limit": limit,
                }, legacy_alias_key=None, enable_legacy_alias=legacy)
            else:
                raise ExternalServiceError("celery_not_available")

        result = create_tdx_dayk_sync_service().full_sync_from_tdx_dayk(limit=limit)
        return ok_response(data={**result, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/data/tdx-dayk/incremental-sync")
    @login_required
    @require_role("can_manage_users")
    def tdx_dayk_incremental_sync():
        """增量 TDX 日 K：以 MySQL 最新日为游标补写（源数据来自 TDX lday）。"""
        from ...infrastructure.repositories.deps import create_tdx_dayk_sync_service

        body = request.get_json(silent=True) or {}
        limit = parse_int_param(body.get("limit"), name="limit", default=None, min_value=1)
        sync = body.get("sync", False)
        enable_celery = get_runtime("ENABLE_CELERY", False)

        if enable_celery and not sync:
            from ...tasks.data_backfill_tasks import sync_incremental_tdx
            from app.celery_app import celery as _c
            if _c is not None and sync_incremental_tdx is not None and hasattr(sync_incremental_tdx, "delay"):
                _, task_id, enqueued = task_dispatcher.dispatch(
                    sync_incremental_tdx,
                    task_name="app.tasks.data_backfill_tasks.sync_incremental_tdx",
                    kwargs={"limit": limit},
                    bucket_seconds=300,
                )
                return ok_response(data={
                    "mode": "async",
                    "task_id": task_id,
                    "task_name": "sync_incremental_tdx",
                    "limit": limit,
                }, legacy_alias_key=None, enable_legacy_alias=legacy)
            else:
                raise ExternalServiceError("celery_not_available")

        result = create_tdx_dayk_sync_service().incremental_sync_from_tdx_dayk(limit=limit)
        return ok_response(data={**result, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/data/qlib/export")
    @login_required
    @require_role("can_manage_users")
    def qlib_export():
        """Qlib数据导出：从CSV导出到qlib_bin。"""
        from ...tasks.qlib_data_update import qlib_full_backfill_if_empty

        body = request.get_json(silent=True) or {}
        period = str(body.get("period") or "5y").strip()
        max_workers = parse_int_param(body.get("max_workers"), name="max_workers", default=8, min_value=1)
        sync = body.get("sync", False)
        enable_celery = get_runtime("ENABLE_CELERY", False)

        if enable_celery and not sync:
            from app.celery_app import celery as _c
            if _c is not None and qlib_full_backfill_if_empty is not None and hasattr(qlib_full_backfill_if_empty, "delay"):
                _, task_id, enqueued = task_dispatcher.dispatch(
                    qlib_full_backfill_if_empty,
                    task_name="app.tasks.qlib_data_update.qlib_full_backfill_if_empty",
                    kwargs={"period": period, "max_workers": max_workers},
                    bucket_seconds=600,
                )
                return ok_response(data={
                    "mode": "async",
                    "task_id": task_id,
                    "task_name": "qlib_full_backfill_if_empty",
                    "period": period,
                }, legacy_alias_key=None, enable_legacy_alias=legacy)
            else:
                raise ExternalServiceError("celery_not_available")

        result = qlib_full_backfill_if_empty(period=period, max_workers=max_workers)
        return ok_response(data={**result, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)
