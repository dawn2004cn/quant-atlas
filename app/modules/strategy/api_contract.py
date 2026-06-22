"""Strategy Service API Contract (OpenAPI 3.0).

This module defines the external API contract for the Strategy Service,
which will be extracted as an independent microservice in Phase 2B.

Current status: In-process monolith (routes registered under /api/v1/*)
Target status: Independent service (routes under /api/v1/strategy/*)
"""

from __future__ import annotations

from typing import Any


class StrategyServicePort:
    """Port (interface) for strategy operations.

    All methods are synchronous in the current implementation.
    Phase 2B will introduce async variants for CPU-intensive operations.
    """

    def get_recommendations(self, user_id: int, market: str) -> list[dict[str, Any]]:
        """Get stock recommendations for a user."""
        raise NotImplementedError

    def scan_signals(self, symbols: list[str], strategy_id: str) -> dict[str, Any]:
        """Run signal scan on given symbols."""
        raise NotImplementedError

    def get_factor(self, factor_id: str) -> dict[str, Any]:
        """Get factor details and performance."""
        raise NotImplementedError

    def list_factors(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available factors."""
        raise NotImplementedError

    def run_backtest(self, strategy_id: str, start: str, end: str) -> dict[str, Any]:
        """Run strategy backtest."""
        raise NotImplementedError

    def get_strategy_snapshot(self, strategy_id: str) -> dict[str, Any]:
        """Get strategy performance snapshot."""
        raise NotImplementedError

    def synthesize_strategy(self, market_regime: str, constraints: dict[str, Any]) -> dict[str, Any]:
        """Synthesize a new strategy based on market regime."""
        raise NotImplementedError

    def get_attribution(self, strategy_id: str, period: str) -> dict[str, Any]:
        """Get strategy attribution analysis."""
        raise NotImplementedError

    def submit_review(self, strategy_id: str, review_data: dict[str, Any]) -> dict[str, Any]:
        """Submit strategy review/correction."""
        raise NotImplementedError

    def get_briefing(self, user_id: int) -> dict[str, Any]:
        """Get daily strategy briefing."""
        raise NotImplementedError


API_CONTRACT = {
    "service": "strategy",
    "version": "v1",
    "base_path": "/api/v1/strategy",
    "endpoints": [
        {
            "method": "GET",
            "path": "/recommendations",
            "summary": "Get stock recommendations",
            "params": ["user_id (query)", "market (query)"],
            "response": [{"symbol": "str", "score": "float", "reason": "str"}],
            "latency_target_ms": 200,
        },
        {
            "method": "POST",
            "path": "/signals/scan",
            "summary": "Run signal scan",
            "params": ["symbols (body array)", "strategy_id (body)"],
            "response": {"signals": [], "scan_id": "str"},
            "latency_target_ms": 500,
        },
        {
            "method": "GET",
            "path": "/factors",
            "summary": "List factors",
            "params": ["category (query, optional)"],
            "response": [{"id": "str", "name": "str", "sharpe": "float"}],
            "latency_target_ms": 100,
        },
        {
            "method": "GET",
            "path": "/factors/{factor_id}",
            "summary": "Get factor details",
            "params": ["factor_id (path)"],
            "response": {"id": "str", "formula": "str", "performance": {}},
            "latency_target_ms": 100,
        },
        {
            "method": "POST",
            "path": "/backtest",
            "summary": "Run backtest",
            "params": ["strategy_id (body)", "start (body)", "end (body)"],
            "response": {"total_return": "float", "sharpe": "float", "trades": []},
            "latency_target_ms": 2000,
        },
        {
            "method": "GET",
            "path": "/snapshot/{strategy_id}",
            "summary": "Get strategy snapshot",
            "params": ["strategy_id (path)"],
            "response": {"strategy_id": "str", "performance": {}, "positions": []},
            "latency_target_ms": 200,
        },
        {
            "method": "POST",
            "path": "/synthesize",
            "summary": "Synthesize new strategy",
            "params": ["market_regime (body)", "constraints (body)"],
            "response": {"strategy_id": "str", "components": []},
            "latency_target_ms": 3000,
        },
        {
            "method": "GET",
            "path": "/attribution/{strategy_id}",
            "summary": "Get strategy attribution",
            "params": ["strategy_id (path)", "period (query)"],
            "response": {"factor_contributions": [], "sector_weights": {}},
            "latency_target_ms": 300,
        },
        {
            "method": "POST",
            "path": "/review",
            "summary": "Submit strategy review",
            "params": ["strategy_id (body)", "review_data (body)"],
            "response": {"review_id": "str", "status": "str"},
            "latency_target_ms": 200,
        },
        {
            "method": "GET",
            "path": "/briefing",
            "summary": "Get daily strategy briefing",
            "params": ["user_id (query)"],
            "response": {"date": "str", "summary": "str", "actions": []},
            "latency_target_ms": 500,
        },
    ],
}


def get_strategy_api_contract() -> dict[str, Any]:
    """Return the Strategy Service API contract."""
    return API_CONTRACT
