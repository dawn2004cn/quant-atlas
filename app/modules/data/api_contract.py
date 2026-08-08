"""Data Service API Contract (OpenAPI 3.0).

This module defines the external API contract for the Data Service,
which will be extracted as an independent microservice in Phase 2G.

Current status: In-process monolith (routes registered under /api/v1/*)
Target status: Independent service (routes under /api/v1/data/*)
"""

from __future__ import annotations

from typing import Any


class DataServicePort:
    """Port (interface) for data operations."""

    def get_data_infrastructure_status(self) -> dict[str, Any]:
        """Get data infrastructure status."""
        raise NotImplementedError

    def query_data_lake(self, query: dict[str, Any]) -> dict[str, Any]:
        """Query data lake."""
        raise NotImplementedError

    def run_data_optimizer(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run data optimizer."""
        raise NotImplementedError

    def verify_data_quality(self, source: str) -> dict[str, Any]:
        """Verify data quality."""
        raise NotImplementedError

    def get_historical_resonance(self, symbol: str) -> dict[str, Any]:
        """Get historical resonance data."""
        raise NotImplementedError

    def get_memory_optimization(self) -> dict[str, Any]:
        """Get memory optimization status."""
        raise NotImplementedError

    def query_pytdx(self, params: dict[str, Any]) -> dict[str, Any]:
        """Query via pytdx."""
        raise NotImplementedError

    def get_qlib_research_data(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get Qlib research data."""
        raise NotImplementedError

    def get_task_pipeline_status(self) -> dict[str, Any]:
        """Get task pipeline status."""
        raise NotImplementedError

    def get_truth_badge(self, market: str, symbol: str) -> dict[str, Any]:
        """Get truth badge for a symbol."""
        raise NotImplementedError


API_CONTRACT = {
    "service": "data",
    "version": "v1",
    "base_path": "/api/v1/data",
    "endpoints": [
        {
            "method": "GET",
            "path": "/infrastructure/status",
            "summary": "Get data infrastructure status",
            "params": [],
            "response": {"status": "str", "services": {}},
            "latency_target_ms": 200,
        },
        {
            "method": "POST",
            "path": "/lake/query",
            "summary": "Query data lake",
            "params": ["query (body)"],
            "response": {"result": {}},
            "latency_target_ms": 1000,
        },
        {
            "method": "POST",
            "path": "/optimizer/run",
            "summary": "Run data optimizer",
            "params": ["params (body)"],
            "response": {"result": {}},
            "latency_target_ms": 2000,
        },
        {
            "method": "GET",
            "path": "/quality/verify/{source}",
            "summary": "Verify data quality",
            "params": ["source (path)"],
            "response": {"quality": "float"},
            "latency_target_ms": 500,
        },
        {
            "method": "GET",
            "path": "/resonance/{symbol}",
            "summary": "Get historical resonance",
            "params": ["symbol (path)"],
            "response": {"resonance": {}},
            "latency_target_ms": 300,
        },
        {
            "method": "GET",
            "path": "/memory/optimization",
            "summary": "Get memory optimization",
            "params": [],
            "response": {"optimization": {}},
            "latency_target_ms": 200,
        },
        {
            "method": "POST",
            "path": "/pytdx/query",
            "summary": "Query via pytdx",
            "params": ["params (body)"],
            "response": {"result": {}},
            "latency_target_ms": 500,
        },
        {
            "method": "GET",
            "path": "/qlib/research",
            "summary": "Get Qlib research data",
            "params": ["params (query)"],
            "response": {"data": {}},
            "latency_target_ms": 1000,
        },
        {
            "method": "GET",
            "path": "/pipeline/status",
            "summary": "Get task pipeline status",
            "params": [],
            "response": {"status": {}},
            "latency_target_ms": 200,
        },
        {
            "method": "GET",
            "path": "/truth-badge/{market}/{symbol}",
            "summary": "Get truth badge",
            "params": ["market (path)", "symbol (path)"],
            "response": {"badge": {}},
            "latency_target_ms": 300,
        },
    ],
}


def get_data_api_contract() -> dict[str, Any]:
    """Return the Data Service API contract."""
    return API_CONTRACT
