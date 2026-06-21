from __future__ import annotations
"""Service Migration Wrapper - Migrates existing services to use domain layer.

This module shows how to migrate existing application services
to use the domain layer infrastructure.
"""


import logging
from typing import Any, Optional

from app.application.domain_facade import get_domain_facade
from app.application.aggregate_registry import get_aggregate_registry
from app.application.event_publisher import get_event_publisher


from app.core.logger import get_logger

logger = get_logger(__name__)


class StockServiceMigrated:
    """Stock service using domain layer.
    
    This is a reference implementation showing how to migrate
    from direct implementation to domain-based.
    """
    
    def __init__(self, market_provider=None):
        self._market_provider = market_provider
        self._domain = get_domain_facade()
        self._aggregates = get_aggregate_registry()
        logger.info("StockServiceMigrated initialized")
    
    def screen_stocks(self, criteria: dict) -> list[dict]:
        """Screen stocks using domain service."""
        all_stocks = self._market_provider.list_stocks(market="A")
        results = self._domain.screen_stocks(all_stocks, criteria)
        logger.info(f"Screened {len(results)} stocks")
        return results
    
    def get_stock(self, stock_code: str) -> dict:
        """Get stock with domain aggregate."""
        aggregate = self._aggregates.get_stock(stock_code)
        
        if aggregate:
            return aggregate.to_dict()
        
        stock_data = self._market_provider.get_quote(stock_code)
        
        if stock_data:
            self._aggregates.create_stock(
                stock_code=stock_code,
                name=stock_data.get("name", ""),
                market="A"
            )
            aggregate = self._aggregates.get_stock(stock_code)
            if aggregate:
                return aggregate.to_dict()
        
        return {"error": "Stock not found"}
    
    def create_stock(self, stock_code: str, name: str, market: str = "A") -> dict:
        """Create stock using domain aggregate."""
        aggregate = self._aggregates.create_stock(stock_code, name, market)
        
        from app.application.event_publisher import emit_stock_created
        emit_stock_created(stock_code, name, market)
        
        return {"status": "created", "stock_code": stock_code}


class SignalServiceMigrated:
    """Signal service using domain layer."""
    
    def __init__(self, market_provider=None):
        self._market_provider = market_provider
        self._domain = get_domain_facade()
        logger.info("SignalServiceMigrated initialized")
    
    def generate_signal(self, stock_code: str) -> dict:
        """Generate signal using domain service."""
        indicators = self._market_provider.get_indicators(stock_code)
        
        signal = self._domain.generate_signal(stock_code, indicators)
        
        from app.application.event_publisher import emit_signal_generated
        emit_signal_generated(
            stock_code,
            signal["signal_type"],
            signal["confidence"],
            "domain_service"
        )
        
        return signal
    
    def generate_composite_signal(self, stock_code: str) -> dict:
        """Generate composite signal."""
        indicators = self._market_provider.get_indicators(stock_code)
        momentum = self._market_provider.get_momentum(stock_code)
        
        return self._domain.generate_composite_signal(stock_code, indicators, momentum)
    
    def screen_signals(self, stocks: list[dict]) -> list[dict]:
        """Screen stocks and generate signals."""
        results = []
        
        for stock in stocks:
            code = stock.get("code")
            try:
                signal = self.generate_signal(code)
                results.append({
                    "stock_code": code,
                    "signal": signal,
                })
            except Exception as e:
                logger.error(f"Error generating signal for {code}: {e}")
        
        return results


