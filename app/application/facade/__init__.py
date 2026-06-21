"""Application-layer facade entry — stable imports for presentation and tasks.

Re-exports the platform facades from ``app.facade`` so routes and jobs
depend on ``app.application.facade`` instead of reaching into services.
"""

from app.facade import AIFacade, BacktestFacade, MarketFacade
from app.facade.dto import AIAnalysisResultDTO, BacktestResultDTO

__all__ = [
    "AIFacade",
    "AIAnalysisResultDTO",
    "BacktestFacade",
    "BacktestResultDTO",
    "MarketFacade",
]
