"""
Facade package exposing high-level APIs for the Quant Atlas platform.
Each facade groups related services behind a simple, stable interface.
"""

from app.facade.ai_facade import AIFacade
from app.facade.backtest_facade import BacktestFacade
from app.facade.market_facade import MarketFacade

__all__ = ["MarketFacade", "BacktestFacade", "AIFacade"]
