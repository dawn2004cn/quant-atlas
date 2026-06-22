"""Execution Service API Contract (OpenAPI 3.0).

This module defines the external API contract for the Execution Service,
which will be extracted as an independent microservice in Phase 2E.

Current status: In-process monolith (routes registered under /api/v1/*)
Target status: Independent service (routes under /api/v1/execution/*)
"""

from __future__ import annotations

from typing import Any


class ExecutionServicePort:
    """Port (interface) for execution operations."""

    def execute_trade(self, order: dict[str, Any]) -> dict[str, Any]:
        """Execute a trade order."""
        raise NotImplementedError

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get order execution status."""
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel a pending order."""
        raise NotImplementedError

    def run_simulation(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run trading simulation."""
        raise NotImplementedError

    def get_execution_history(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get execution history."""
        raise NotImplementedError


API_CONTRACT = {
    "service": "execution",
    "version": "v1",
    "base_path": "/api/v1/execution",
    "endpoints": [
        {
            "method": "POST",
            "path": "/trade/execute",
            "summary": "Execute trade order",
            "params": ["order (body)"],
            "response": {"order_id": "str", "status": "str"},
            "latency_target_ms": 500,
        },
        {
            "method": "GET",
            "path": "/order/{order_id}/status",
            "summary": "Get order status",
            "params": ["order_id (path)"],
            "response": {"status": "str", "filled": "float"},
            "latency_target_ms": 200,
        },
        {
            "method": "POST",
            "path": "/order/{order_id}/cancel",
            "summary": "Cancel order",
            "params": ["order_id (path)"],
            "response": {"cancelled": "bool"},
            "latency_target_ms": 300,
        },
        {
            "method": "POST",
            "path": "/simulation/run",
            "summary": "Run simulation",
            "params": ["params (body)"],
            "response": {"result": {}},
            "latency_target_ms": 5000,
        },
        {
            "method": "GET",
            "path": "/history/{user_id}",
            "summary": "Get execution history",
            "params": ["user_id (path)", "limit (query)"],
            "response": [{"order_id": "str", "status": "str"}],
            "latency_target_ms": 300,
        },
    ],
}


def get_execution_api_contract() -> dict[str, Any]:
    """Return the Execution Service API contract."""
    return API_CONTRACT
