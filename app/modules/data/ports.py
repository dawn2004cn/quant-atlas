"""Data Service Ports (abstract interfaces).

Ports define the contracts that the Data Service exposes.
Adapters implement these ports using the current concrete services.

This follows the Ports and Adapters (Hexagonal Architecture) pattern,
enabling the Data Service to be extracted as an independent microservice
in Phase 2G.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DataInfrastructurePort(ABC):
    """Port for data infrastructure operations."""

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Get data infrastructure status."""
        raise NotImplementedError


class DataLakePort(ABC):
    """Port for data lake operations."""

    @abstractmethod
    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        """Query data lake."""
        raise NotImplementedError


class DataOptimizerPort(ABC):
    """Port for data optimizer operations."""

    @abstractmethod
    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run data optimizer."""
        raise NotImplementedError


class DataQualityPort(ABC):
    """Port for data quality operations."""

    @abstractmethod
    def verify(self, source: str) -> dict[str, Any]:
        """Verify data quality."""
        raise NotImplementedError


class HistoricalResonancePort(ABC):
    """Port for historical resonance operations."""

    @abstractmethod
    def get_resonance(self, symbol: str) -> dict[str, Any]:
        """Get historical resonance data."""
        raise NotImplementedError


class MemoryOptimizationPort(ABC):
    """Port for memory optimization operations."""

    @abstractmethod
    def get_optimization(self) -> dict[str, Any]:
        """Get memory optimization status."""
        raise NotImplementedError


class PyTdxPort(ABC):
    """Port for pytdx operations."""

    @abstractmethod
    def query(self, params: dict[str, Any]) -> dict[str, Any]:
        """Query via pytdx."""
        raise NotImplementedError


class QlibPort(ABC):
    """Port for Qlib operations."""

    @abstractmethod
    def get_research_data(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get Qlib research data."""
        raise NotImplementedError


class TaskPipelinePort(ABC):
    """Port for task pipeline operations."""

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Get task pipeline status."""
        raise NotImplementedError


class TruthBadgePort(ABC):
    """Port for truth badge operations."""

    @abstractmethod
    def get_badge(self, market: str, symbol: str) -> dict[str, Any]:
        """Get truth badge for a symbol."""
        raise NotImplementedError
