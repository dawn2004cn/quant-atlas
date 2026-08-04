"""Application-layer facade entry — stable imports for presentation and tasks.

Real implementations live here; app.facade is a shim for backward compat.
"""
from app.application.facade.ai_facade import AIFacade
from app.application.facade.backtest_facade import BacktestFacade
from app.application.facade.market_data_facade import MarketDataFacade
from app.application.facade.market_facade import MarketFacade
from app.application.facade.dto import AIAnalysisResultDTO, BacktestResultDTO

__all__ = [
    "AIFacade",
    "AIAnalysisResultDTO",
    "BacktestFacade",
    "BacktestResultDTO",
    "MarketDataFacade",
    "MarketFacade",
]
