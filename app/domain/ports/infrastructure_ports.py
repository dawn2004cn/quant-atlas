from __future__ import annotations
"""Infrastructure ports - interfaces for dependency inversion.

These interfaces define contracts that infrastructure components must implement.
"""


from abc import ABC, abstractmethod
from typing import Any


class IExperimentRepository(ABC):
    """Contract for experiment persistence."""

    @abstractmethod
    def save_experiment(self, experiment_data: dict) -> dict:
        pass

    @abstractmethod
    def get_experiment(self, experiment_id: str) -> dict | None:
        pass

    @abstractmethod
    def list_experiments(self, limit: int = 100) -> list[dict]:
        pass

    @abstractmethod
    def update_experiment(self, experiment_id: str, data: dict) -> dict:
        pass


class IMessageStore(ABC):
    """Contract for message storage."""

    @abstractmethod
    def save(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def get(self, key: str) -> Any | None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def list_keys(self, pattern: str = "*") -> list[str]:
        pass


class IMarketDataProvider(ABC):
    """Contract for market data providers."""

    @abstractmethod
    def get_quote(self, symbol: str) -> dict:
        pass

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> list[dict]:
        pass

    @abstractmethod
    def get_realtime(self, symbols: list[str]) -> list[dict]:
        pass


class IIngestorAdapter(ABC):
    """Contract for data ingestion."""

    @abstractmethod
    def ingest(self, data: dict) -> int:
        pass

    @abstractmethod
    def validate(self, data: dict) -> bool:
        pass


class IDataMapper(ABC):
    """Contract for data mapping."""

    @abstractmethod
    def to_domain(self, data: dict) -> dict:
        pass

    @abstractmethod
    def to_external(self, data: dict) -> dict:
        pass


class IAnalyticsEngine(ABC):
    """Contract for analytics engines."""

    @abstractmethod
    def analyze(self, data: dict) -> dict:
        pass

    @abstractmethod
    def generate_report(self, result: dict) -> str:
        pass


class IKnowledgeStore(ABC):
    """Contract for knowledge/embedding store."""

    @abstractmethod
    def save(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def get(self, key: str) -> Any | None:
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict]:
        pass


__all__ = [
    "IExperimentRepository",
    "IMessageStore",
    "IMarketDataProvider",
    "IIngestorAdapter",
    "IDataMapper",
    "IAnalyticsEngine",
    "IKnowledgeStore",
]
