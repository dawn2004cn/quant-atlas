from __future__ import annotations

"""Domain-integrated Services - App services using domain layer.

Shows how application services integrate with domain services.
"""



from app.application.domain_facade import (
    get_domain_facade,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class StockServiceWithDomain:
    """Stock service with domain integration.

    This shows how to integrate domain services into
    existing application services.
    """

    def __init__(self, market_provider):
        self._market_provider = market_provider
        self._domain = get_domain_facade()
        logger.info("StockServiceWithDomain initialized")

    def screen_stocks(
        self,
        criteria: dict,
        market: str = "A"
    ) -> list[dict]:
        """Screen stocks using domain service."""
        all_stocks = self._market_provider.list_stocks(market=market)

        return self._domain.screen_stocks(all_stocks, criteria)

    def generate_signal(
        self,
        stock_code: str,
        indicators: dict | None = None
    ) -> dict:
        """Generate signal using domain service."""
        if not indicators:
            indicators = self._market_provider.get_indicators(stock_code)

        return self._domain.generate_signal(stock_code, indicators)


class SignalServiceWithDomain:
    """Signal service with domain integration."""

    def __init__(self, market_provider):
        self._market_provider = market_provider
        self._domain = get_domain_facade()
        logger.info("SignalServiceWithDomain initialized")

    def create_composite_signal(
        self,
        stock_code: str,
        indicators: dict | None = None,
        momentum: dict | None = None
    ) -> dict:
        """Create composite signal from multiple sources."""
        if not indicators:
            indicators = self._market_provider.get_indicators(stock_code)

        if not momentum:
            momentum = self._market_provider.get_momentum(stock_code)

        return self._domain.generate_composite_signal(
            stock_code, indicators, momentum
        )


class PortfolioServiceWithDomain:
    """Portfolio service with domain integration."""

    def __init__(self, market_provider):
        self._market_provider = market_provider
        self._domain = get_domain_facade()
        logger.info("PortfolioServiceWithDomain initialized")

    def calculate_metrics(
        self,
        positions: list[dict],
        cash: float
    ) -> dict:
        """Calculate portfolio metrics using domain service."""
        prices = {}
        for pos in positions:
            quote = self._market_provider.get_quote(pos["stock_code"])
            prices[pos["stock_code"]] = quote.get("price", pos.get("avg_price", 0))

        returns = self._calculate_returns(positions, prices)

        return self._domain.calculate_portfolio_metrics(positions, prices, cash, returns)

    def _calculate_returns(
        self,
        positions: list[dict],
        prices: dict
    ) -> list[float]:
        """Calculate historical returns."""
        return [0.0] * 30

    def get_position_sizing(
        self,
        total_capital: float,
        risk_per_trade: float,
        stock_code: str
    ) -> float:
        """Calculate position size using domain service."""
        quote = self._market_provider.get_quote(stock_code)
        price = quote.get("price", 0)

        return self._domain.get_position_sizing(
            total_capital, risk_per_trade, price, 5.0
        )


class TradingPolicyService:
    """Trading policy service with domain integration."""

    def __init__(self):
        self._domain = get_domain_facade()
        logger.info("TradingPolicyService initialized")

    def check_buy(
        self,
        stock_code: str,
        quantity: float,
        price: float,
        portfolio_value: float,
        current_positions: dict,
        sector_allocation: dict
    ) -> dict:
        """Check buy order against policy."""
        trade_value = quantity * price

        return self._domain.check_trade_policy(
            stock_code=stock_code,
            trade_value=trade_value,
            portfolio_value=portfolio_value,
            current_positions=current_positions,
            sector_allocation=sector_allocation,
            is_buy=True,
        )

    def check_sell(
        self,
        stock_code: str,
        quantity: float,
        price: float,
        portfolio_value: float
    ) -> dict:
        """Check sell order against policy."""
        trade_value = quantity * price

        return self._domain.check_trade_policy(
            stock_code=stock_code,
            trade_value=trade_value,
            portfolio_value=portfolio_value,
            current_positions={},
            sector_allocation={},
            is_buy=False,
        )


__all__ = [
    "StockServiceWithDomain",
    "SignalServiceWithDomain",
    "PortfolioServiceWithDomain",
    "TradingPolicyService",
]
