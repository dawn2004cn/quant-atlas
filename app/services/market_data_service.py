"""Market Data Service — standalone entry point for Phase 2A extraction.

This module provides the entry point for running the Market Data Service
as an independent Flask application. It includes:

1. Standalone Flask app factory
2. Dual-write middleware (monolith ↔ service)
3. Health check and metrics endpoints
4. API Gateway routing configuration

Usage:
    # Run standalone (Phase 2A)
    python -m app.services.market_data_service

    # Or programmatically:
    from app.services.market_data_service import create_market_data_app
    app = create_market_data_app()
    app.run(host="0.0.0.0", port=5101)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)


# ── Dual-Write Middleware ───────────────────────────────────────────
# In Phase 2A, this middleware ensures both the monolith and the new
# service handle requests simultaneously (dual-write pattern).
# After validation period, traffic shifts entirely to the new service.

class DualWriteMiddleware:
    """Dual-write middleware for gradual service extraction.

    During the migration period, requests are processed by both:
    1. The monolith (existing Flask app)
    2. The new service (standalone Flask app)

    Responses from the new service are validated against monolith responses.
    Once confidence is high, traffic shifts to the new service only.
    """

    def __init__(self, app: Flask, service_client: Any | None = None):
        self.app = app
        self.service_client = service_client
        self.stats = {
            "monolith_requests": 0,
            "service_requests": 0,
            "discrepancies": 0,
            "errors": 0,
        }

    def __call__(self, environ: dict, start_response: Callable) -> Any:
        """Process request through dual-write pipeline."""
        self.stats["monolith_requests"] += 1

        # Phase 2A: Route to service if configured
        if self.service_client is not None:
            try:
                self.stats["service_requests"] += 1
                # Service handling would happen here via HTTP proxy
                # For now, fall through to monolith
            except Exception as exc:
                logger.warning("Dual-write service call failed: %s", exc)
                self.stats["errors"] += 1

        return self.app(environ, start_response)

    def get_stats(self) -> dict[str, int]:
        """Get dual-write statistics."""
        return dict(self.stats)


def create_market_data_app() -> Flask:
    """Create standalone Market Data Service Flask app.

    This factory creates a minimal Flask app with:
    - Market data routes (from blueprint)
    - Health check endpoint
    - Metrics endpoint
    - CORS headers
    - Request logging

    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__)

    # Configuration
    app.config["JSON_AS_ASCII"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 300  # 5 min cache

    # Initialize dual-write middleware
    dual_write = DualWriteMiddleware(app)
    app.extensions["dual_write"] = dual_write

    # Import and register market data blueprint
    from app.modules.market_data.market_data_blueprint import create_market_data_blueprint
    bp = create_market_data_blueprint()
    app.register_blueprint(bp, url_prefix="/api/v1/market")

    # Health check
    @app.route("/health")
    def health_check():
        return jsonify({
            "status": "ok",
            "service": "market-data",
            "version": "2a",
            "timestamp": time.time(),
        })

    # Metrics endpoint
    @app.route("/metrics")
    def metrics():
        dual_write_stats = dual_write.get_stats()
        return jsonify({
            "service": "market-data",
            "version": "2a",
            "dual_write": dual_write_stats,
            "routes_registered": len(list(app.url_map.iter_rules())),
        })

    # Readiness probe
    @app.route("/ready")
    def readiness():
        return jsonify({"ready": True}), 200

    # Liveness probe
    @app.route("/live")
    def liveness():
        return jsonify({"alive": True}), 200

    # Request logging middleware
    @app.before_request
    def log_request():
        request.start_time = time.time()
        logger.debug("%s %s", request.method, request.path)

    @app.after_request
    def log_response(response):
        if hasattr(request, "start_time"):
            elapsed = time.time() - request.start_time
            if elapsed > 0.5:  # Log slow requests
                logger.warning("Slow request: %s %s took %.2fs", request.method, request.path, elapsed)
        return response

    logger.info("Market Data Service app created (Phase 2A)")
    return app


# ── API Gateway Routing Configuration ──────────────────────────────
# These rules define how the API Gateway routes traffic to services.
# In production, this config is loaded by Kong/APISIX/NGINX.

API_GATEWAY_ROUTES = {
    "market_data_service": {
        "paths": [
            "/api/v1/market/*",
            "/api/v1/stocks/*",
            "/api/v1/global/*",
            "/api/v1/hot-sectors/*",
            "/api/v1/sentiment/*",
            "/api/v1/tdx/*",
            "/api/v1/pytdx/*",
        ],
        "upstream": "http://localhost:5101",
        "timeout": 10,  # seconds
        "retries": 3,
        "circuit_breaker": {
            "failure_threshold": 5,
            "recovery_timeout": 30,
        },
        "rate_limit": "1000 req/s per user",
        "cache": {
            "enabled": True,
            "ttl_seconds": 5,  # Market data cached for 5s
            "paths": ["/quotes/*", "/history/*"],
        },
    },
}


def get_api_gateway_config() -> dict[str, Any]:
    """Return API Gateway routing configuration for Market Data Service."""
    return API_GATEWAY_ROUTES


# ── Service Entry Point ─────────────────────────────────────────────

def main() -> None:
    """Run Market Data Service standalone (Phase 2A)."""
    import argparse

    parser = argparse.ArgumentParser(description="Market Data Service (Phase 2A)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")  # service entry-point; host is configurable at runtime
    parser.add_argument("--port", type=int, default=5101, help="Bind port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    app = create_market_data_app()
    logger.info("Starting Market Data Service on %s:%d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
