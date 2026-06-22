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
    "strategy_v1": {
        "name": "Strategy Service v1",
        "paths": ["/strategy"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "upstream_url": "http://strategy-service:5201",
        "plugins": [
            {"name": "cors", "config": {"origins": ["*"], "methods": ["GET", "POST"], "headers": ["Content-Type", "Authorization"]}},
            {"name": "rate-limiting", "config": {"minute": 500, "policy": "local"}},
        ],
    },
    "ai_agent_v1": {
        "name": "AI Agent Service v1",
        "paths": ["/ai-agent"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "upstream_url": "http://ai-agent-service:5301",
        "plugins": [
            {"name": "cors", "config": {"origins": ["*"], "methods": ["GET", "POST"], "headers": ["Content-Type", "Authorization"]}},
            {"name": "rate-limiting", "config": {"minute": 200, "policy": "local"}},
        ],
    },
    "portfolio_risk_v1": {
        "name": "Portfolio/Risk Service v1",
        "paths": ["/portfolio-risk"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "upstream_url": "http://portfolio-risk-service:5401",
        "plugins": [
            {"name": "cors", "config": {"origins": ["*"], "methods": ["GET", "POST"], "headers": ["Content-Type", "Authorization"]}},
            {"name": "rate-limiting", "config": {"minute": 1000, "policy": "local"}},
        ],
    },
    "execution_v1": {
        "name": "Execution Service v1",
        "paths": ["/execution"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "upstream_url": "http://execution-service:5501",
        "plugins": [
            {"name": "cors", "config": {"origins": ["*"], "methods": ["GET", "POST"], "headers": ["Content-Type", "Authorization"]}},
            {"name": "rate-limiting", "config": {"minute": 2000, "policy": "local"}},
        ],
    },
    "system_user_v1": {
        "name": "System/User Service v1",
        "paths": ["/system"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "upstream_url": "http://system-user-service:5601",
        "plugins": [
            {"name": "cors", "config": {"origins": ["*"], "methods": ["GET", "POST"], "headers": ["Content-Type", "Authorization"]}},
            {"name": "rate-limiting", "config": {"minute": 1000, "policy": "local"}},
        ],
    },
    "data_v1": {
        "name": "Data Service v1",
        "paths": ["/data"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "upstream_url": "http://data-service:5701",
        "plugins": [
            {"name": "cors", "config": {"origins": ["*"], "methods": ["GET", "POST"], "headers": ["Content-Type", "Authorization"]}},
            {"name": "rate-limiting", "config": {"minute": 500, "policy": "local"}},
        ],
    },
    "research_v1": {
        "name": "Research Service v1",
        "paths": ["/research"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "upstream_url": "http://research-service:5801",
        "plugins": [
            {"name": "cors", "config": {"origins": ["*"], "methods": ["GET", "POST"], "headers": ["Content-Type", "Authorization"]}},
            {"name": "rate-limiting", "config": {"minute": 200, "policy": "local"}},
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
}

upstream strategy_service {
    least_conn;
    server strategy-service:5201 max_fails=3 fail_timeout=30s;
}

upstream ai_agent_service {
    least_conn;
    server ai-agent-service:5301 max_fails=3 fail_timeout=30s;
}

upstream portfolio_risk_service {
    least_conn;
    server portfolio-risk-service:5401 max_fails=3 fail_timeout=30s;
}

upstream execution_service {
    least_conn;
    server execution-service:5501 max_fails=3 fail_timeout=30s;
}

upstream system_user_service {
    least_conn;
    server system-user-service:5601 max_fails=3 fail_timeout=30s;
}

upstream data_service {
    least_conn;
    server data-service:5701 max_fails=3 fail_timeout=30s;
}

upstream research_service {
    least_conn;
    server research-service:5801 max_fails=3 fail_timeout=30s;
}
"""

NGINX_LOCATION_TEMPLATE = """
location {path} {{
    proxy_pass http://{upstream};
    proxy_connect_timeout 1s;
    proxy_read_timeout 10s;
    proxy_send_timeout 10s;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_next_upstream error timeout http_502 http_503 http_504;
    proxy_next_upstream_tries 2;
    proxy_next_upstream_timeout 5s;
}}
"""

NGINX_LOCATIONS = "\n".join([
    NGINX_LOCATION_TEMPLATE.format(path="/api/v1/market/", upstream="market_data_service"),
    NGINX_LOCATION_TEMPLATE.format(path="/strategy/", upstream="strategy_service"),
    NGINX_LOCATION_TEMPLATE.format(path="/ai-agent/", upstream="ai_agent_service"),
    NGINX_LOCATION_TEMPLATE.format(path="/portfolio-risk/", upstream="portfolio_risk_service"),
    NGINX_LOCATION_TEMPLATE.format(path="/execution/", upstream="execution_service"),
    NGINX_LOCATION_TEMPLATE.format(path="/system/", upstream="system_user_service"),
    NGINX_LOCATION_TEMPLATE.format(path="/data/", upstream="data_service"),
    NGINX_LOCATION_TEMPLATE.format(path="/research/", upstream="research_service"),
])


def get_kong_routes() -> dict[str, Any]:
    """Get Kong route configuration for all microservices."""
    return KONG_ROUTES


def get_apisix_routes() -> dict[str, Any]:
    """Get APISIX route configuration for all microservices."""
    return APISIX_ROUTES


def get_nginx_config() -> str:
    """Get NGINX configuration snippet for all Phase 2 services."""
    return NGINX_UPSTREAMS + "\n" + NGINX_LOCATIONS


# ── Service Discovery Configuration ────────────────────────────────────────

SERVICE_DISCOVERY = {
    "market_data_service": {
        "name": "market-data",
        "port": 5101,
        "health_path": "/health",
        "tags": ["market", "data", "quotes", "history"],
        "dependencies": ["mysql", "redis"],
        "scaling": {"min_instances": 2, "max_instances": 10, "target_cpu": 70},
    },
    "strategy_service": {
        "name": "strategy",
        "port": 5201,
        "health_path": "/health",
        "tags": ["strategy", "backtest", "signals"],
        "dependencies": ["mysql", "redis"],
        "scaling": {"min_instances": 2, "max_instances": 10, "target_cpu": 70},
    },
    "ai_agent_service": {
        "name": "ai-agent",
        "port": 5301,
        "health_path": "/health",
        "tags": ["ai", "nlp", "chat", "analysis"],
        "dependencies": ["mysql", "redis"],
        "scaling": {"min_instances": 2, "max_instances": 5, "target_cpu": 80},
    },
    "portfolio_risk_service": {
        "name": "portfolio-risk",
        "port": 5401,
        "health_path": "/health",
        "tags": ["portfolio", "risk", "positions"],
        "dependencies": ["mysql", "redis"],
        "scaling": {"min_instances": 2, "max_instances": 10, "target_cpu": 70},
    },
    "execution_service": {
        "name": "execution",
        "port": 5501,
        "health_path": "/health",
        "tags": ["execution", "orders", "trading"],
        "dependencies": ["mysql", "redis"],
        "scaling": {"min_instances": 2, "max_instances": 5, "target_cpu": 80},
    },
    "system_user_service": {
        "name": "system-user",
        "port": 5601,
        "health_path": "/health",
        "tags": ["system", "user", "auth", "config"],
        "dependencies": ["mysql", "redis"],
        "scaling": {"min_instances": 2, "max_instances": 5, "target_cpu": 70},
    },
    "data_service": {
        "name": "data",
        "port": 5701,
        "health_path": "/health",
        "tags": ["data", "lake", "storage", "infrastructure"],
        "dependencies": ["mysql", "redis"],
        "scaling": {"min_instances": 2, "max_instances": 10, "target_cpu": 70},
    },
    "research_service": {
        "name": "research",
        "port": 5801,
        "health_path": "/health",
        "tags": ["research", "simulation", "evidence"],
        "dependencies": ["mysql", "redis"],
        "scaling": {"min_instances": 2, "max_instances": 5, "target_cpu": 70},
    },
}


def get_service_discovery_config() -> dict[str, Any]:
    """Get service discovery configuration for all Phase 2A services."""
    return SERVICE_DISCOVERY
