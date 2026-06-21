from __future__ import annotations
"""Portfolio management ports."""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PortfolioAsset:
    """A single asset in a portfolio."""
    symbol: str
    current_weight: float = 0.0
    target_weight: float = 0.0
    expected_return: float = 0.0
    volatility: float = 0.0
    shares: int = 0
    price: float = 0.0


@dataclass(frozen=True)
class EfficientFrontier:
    """Efficient frontier point."""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: dict[str, float]


@dataclass(frozen=True)
class OptimizationResult:
    """Result of portfolio optimization."""
    optimal_weights: dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    method: str
    frontier: list[EfficientFrontier] = field(default_factory=list)


class PortfolioOptimizerPort(ABC):
    """Port for portfolio optimization (Markowitz, Black-Litterman, etc.)."""

    @abstractmethod
    def optimize(
        self,
        assets: list[PortfolioAsset],
        *,
        method: str = "markowitz",
        target_return: float | None = None,
        risk_aversion: float = 1.0,
    ) -> OptimizationResult:
        """Run portfolio optimization."""
        raise NotImplementedError

    @abstractmethod
    def compute_frontier(
        self,
        assets: list[PortfolioAsset],
        *,
        n_points: int = 50,
    ) -> list[EfficientFrontier]:
        """Compute efficient frontier."""
        raise NotImplementedError


class AttributionAnalysisPort(ABC):
    """Port for portfolio attribution analysis."""

    @abstractmethod
    def decompose(
        self,
        portfolio_return: float,
        benchmark_return: float,
        factor_exposures: dict[str, float],
        factor_returns: dict[str, float],
        alpha: float,
    ) -> dict[str, float]:
        """Decompose portfolio return into Beta, Alpha, Style factors."""
        raise NotImplementedError