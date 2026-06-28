from abc import ABC, abstractmethod
from typing import Any


class StrategyServiceABC(ABC):
    """
    Abstract Base Class for managing and executing trading strategies
    based on diverse inputs (e.g., macro data, risk parameters).

    This defines the contract that any concrete strategy implementation must follow.
    """

    @abstractmethod
    def select_stocks(self, strategy_name: str, market: Any, top_n: int) -> dict[str, Any]:
        """
        Identifies a list of candidate stocks based on defined criteria
        and the specified strategy name.
        Must return a structured dictionary containing 'ok', 'candidates', and error details.
        """
        raise NotImplementedError("Must be implemented by concrete class.")

    @abstractmethod
    def execute_trade(self, symbol: str, quantity: int) -> dict[str, Any]:
        """
        Stub for executing a trade decision through the connected broker/system.
        Returns status and transaction hash.
        """
        raise NotImplementedError("Must be implemented by concrete class.")

    @abstractmethod
    def calculate_metrics(self, data: list[Any]) -> dict[str, Any]:
        """
        Performs complex metric calculation (e.g., rolling volatility, correlation matrix).
        Accepts raw data points and returns a structured set of derived insights.
        """
        raise NotImplementedError("Must be implemented by concrete class.")
