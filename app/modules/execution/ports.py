"""Execution Service Ports (abstract interfaces).

Ports define the contracts that the Execution Service exposes.
Adapters implement these ports using the current concrete services.

This follows the Ports and Adapters (Hexagonal Architecture) pattern,
enabling the Execution Service to be extracted as an independent microservice
in Phase 2E.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TradeExecutionPort(ABC):
    """Port for trade execution operations."""

    @abstractmethod
    def execute_trade(self, order: dict[str, Any]) -> dict[str, Any]:
        """Execute a trade order."""
        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get order execution status."""
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel a pending order."""
        raise NotImplementedError

    @abstractmethod
    def get_execution_history(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get execution history."""
        raise NotImplementedError


class SimulationPort(ABC):
    """Port for simulation operations."""

    @abstractmethod
    def run_simulation(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run trading simulation."""
        raise NotImplementedError


class SelfHealingPort(ABC):
    """Port for self-healing execution operations."""

    @abstractmethod
    def heal_execution(self, order_id: str) -> dict[str, Any]:
        """Attempt to heal a failed execution."""
        raise NotImplementedError

    @abstractmethod
    def get_healing_status(self, order_id: str) -> dict[str, Any]:
        """Get healing status for an order."""
        raise NotImplementedError
