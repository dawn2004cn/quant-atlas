"""API routes for system monitoring and tracing."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app

from app.config import get_settings
from app.core.circuit_breaker import CircuitBreakerRegistry
from app.core.registry import register_routes
from app.modules.system.services.helpers.monitoring_access import check_table_freshness
from app.modules.system.services.monitoring.trace_query_service import TraceQueryService
from app.presentation.api.responses import success_response

from .common import ok_response

monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/system")
query_service = TraceQueryService()


@monitoring_bp.route("/trace/<trace_id>", methods=["GET"])
def get_trace(trace_id: str):
    """Retrieve execution chain for a specific TraceID."""
    traces = query_service.get_traces_by_id(trace_id)
    return success_response(data={"trace_id": trace_id, "logs": traces})


@monitoring_bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint."""
    settings = get_settings()

    db_status = "skipped"
    db_engine = current_app.extensions.get("db_engine")
    if db_engine is not None:
        try:
            with db_engine.connect():
                db_status = "ok"
        except Exception as exc:
            db_status = f"error: {exc}"

    freshness = check_table_freshness("stock_history_sh")

    tdx_status = "not_configured"
    tdx_root = (settings.tdx_root_path or "").strip()
    if tdx_root:
        tdx_status = "ok" if Path(tdx_root).exists() else "error"

    try:
        cb_states = CircuitBreakerRegistry.get_all_status()
        any_open = any(s.get("state") == "OPEN" for s in cb_states.values())
        resilience_status = "degraded" if any_open else "ok"
    except Exception:
        cb_states = {}
        resilience_status = "unknown"

    overall = "ok"
    if db_status != "ok" or not freshness or resilience_status == "degraded":
        overall = "degraded"

    return ok_response(
        data={
            "status": overall,
            "services": {
                "database": db_status,
                "data_freshness": "ok" if freshness else "stale",
                "tdx_path": tdx_status,
            },
            "resilience": {
                "status": resilience_status,
                "circuit_breakers": cb_states,
                "circuit_breaker_count": len(cb_states),
            },
        }
    )


@register_routes(name="monitoring", context="system", description="System monitoring and tracing")
def register_monitoring_routes(blueprint: Blueprint, ctx=None) -> None:
    blueprint.register_blueprint(monitoring_bp)
