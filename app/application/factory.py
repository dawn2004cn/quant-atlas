"""Service Factory - Creates service instances.

This is a simple factory that provides service instances.
In a full implementation, this would use a DI container.
"""

from app.application.interfaces import (
    IStockService,
    ISignalService,
    IAnalysisService,
    IServiceFactory,
    StockDTO,
    SignalDTO,
)


class StockServiceImpl(IStockService):
    """Stock service implementation."""

    def get_stock(self, code: str) -> StockDTO | None:
        # Placeholder - will be connected to actual implementation
        return None

    def list_stocks(self, market: str, limit: int = 50) -> list[StockDTO]:
        return []

    def search_stocks(self, query: str, limit: int = 20) -> list[StockDTO]:
        return []


class SignalServiceImpl(ISignalService):
    """Signal service implementation."""

    def get_signals(self, stock_code: str) -> list[SignalDTO]:
        return []

    def get_active_signals(self, limit: int = 100) -> list[SignalDTO]:
        return []

    def create_signal(self, stock_code: str, signal_type: str, reason: str, confidence: float) -> SignalDTO:
        return SignalDTO(
            stock_code=stock_code,
            signal_type=signal_type,
            source="system",
            confidence=confidence,
            reason=reason,
        )


class AnalysisServiceImpl(IAnalysisService):
    """Analysis service implementation."""

    def __init__(self, stock_service: IStockService, signal_service: ISignalService):
        self._stock_service = stock_service
        self._signal_service = signal_service

    def analyze_stock(self, code: str) -> dict:
        stock = self._stock_service.get_stock(code)
        if not stock:
            return {"error": "Stock not found"}

        return {
            "stock_code": code,
            "signals": [],
            "summary": f"Analysis for {code}",
            "confidence": 0.5,
        }

    def batch_analyze(self, codes: list[str]) -> list[dict]:
        return [self.analyze_stock(code) for code in codes]


class ServiceFactory(IServiceFactory):
    """Service factory implementation."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
        return cls._instance

    def get_stock_service(self) -> IStockService:
        if "stock" not in self._services:
            self._services["stock"] = StockServiceImpl()
        return self._services["stock"]

    def get_signal_service(self) -> ISignalService:
        if "signal" not in self._services:
            self._services["signal"] = SignalServiceImpl()
        return self._services["signal"]

    def get_analysis_service(self) -> IAnalysisService:
        if "analysis" not in self._services:
            self._services["analysis"] = AnalysisServiceImpl(
                self.get_stock_service(),
                self.get_signal_service()
            )
        return self._services["analysis"]


# Singleton instance
service_factory = ServiceFactory()


__all__ = [
    "IStockService",
    "ISignalService",
    "IAnalysisService",
    "IServiceFactory",
    "StockServiceImpl",
    "SignalServiceImpl",
    "AnalysisServiceImpl",
    "ServiceFactory",
    "service_factory",
]