class PortfolioServiceMigrated:
    """Portfolio service using domain layer."""
    
    def __init__(self, market_provider=None):
        self._market_provider = market_provider
        self._domain = get_domain_facade()
        self._aggregates = get_aggregate_registry()
        logger.info("PortfolioServiceMigrated initialized")
    
    def calculate_metrics(self, portfolio_id: str) -> dict:
        """Calculate portfolio metrics."""
        portfolio = self._aggregates.get_portfolio(portfolio_id)
        
        if not portfolio:
            return {"error": "Portfolio not found"}
        
        prices = {}
        for pos in portfolio._positions:
            quote = self._market_provider.get_quote(pos.stock_code)
            prices[pos.stock_code] = quote.get("price", pos.avg_price)
        
        snapshot = portfolio.create_snapshot(prices)
        
        returns = self._calculate_returns(portfolio)
        
        metrics = self._domain.calculate_portfolio_metrics(
            portfolio._positions,
            prices,
            portfolio.cash,
            returns
        )
        
        return metrics
    
    def _calculate_returns(self, portfolio) -> list[float]:
        """Calculate historical returns."""
        return [0.0] * 30
    
    def rebalance(self, portfolio_id: str, target_allocations: dict) -> dict:
        """Rebalance portfolio."""
        portfolio = self._aggregates.get_portfolio(portfolio_id)
        
        if not portfolio:
            return {"error": "Portfolio not found"}
        
        prices = {}
        for pos in portfolio._positions:
            quote = self._market_provider.get_quote(pos.stock_code)
            prices[pos.stock_code] = quote.get("price", pos.avg_price)
        
        rebalances = portfolio.rebalance(target_allocations, prices)
        
        portfolio.apply_rebalance(rebalances, prices)
        
        return {"status": "rebalanced", "changes": rebalances}


class TradingPolicyServiceMigrated:
    """Trading policy service using domain layer."""
    
    def __init__(self):
        self._domain = get_domain_facade()
        logger.info("TradingPolicyServiceMigrated initialized")
    
    def check_buy(
        self,
        stock_code: str,
        quantity: float,
        price: float,
        portfolio_value: float,
        current_positions: dict
    ) -> dict:
        """Check buy against policy."""
        trade_value = quantity * price
        
        return self._domain.check_trade_policy(
            stock_code=stock_code,
            trade_value=trade_value,
            portfolio_value=portfolio_value,
            current_positions=current_positions,
            sector_allocation={},
            is_buy=True
        )
    
    def check_sell(
        self,
        stock_code: str,
        quantity: float,
        price: float,
        portfolio_value: float
    ) -> dict:
        """Check sell against policy."""
        trade_value = quantity * price
        
        return self._domain.check_trade_policy(
            stock_code=stock_code,
            trade_value=trade_value,
            portfolio_value=portfolio_value,
            current_positions={},
            sector_allocation={},
            is_buy=False
        )


class ServiceMigrationGuide:
    """Guide for migrating services to domain layer."""
    
    @staticmethod
    def get_old_pattern_comparison() -> dict:
        """Show old vs new pattern comparison."""
        return {
            "stock_screening": {
                "old": "Direct filtering in service",
                "new": "StockScreeningService + DomainFacade",
            },
            "signal_generation": {
                "old": "Hard-coded logic",
                "new": "SignalGenerationService",
            },
            "portfolio": {
                "old": "Simple calculations",
                "new": "PortfolioCalculationService + PortfolioAggregate",
            },
            "policy": {
                "old": "Inline checks",
                "new": "TradingPolicyService",
            },
        }
    
    @staticmethod
    def get_migration_steps(service_name: str) -> list[str]:
        """Get migration steps for a service."""
        steps = {
            "StockService": [
                "1. Import DomainServiceFacade",
                "2. Add domain facade to __init__",
                "3. Replace screening with facade.screen_stocks()",
                "4. Replace signal with facade.generate_signal()",
                "5. Run tests",
            ],
            "SignalService": [
                "1. Import SignalGenerationService",
                "2. Add domain service to __init__",
                "3. Replace logic with service methods",
                "4. Add event publishing",
                "5. Run tests",
            ],
            "PortfolioService": [
                "1. Import PortfolioCalculationService",
                "2. Add domain facade to __init__",
                "3. Use PortfolioAggregate for positions",
                "4. Use calculate_portfolio_metrics()",
                "5. Run tests",
            ],
        }
        return steps.get(service_name, [])


__all__ = [
    "StockServiceMigrated",
    "SignalServiceMigrated", 
    "PortfolioServiceMigrated",
    "TradingPolicyServiceMigrated",
    "ServiceMigrationGuide",
]