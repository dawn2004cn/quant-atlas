from __future__ import annotations
"""Factory ports for strategy and exchange instantiation."""


from abc import ABC, abstractmethod
from typing import Any

from ..entities import StrategyConfig


class StrategyFactoryPort(ABC):
    """Port for strategy instantiation."""

    @abstractmethod
    def create(self, config: StrategyConfig) -> Any:
        """Create strategy instance from config."""
        raise NotImplementedError

    @abstractmethod
    def get_registered_ids(self) -> list[str]:
        """List registered strategy IDs."""
        raise NotImplementedError


class ExchangeFactoryPort(ABC):
    """Port for exchange instantiation."""

    @abstractmethod
    def create_exchange(self, exchange_id: str) -> Any:
        """Create exchange instance by ID."""
        raise NotImplementedError
