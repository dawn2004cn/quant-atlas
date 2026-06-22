"""Portfolio/Risk Service Ports (abstract interfaces).

Ports define the contracts that the Portfolio/Risk Service exposes.
Adapters implement these ports using the current concrete services.

This follows the Ports and Adapters (Hexagonal Architecture) pattern,
enabling the Portfolio/Risk Service to be extracted as an independent microservice
in Phase 2D.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PortfolioPort(ABC):
    """Port for portfolio operations."""

    @abstractmethod
    def get_portfolio(self, user_id: int) -> dict[str, Any]:
        """Get user portfolio holdings."""
        raise NotImplementedError

    @abstractmethod
    def update_portfolio(self, user_id: int, holdings: list[dict[str, Any]]) -> dict[str, Any]:
        """Update portfolio holdings."""
        raise NotImplementedError


class RiskMetricsPort(ABC):
    """Port for risk metrics operations."""

    @abstractmethod
    def get_risk_metrics(self, user_id: int) -> dict[str, Any]:
        """Get portfolio risk metrics."""
        raise NotImplementedError

    @abstractmethod
    def run_stress_test(self, user_id: int, scenario: str) -> dict[str, Any]:
        """Run portfolio stress test."""
        raise NotImplementedError


class TradePlanPort(ABC):
    """Port for trade plan operations."""

    @abstractmethod
    def submit_trade_plan(self, user_id: int, plan: dict[str, Any]) -> dict[str, Any]:
        """Submit a trade plan for approval."""
        raise NotImplementedError

    @abstractmethod
    def get_trade_plan(self, plan_id: str) -> dict[str, Any]:
        """Get trade plan details."""
        raise NotImplementedError


class SignalObservationPort(ABC):
    """Port for signal observation operations."""

    @abstractmethod
    def record_observation(self, signal_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        """Record signal observation outcome."""
        raise NotImplementedError


class RiskCompanionPort(ABC):
    """Port for risk companion operations."""

    @abstractmethod
    def get_companion(self, user_id: int) -> dict[str, Any]:
        """Get risk companion analysis."""
        raise NotImplementedError
