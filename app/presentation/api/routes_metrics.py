from __future__ import annotations

"""Prometheus metrics endpoints (optional standalone registration)."""

from datetime import datetime

from flask import Flask, Response

from app.modules.system.services.helpers.metrics_access import (
    build_metrics_summary,
    prometheus_metrics_content_type,
    render_prometheus_metrics,
)


def register_metrics_routes(app: Flask) -> None:
    """Register Prometheus metrics endpoints on the Flask app."""

    @app.route("/metrics")
    def metrics():
        return Response(
            render_prometheus_metrics(),
            mimetype=prometheus_metrics_content_type(),
        )

    @app.route("/health")
    def health():
        return ok_response(data={"status": "healthy", "timestamp": datetime.now().isoformat()})

    @app.route("/metrics/summary")
    def metrics_summary():
        summary = build_metrics_summary()
        summary["timestamp"] = datetime.now().isoformat()
        return ok_response(data=summary)
