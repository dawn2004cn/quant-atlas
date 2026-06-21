from __future__ import annotations
"""Bound market data provider for application services (configured at bootstrap)."""

from app.domain.ports.market_ports import MarketDataProvider

_provider: MarketDataProvider | None = None


def bind_market_data_provider(provider: MarketDataProvider) -> None:
    global _provider
    _provider = provider


def get_market_data_provider() -> MarketDataProvider:
    if _provider is None:
        raise RuntimeError(
            "MarketDataProvider not configured; bootstrap must call bind_market_data_provider()"
        )
    return _provider
