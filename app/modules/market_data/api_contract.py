"""Market Data Service API Contract (OpenAPI 3.0).

This module defines the external API contract for the Market Data Service,
which will be extracted as an independent microservice in Phase 2A.

Current status: In-process monolith (routes registered under /api/v1/*)
Target status: Independent service (routes under /api/v1/market/*)
"""

from __future__ import annotations

from typing import Any

# ── Service Port Definition ─────────────────────────────────────────
# This is the interface that the rest of the application uses to
# interact with market data. In Phase 2A, this becomes the contract
# between the monolith and the new Market Data Service.

class MarketDataServicePort:
    """Port (interface) for market data operations.

    All methods are synchronous in the current implementation.
    Phase 2A will introduce async variants.
    """

    def get_quote(self, symbol: str, market: str) -> dict[str, Any]:
        """Get real-time quote for a single symbol."""
        raise NotImplementedError

    def get_quotes(self, symbols: list[str], market: str) -> list[dict[str, Any]]:
        """Get real-time quotes for multiple symbols."""
        raise NotImplementedError

    def get_history(self, symbol: str, market: str, start: str, end: str) -> dict[str, Any]:
        """Get OHLCV history for backtesting."""
        raise NotImplementedError

    def get_sector_members(self, sector: str, market: str) -> list[dict[str, Any]]:
        """Get stocks in a sector/industry."""
        raise NotImplementedError

    def get_hot_sectors(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get hot/momentum sectors."""
        raise NotImplementedError

    def get_sentiment(self, symbols: list[str]) -> dict[str, Any]:
        """Get market sentiment for symbols."""
        raise NotImplementedError

    def get_global_quote(self, symbol: str, market: str) -> dict[str, Any]:
        """Get global market quote (US, HK, CN)."""
        raise NotImplementedError

    def get_fundamental(self, symbol: str, market: str) -> dict[str, Any]:
        """Get fundamental data (PE, PB, market cap)."""
        raise NotImplementedError


# ── API Route Contract (OpenAPI-style docstrings) ───────────────────
# These define the HTTP API that the Market Data Service will expose.
# Used for documentation, validation, and eventual service mesh config.

API_CONTRACT = {
    "service": "market-data",
    "version": "v1",
    "base_path": "/api/v1/market",
    "endpoints": [
        {
            "method": "GET",
            "path": "/quotes/{market}/{symbol}",
            "summary": "Get real-time quote",
            "params": ["market (path)", "symbol (path)"],
            "response": {"price": "float", "change_pct": "float", "volume": "int"},
            "latency_target_ms": 50,
        },
        {
            "method": "GET",
            "path": "/quotes/{market}",
            "summary": "Get batch quotes",
            "params": ["market (path)", "symbols (query, comma-separated)"],
            "response": [{"symbol": "str", "price": "float"}],
            "latency_target_ms": 100,
        },
        {
            "method": "GET",
            "path": "/history/{market}/{symbol}",
            "summary": "Get OHLCV history",
            "params": [
                "market (path)",
                "symbol (path)",
                "start (query, YYYYMMDD)",
                "end (query, YYYYMMDD)",
            ],
            "response": {"dates": ["str"], "open": ["float"], "high": ["float"], "low": ["float"], "close": ["float"], "volume": ["int"]},
            "latency_target_ms": 200,
        },
        {
            "method": "GET",
            "path": "/sectors/{market}",
            "summary": "Get sector members",
            "params": ["market (path)", "sector (query)"],
            "response": [{"symbol": "str", "name": "str", "weight": "float"}],
            "latency_target_ms": 100,
        },
        {
            "method": "GET",
            "path": "/hot-sectors",
            "summary": "Get hot sectors",
            "params": ["limit (query, default 20)"],
            "response": [{"name": "str", "change_pct": "float", "volume": "int"}],
            "latency_target_ms": 100,
        },
        {
            "method": "GET",
            "path": "/sentiment",
            "summary": "Get market sentiment",
            "params": ["symbols (query, comma-separated)"],
            "response": {"symbol": "str", "sentiment": "float", "confidence": "float"},
            "latency_target_ms": 150,
        },
        {
            "method": "GET",
            "path": "/global/quote",
            "summary": "Get global quote",
            "params": ["symbol (query)", "market (query, US|HK|CN)"],
            "response": {"symbol": "str", "price": "float", "currency": "str"},
            "latency_target_ms": 200,
        },
        {
            "method": "GET",
            "path": "/fundamental/{market}/{symbol}",
            "summary": "Get fundamental data",
            "params": ["market (path)", "symbol (path)"],
            "response": {"pe": "float", "pb": "float", "market_cap": "float"},
            "latency_target_ms": 300,
        },
    ],
}


def get_market_data_api_contract() -> dict[str, Any]:
    """Return the Market Data Service API contract."""
    return API_CONTRACT
