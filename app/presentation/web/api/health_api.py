from __future__ import annotations
"""Health Check API Blueprint.

REST endpoints for system health checks.
"""


from flask import Blueprint, jsonify
from datetime import datetime


from app.core.logger import get_logger

logger = get_logger(__name__)

health_bp = Blueprint("health", __name__, url_prefix="/api/health")


@health_bp.route("/", methods=["GET"])
def health_check():
    """General health check."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })


@health_bp.route("/domain", methods=["GET"])
def domain_health_check():
    """Domain layer health check."""
    try:
        from app.application.domain_facade import get_domain_facade
        from app.application.aggregate_registry import get_aggregate_registry
        from app.domain.events.handlers import get_event_bus

        get_domain_facade()
        registry = get_aggregate_registry()
        event_bus = get_event_bus()

        return jsonify({
            "status": "healthy",
            "domain_services": {
                "screening": "ok",
                "signals": "ok",
                "portfolio": "ok",
                "policy": "ok",
            },
            "aggregates": registry.get_stats(),
            "events": {
                "count": event_bus.event_count,
            },
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Domain health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


@health_bp.route("/event-store", methods=["GET"])
def event_store_health_check():
    """Event store health check."""
    try:
        from app.infrastructure.events.event_store import get_event_store

        store = get_event_store()

        return jsonify({
            "status": "healthy",
            "event_count": store.get_event_count(),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Event store health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


@health_bp.route("/cqrs", methods=["GET"])
def cqrs_health_check():
    """CQRS health check."""
    try:
        from app.application.mediator import get_mediator

        mediator = get_mediator()

        return jsonify({
            "status": "healthy",
            "command_handlers": len(mediator._command_handlers),
            "query_handlers": len(mediator._query_handlers),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"CQRS health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


__all__ = ["health_bp"]
