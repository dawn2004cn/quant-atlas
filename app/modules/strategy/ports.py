"""Strategy Service Ports (abstract interfaces).

Ports define the contracts that the Strategy Service exposes.
Adapters implement these ports using the current concrete services.

This follows the Ports and Adapters (Hexagonal Architecture) pattern,
enabling the Strategy Service to be extracted as an independent microservice
in Phase 2B.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RecommendationPort(ABC):
    """Port for stock recommendation operations."""

    @abstractmethod
    def daily_top(self, market: str, top_n: int, account_equity: float) -> list[dict[str, Any]]:
        """Get daily top stock recommendations."""
        raise NotImplementedError


class StrategyOptimizationPort(ABC):
    """Port for strategy optimization operations."""

    @abstractmethod
    def run_walk_forward(
        self,
        symbol: str,
        param_space: dict[str, Any],
        start_date: str,
        end_date: str,
        objective: str,
        train_window_days: int,
        test_window_days: int,
        n_windows: int,
    ) -> dict[str, Any]:
        """Run walk-forward parameter optimization."""
        raise NotImplementedError


class StrategySnapshotPort(ABC):
    """Port for strategy snapshot operations."""

    @abstractmethod
    def get_snapshot(self, strategy_id: str) -> dict[str, Any]:
        """Get strategy performance snapshot."""
        raise NotImplementedError


class StrategyCopilotPort(ABC):
    """Port for strategy copilot operations."""

    @abstractmethod
    def analyze_strategy(self, strategy_id: str, query: str) -> dict[str, Any]:
        """Analyze strategy with natural language query."""
        raise NotImplementedError


class SignalObservationPort(ABC):
    """Port for signal observation operations."""

    @abstractmethod
    def record_observation(self, signal_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        """Record signal observation outcome."""
        raise NotImplementedError

    @abstractmethod
    def get_observations(self, signal_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get signal observation history."""
        raise NotImplementedError


class SignalFlagPort(ABC):
    """Port for signal flag operations."""

    @abstractmethod
    def scan_flags(self, symbols: list[str], strategy_id: str) -> dict[str, Any]:
        """Scan for signal flags on given symbols."""
        raise NotImplementedError


class AttributionPort(ABC):
    """Port for strategy attribution operations."""

    @abstractmethod
    def get_attribution(self, strategy_id: str, period: str) -> dict[str, Any]:
        """Get strategy attribution analysis."""
        raise NotImplementedError


class ReviewPort(ABC):
    """Port for strategy review operations."""

    @abstractmethod
    def submit_review(self, strategy_id: str, review_data: dict[str, Any]) -> dict[str, Any]:
        """Submit strategy review/correction."""
        raise NotImplementedError

    @abstractmethod
    def get_reviews(self, strategy_id: str) -> list[dict[str, Any]]:
        """Get strategy review history."""
        raise NotImplementedError


class BriefingPort(ABC):
    """Port for daily briefing operations."""

    @abstractmethod
    def get_briefing(self, user_id: int) -> dict[str, Any]:
        """Get daily strategy briefing."""
        raise NotImplementedError


class StrategySynthesisPort(ABC):
    """Port for strategy synthesis operations."""

    @abstractmethod
    def synthesize(self, market_regime: str, constraints: dict[str, Any]) -> dict[str, Any]:
        """Synthesize a new strategy based on market regime."""
        raise NotImplementedError


class FactorPort(ABC):
    """Port for factor operations."""

    @abstractmethod
    def list_factors(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available factors."""
        raise NotImplementedError

    @abstractmethod
    def get_factor(self, factor_id: str) -> dict[str, Any]:
        """Get factor details and performance."""
        raise NotImplementedError
