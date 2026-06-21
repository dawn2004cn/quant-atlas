from __future__ import annotations
"""Strategy optimization ports."""


from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class WalkForwardWindow:
    """A single walk-forward window."""
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_return: float
    test_return: float
    params: dict[str, float]


@dataclass
class WalkForwardResult:
    """Result of walk-forward optimization."""
    optimal_params: dict[str, float]
    windows: list[WalkForwardWindow]
    avg_train_return: float
    avg_test_return: float
    in_sample_score: float
    out_sample_score: float
    stability_score: float
    conclusion: str


class WalkForwardOptimizerPort(ABC):
    """Port for walk-forward parameter optimization."""

    @abstractmethod
    def optimize(
        self,
        data: list[dict],
        param_space: dict[str, list[float]],
        objective: str = "sharpe_ratio",
        train_window_days: int = 252,
        test_window_days: int = 63,
        n_windows: int = 5,
    ) -> WalkForwardResult:
        """Run walk-forward optimization."""
        raise NotImplementedError