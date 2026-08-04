from __future__ import annotations

"""API v1: Data infrastructure routes - WebSocket and Data Quality."""

import logging

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.core.registry import register_routes
from app.presentation.api.common import ok_resource
from app.presentation.api.decorators import require_role
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.route_deps import DataInfrastructureRouteDeps, build_data_infrastructure_route_deps
from app.presentation.api.v1.data_infrastructure.task_routes import register_data_task_routes
from app.presentation.api.v1.data_infrastructure.tdx_sync_routes import register_data_tdx_sync_routes
from app.presentation.api.v1.data_infrastructure.timeseries_routes import register_data_timeseries_routes
from app.presentation.api.v1_context import ApiV1Context

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

    register_data_task_routes(
        blueprint,
        legacy=legacy,
        task_dispatcher=task_dispatcher,
        task_message_store=task_message_store,
    )
    register_data_timeseries_routes(blueprint, legacy=legacy)
    register_data_tdx_sync_routes(
        blueprint,
        legacy=legacy,
        task_dispatcher=task_dispatcher,
        task_message_store=task_message_store,
    )

    @blueprint.get("/data/quality")
    @login_required
    def data_quality_check():
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
