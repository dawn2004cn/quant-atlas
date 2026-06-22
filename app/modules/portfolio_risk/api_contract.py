"""Portfolio/Risk Service API Contract (OpenAPI 3.0).

This module defines the external API contract for the Portfolio/Risk Service,
which will be extracted as an independent microservice in Phase 2D.

Current status: In-process monolith (routes registered under /api/v1/*)
Target status: Independent service (routes under /api/v1/portfolio-risk/*)
"""

from __future__ import annotations

from typing import Any


class PortfolioRiskServicePort:
    """Port (interface) for portfolio and risk operations."""

    def get_portfolio(self, user_id: int) -> dict[str, Any]:
        """Get user portfolio holdings."""
        raise NotImplementedError

    def update_portfolio(self, user_id: int, holdings: list[dict[str, Any]]) -> dict[str, Any]:
        """Update portfolio holdings."""
        raise NotImplementedError

    def get_risk_metrics(self, user_id: int) -> dict[str, Any]:
        """Get portfolio risk metrics."""
        raise NotImplementedError

    def run_stress_test(self, user_id: int, scenario: str) -> dict[str, Any]:
        """Run portfolio stress test."""
        raise NotImplementedError

    def submit_trade_plan(self, user_id: int, plan: dict[str, Any]) -> dict[str, Any]:
        """Submit a trade plan for approval."""
        raise NotImplementedError

    def get_trade_plan(self, plan_id: str) -> dict[str, Any]:
        """Get trade plan details."""
        raise NotImplementedError

    def record_signal_observation(self, signal_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        """Record signal observation outcome."""
        raise NotImplementedError

    def get_risk_companion(self, user_id: int) -> dict[str, Any]:
        """Get risk companion analysis."""
        raise NotImplementedError


API_CONTRACT = {
    "service": "portfolio_risk",
    "version": "v1",
    "base_path": "/api/v1/portfolio-risk",
    "endpoints": [
        {
            "method": "GET",
            "path": "/portfolio/{user_id}",
            "summary": "Get user portfolio",
            "params": ["user_id (path)"],
            "response": {"holdings": [], "total_value": "float"},
            "latency_target_ms": 200,
        },
        {
            "method": "PUT",
            "path": "/portfolio/{user_id}",
            "summary": "Update portfolio holdings",
            "params": ["user_id (path)", "holdings (body)"],
            "response": {"updated": "bool"},
            "latency_target_ms": 300,
        },
        {
            "method": "GET",
            "path": "/risk/metrics/{user_id}",
            "summary": "Get risk metrics",
            "params": ["user_id (path)"],
            "response": {"var": "float", "sharpe": "float", "beta": "float"},
            "latency_target_ms": 500,
        },
        {
            "method": "POST",
            "path": "/stress-test/{user_id}",
            "summary": "Run stress test",
            "params": ["user_id (path)", "scenario (body)"],
            "response": {"result": {}, "passed": "bool"},
            "latency_target_ms": 2000,
        },
        {
            "method": "POST",
            "path": "/trade-plan",
            "summary": "Submit trade plan",
            "params": ["user_id (body)", "plan (body)"],
            "response": {"plan_id": "str", "status": "str"},
            "latency_target_ms": 300,
        },
        {
            "method": "GET",
            "path": "/trade-plan/{plan_id}",
            "summary": "Get trade plan",
            "params": ["plan_id (path)"],
            "response": {"plan": {}},
            "latency_target_ms": 200,
        },
        {
            "method": "POST",
            "path": "/signal-observation",
            "summary": "Record signal observation",
            "params": ["signal_id (body)", "outcome (body)"],
            "response": {"recorded": "bool"},
            "latency_target_ms": 200,
        },
        {
            "method": "GET",
            "path": "/risk-companion/{user_id}",
            "summary": "Get risk companion",
            "params": ["user_id (path)"],
            "response": {"analysis": {}, "recommendations": []},
            "latency_target_ms": 1000,
        },
    ],
}


def get_portfolio_risk_api_contract() -> dict[str, Any]:
    """Return the Portfolio/Risk Service API contract."""
    return API_CONTRACT
