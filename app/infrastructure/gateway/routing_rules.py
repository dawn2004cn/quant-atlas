"""API Gateway routing rules for Phase 2A microservice extraction.

This module defines the routing configuration for the API Gateway (Kong/APISIX/NGINX)
that will route traffic between the monolith and the new microservices.

Phase 2A: Market Data Service extraction
Phase 2B: Strategy Service extraction
Phase 2C: Execution Service extraction
"""

from __future__ import annotations

from typing import Any


# ── Kong/APISIX Route Configuration ────────────────────────────────

KONG_ROUTES = {
    "market_data_v1": {
        "name": "Market Data Service v1",
        "paths": ["/api/v1/market"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "upstream_url": "http://market-data-service:5101",
        "plugins": [
            {"name": "cors", "config": {"origins": ["*"], "methods": ["GET", "POST"], "headers": ["Content-Type", "Authorization"]}},
            {"name": "rate-limiting", "config": {"minute": 1000, "policy": "local"}},
            {"name": "prometheus", "config": {"per_consumer": False}},
        ],
        "timeouts": {"connect_timeout": 1000, "read_timeout": 10000, "write_timeout": 10000},
        "retries": 3,
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 30},
    },
    "market_data_v2": {
        "name": "Market Data Service v2",
        "paths": ["/api/v2/market"],
        "methods": ["GET", "POST"],
        "upstream_url": "http://market-data-service:5101",
        "plugins": [
            {"name": "jwt", "config": {"claims_to_verify": ["exp"]}},
            {"name": "rate-limiting", "config": {"minute": 2000, "policy": "redis"}},
        ],
    },
}

APISIX_ROUTES = {
    "market_data": {
        "name": "Market Data Service",
        "uri": "/api/v1/market/*",
        "methods": ["GET", "POST"],
        "upstream": {
            "type": "roundrobin",
            "nodes": {"market-data-service:5101": 1},
        },
        "plugins": {
            "cors": {"allow_origins": ["*"], "allow_methods": ["GET", "POST"], "allow_headers": ["Content-Type", "Authorization"]},
            "limit-req": {"rate": 1000, "burst": 2000, "rejected_code": 429},
            "prometheus": {},
        },
    },
}

NGINX_UPSTREAMS = """
upstream market_data_service {
    least_conn;
    server market-data-service:5101 max_fails=3 fail_timeout=30s;
    server market-data-service-backup:5101 backup;
}

upstream strategy_service {
    least_conn;
    server strategy-service:5102 max_fails=3 fail_timeout=30s;
}

upstream execution_service {
    least_conn;
    server execution-service:5103 max_fails=3 fail_timeout=30s;
}
"""

NGINX_LOCATION_MARKET = """
location /api/v1/market/ {
    proxy_pass http://market_data_service;
    proxy_connect_timeout 1s;
    proxy_read_timeout 10s;
    proxy_send_timeout 10s;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Cache static responses
    proxy_cache market_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$request_uri";
    
    # Circuit breaker
    proxy_next_upstream error timeout http_502 http_503 http_504;
    proxy_next_upstream_tries 2;
    proxy_next_upstream_timeout 5s;
}
"""


def get_kong_routes() -> dict[str, Any]:
    """Get Kong route configuration for all Phase 2A services."""
    return KONG_ROUTES


def get_apisix_routes() -> dict[str, Any]:
    """Get APISIX route configuration for all Phase 2A services."""
    return APISIX_ROUTES


def get_nginx_config() -> str:
    """Get NGINX configuration snippet for Phase 2A services."""
    return NGINX_UPSTREAMS + NGINX_LOCATION_MARKET


# ── Service Discovery Configuration ────────────────────────────────

SERVICE_DISCOVERY = {
    "market_data_service": {
        "name": "market-data",
        "port": 5101,
        "health_path": "/health",
        "readiness_path": "/ready",
        "liveness_path": "/live",
        "tags": ["market", "data", "quotes", "history"],
        "dependencies": ["mysql", "redis", "questdb"],
        "scaling": {
            "min_instances": 2,
            "max_instances": 10,
            "target_cpu": 70,
        },
    },
}


def get_service_discovery_config() -> dict[str, Any]:
    """Get service discovery configuration for all Phase 2A services."""
    return SERVICE_DISCOVERY
