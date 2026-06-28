from __future__ import annotations
"""Application Service Interfaces.

Defines contracts for application services following clean architecture.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass


# =============================================================================
# DTOs
# =============================================================================

@dataclass
class StockDTO:
    """Stock Data Transfer Object."""
    code: str
    name: str
    market: str
    price: float | None = None
    change: float | None = None
    volume: int | None = None


@dataclass
class SignalDTO:
    """Signal Data Transfer Object."""
    stock_code: str
    signal_type: str
    source: str
    confidence: float
    reason: str
    created_at: str


@dataclass
class AnalysisResultDTO:
    """Analysis result Data Transfer Object."""
    stock_code: str
    signals: list[SignalDTO]
    summary: str
    confidence: float


# =============================================================================
# Service Interfaces
# =============================================================================

class IStockService(ABC):
    """Stock service interface."""

    @abstractmethod
    def get_stock(self, code: str) -> StockDTO | None:
        """Get stock by code."""
        pass

    @abstractmethod
    def list_stocks(self, market: str, limit: int = 50) -> list[StockDTO]:
        """List stocks by market."""
        pass

    @abstractmethod
    def search_stocks(self, query: str, limit: int = 20) -> list[StockDTO]:
        """Search stocks."""
        pass


class ISignalService(ABC):
    """Signal service interface."""

    @abstractmethod
    def get_signals(self, stock_code: str) -> list[SignalDTO]:
        """Get signals for a stock."""
        pass

    @abstractmethod
    def get_active_signals(self, limit: int = 100) -> list[SignalDTO]:
        """Get active signals."""
        pass

    @abstractmethod
    def create_signal(self, stock_code: str, signal_type: str, reason: str, confidence: float) -> SignalDTO:
        """Create a new signal."""
        pass


class IAnalysisService(ABC):
    """Analysis service interface."""

    @abstractmethod
    def analyze_stock(self, code: str) -> AnalysisResultDTO:
        """Analyze a stock and return signals."""
        pass

    @abstractmethod
    def batch_analyze(self, codes: list[str]) -> list[AnalysisResultDTO]:
        """Batch analyze multiple stocks."""
        pass


# =============================================================================
# Factory Interface
# =============================================================================

class IServiceFactory(ABC):
    """Service factory interface."""

    @abstractmethod
    def get_stock_service(self) -> IStockService:
        pass

    @abstractmethod
    def get_signal_service(self) -> ISignalService:
        pass

    @abstractmethod
    def get_analysis_service(self) -> IAnalysisService:
        pass


__all__ = [
    "StockDTO",
    "SignalDTO",
    "AnalysisResultDTO",
    "IStockService",
    "ISignalService",
    "IAnalysisService",
    "IServiceFactory",
]
