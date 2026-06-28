"""Repository base classes and interfaces."""

from .base import (
    AnalysisReportRepositoryBase,
    BasicMarketDataRepositoryBase,
    InvestmentManagerRepositoryBase,
    MomentsRepositoryBase,
    NewsArchiveRepositoryBase,
    SignalFlagPoolRepositoryBase,
)

__all__ = [
    "InvestmentManagerRepositoryBase",
    "BasicMarketDataRepositoryBase",
    "NewsArchiveRepositoryBase",
    "SignalFlagPoolRepositoryBase",
    "MomentsRepositoryBase",
    "AnalysisReportRepositoryBase",
]
