from abc import ABC, abstractmethod

from app.domain.dto.trade_signal_dto import TradeSignalDTO


class ITradeExecutor(ABC):
    @abstractmethod
    def execute(self, signal: TradeSignalDTO) -> str:
        """Execute a trade signal, return order_id."""
        pass

    @abstractmethod
    def cancel(self, order_id: str) -> bool:
        """Cancel an order."""
        pass
