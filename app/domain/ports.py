from __future__ import annotations

"""Domain port contracts — backward-compatible re-export shim.

Canonical import path::

    from app.domain.ports import MarketDataProvider
    from app.domain.ports.market_ports import MarketDataProvider

The flat module ``app.domain.ports`` (this file) re-exports the ``ports/`` package.
"""

from .ports import (
    AgentLLMPort,
    AgentRepository,
    BacktestProvider,
    ExchangePort,
    FinGPTPersistencePort,
    IndicatorProvider,
    KronosPredictorPort,
    KronosRepository,
    MarketDataProvider,
    NewsProvider,
    OpenBBRepository,
    PaymentGatewayPort,
    PaymentRepository,
    QlibDataProviderPort,
    QuantMLFactorRepository,
    SentimentProvider,
    StockGroupRepository,
    StrategyProvider,
    ToolFacadePort,
    TradeRepository,
    TradingBotProvider,
    UserRepository,
    WatchlistRepository,
    WebSearchProvider,
)

__all__ = [
    "MarketDataProvider",
    "NewsProvider",
    "WebSearchProvider",
    "SentimentProvider",
    "FinGPTPersistencePort",
    "IndicatorProvider",
    "StrategyProvider",
    "BacktestProvider",
    "TradeRepository",
    "ExchangePort",
    "TradingBotProvider",
    "UserRepository",
    "WatchlistRepository",
    "StockGroupRepository",
    "PaymentRepository",
    "PaymentGatewayPort",
    "KronosRepository",
    "KronosPredictorPort",
    "OpenBBRepository",
    "QuantMLFactorRepository",
    "AgentRepository",
    "AgentLLMPort",
    "ToolFacadePort",
    "QlibDataProviderPort",
]
