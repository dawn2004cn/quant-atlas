from __future__ import annotations
"""Domain Service Facade - Wires domain services to application layer.

Provides unified access to domain services from application layer.
"""



from app.domain.services.stock_screening_service import (
    StockScreeningService,
)
from app.domain.services.signal_generation_service import (
    SignalGenerationService,
    SignalAggregator,
)
from app.domain.services.portfolio_calculation_service import (
    PortfolioCalculationService,
    PortfolioValuator,
)
from app.domain.services.trading_policy_service import (
    TradingPolicyService,
    TradingPolicy,
)


from app.core.logger import get_logger

logger = get_logger(__name__)


class DomainServiceFacade:
    """Facade for domain services.

    Provides unified access to all domain services
    for use by application layer services.
    """

    def __init__(self):
        self._screening_service = StockScreeningService()
        self._signal_service = SignalGenerationService()
        self._portfolio_service = PortfolioCalculationService()
        self._portfolio_valuator = PortfolioValuator()
        self._trading_policy = TradingPolicyService()
        logger.info("DomainServiceFacade initialized")

    @property
    def screening(self) -> StockScreeningService:
        """Get stock screening service."""
        return self._screening_service

    @property
    def signals(self) -> SignalGenerationService:
        """Get signal generation service."""
        return self._signal_service

    @property
    def portfolio(self) -> PortfolioCalculationService:
        """Get portfolio calculation service."""
        return self._portfolio_service

    @property
    def valuator(self) -> PortfolioValuator:
        """Get portfolio valuator."""
        return self._portfolio_valuator

    @property
    def policy(self) -> TradingPolicyService:
        """Get trading policy service."""
        return self._trading_policy

    def screen_stocks(
        self,
        stocks: list[dict],
        criteria: dict
    ) -> list[dict]:
        """Screen stocks using domain service."""
        service = StockScreeningService()

        if criteria.get("min_price"):
            service.with_price_range(min_price=criteria["min_price"])
        if criteria.get("max_price"):
            service.with_price_range(max_price=criteria["max_price"])
        if criteria.get("min_volume"):
            service.with_min_volume(criteria["min_volume"])
        if criteria.get("min_pe") or criteria.get("max_pe"):
            service.with_pe_range(
                min_pe=criteria.get("min_pe", 0),
                max_pe=criteria.get("max_pe", float("inf")),
            )
        if criteria.get("industry"):
            service.with_industry(criteria["industry"])
        if criteria.get("min_change_pct") or criteria.get("max_change_pct"):
            service.with_change_pct_range(
                min_pct=criteria.get("min_change_pct", float("-inf")),
                max_pct=criteria.get("max_change_pct", float("inf")),
            )

        return service.screen(stocks)

    def generate_signal(
        self,
        stock_code: str,
        indicators: dict
    ) -> dict:
        """Generate signal using domain service."""
        signal = self._signal_service.generate_from_technical(stock_code, indicators)

        return {
            "stock_code": signal.stock_code,
            "signal_type": signal.signal_type,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "strength": signal.strength.value,
            "is_expired": signal.is_expired,
        }

    def generate_composite_signal(
        self,
        stock_code: str,
        technical_indicators: dict,
        momentum_returns: dict
    ) -> dict:
        """Generate composite signal."""
        aggregator = SignalAggregator()
        signal = aggregator.aggregate_all(
            stock_code, technical_indicators, momentum_returns
        )

        return {
            "stock_code": signal.stock_code,
            "signal_type": signal.signal_type,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "strength": signal.strength.value,
        }

    def calculate_portfolio_metrics(
        self,
        positions: list[dict],
        prices: dict,
        cash: float,
        returns: list[float]
    ) -> dict:
        """Calculate portfolio metrics."""
        snapshot = self._valuator.create_snapshot(positions, prices, cash)
        risk = self._portfolio.calculate_risk_metrics(returns)

        return {
            "total_market_value": snapshot.total_market_value,
            "total_pnl": snapshot.total_pnl,
            "pnl_pct": snapshot.pnl_pct,
            "volatility": risk.volatility,
            "sharpe_ratio": risk.sharpe_ratio,
            "max_drawdown": risk.max_drawdown,
            "risk_score": risk.risk_score,
        }

    def check_trade_policy(
        self,
        stock_code: str,
        trade_value: float,
        portfolio_value: float,
        current_positions: dict,
        sector_allocation: dict,
        is_buy: bool = True
    ) -> dict:
        """Check trade against policy."""
        if is_buy:
            result = self._trading_policy.check_buy(
                stock_code, trade_value, portfolio_value,
                current_positions, sector_allocation
            )
        else:
            result = self._trading_policy.check_sell(
                stock_code, trade_value, portfolio_value
            )

        return {
            "action": result.action.value,
            "is_allowed": result.is_allowed,
            "is_blocked": result.is_blocked,
            "violations": [v.value for v in result.violations],
            "message": result.message,
        }

    def set_trading_policy(self, policy: TradingPolicy) -> None:
        """Set custom trading policy."""
        self._trading_policy = TradingPolicyService(policy)
        logger.info("Trading policy updated")

    def get_position_sizing(
        self,
        total_capital: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss_pct: float
    ) -> float:
        """Calculate position sizing."""
        return self._portfolio.calculate_position_sizing(
            total_capital, risk_per_trade, entry_price, stop_loss_pct
        )


class DomainServiceRegistry:
    """Registry for domain service facades per context."""

    _instance: DomainServiceRegistry | None = None
    _facades: dict[str, DomainServiceFacade] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._facades = {}
        return cls._instance

    def get_facade(self, context: str = "default") -> DomainServiceFacade:
        """Get facade for context."""
        if context not in self._facades:
            self._facades[context] = DomainServiceFacade()
        return self._facades[context]

    def register_facade(self, context: str, facade: DomainServiceFacade) -> None:
        """Register a facade."""
        self._facades[context] = facade


_global_facade: DomainServiceFacade | None = None


def get_domain_facade() -> DomainServiceFacade:
    """Get global domain facade."""
    global _global_facade
    if _global_facade is None:
        _global_facade = DomainServiceFacade()
    return _global_facade


def screen_stocks(stocks: list[dict], criteria: dict) -> list[dict]:
    """Convenience function for stock screening."""
    return get_domain_facade().screen_stocks(stocks, criteria)


def generate_signal(stock_code: str, indicators: dict) -> dict:
    """Convenience function for signal generation."""
    return get_domain_facade().generate_signal(stock_code, indicators)


def check_trade_policy(
    stock_code: str,
    trade_value: float,
    portfolio_value: float,
    **kwargs
) -> dict:
    """Convenience function for trade policy check."""
    return get_domain_facade().check_trade_policy(
        stock_code, trade_value, portfolio_value, **kwargs
    )


__all__ = [
    "DomainServiceFacade",
    "DomainServiceRegistry",
    "get_domain_facade",
    "screen_stocks",
    "generate_signal",
    "check_trade_policy",
]
