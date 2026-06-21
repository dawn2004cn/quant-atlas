from __future__ import annotations
"""Trading and strategy ports."""


from abc import ABC, abstractmethod
from typing import Any

from ..trading_entities import Trade, Order, SignalType


class StrategyProvider(ABC):
    """Port for trading strategy providers."""

    @abstractmethod
    def list_strategies(self) -> list[dict[str, Any]]:
        """List available strategies."""
        raise NotImplementedError

    @abstractmethod
    def generate_signals(self, symbol: str, market: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate trading signals."""
        raise NotImplementedError


class BacktestProvider(ABC):
    """Port for backtesting engines."""

    @abstractmethod
    def backtest(
        self,
        symbol: str,
        strategy: str,
        start: str,
        end: str,
        initial_capital: float = 100000.0,
    ) -> dict[str, Any]:
        """Run backtest and return results."""
        raise NotImplementedError


class TradeRepository(ABC):
    """Port for trade persistence."""

    @abstractmethod
    def save_trade(self, trade: Trade) -> str:
        """Save trade and return ID."""
        raise NotImplementedError

    @abstractmethod
    def list_trades(self, symbol: str | None = None, limit: int = 100) -> list[Trade]:
        """List trades for symbol."""
        raise NotImplementedError


class ExchangePort(ABC):
    """Port for exchange connectivity."""

    @abstractmethod
    def submit_order(self, order: Order) -> dict[str, Any]:
        """Submit order to exchange."""
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel order."""
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions."""
        raise NotImplementedError


class TradingBotProvider(ABC):
    """Port for trading bot management."""

    @abstractmethod
    def start_bot(self, strategy_name: str, symbol: str) -> dict[str, Any]:
        """Start trading bot."""
        raise NotImplementedError

    @abstractmethod
    def stop_bot(self, strategy_name: str, symbol: str) -> dict[str, Any]:
        """Stop trading bot."""
        raise NotImplementedError

    @abstractmethod
    def get_bot_status(self, strategy_name: str, symbol: str) -> dict[str, Any]:
        """Get bot status."""
        raise NotImplementedError