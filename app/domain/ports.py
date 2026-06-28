from __future__ import annotations

"""Domain ports to support dependency inversion.

DEPRECATED: This module is kept for backward compatibility.
Please use domain.ports package instead:

    from domain.ports import MarketDataProvider
    # or
    from domain.ports.market_ports import MarketDataProvider

This file will be removed in a future version.
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
