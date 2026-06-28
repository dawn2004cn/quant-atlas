from __future__ import annotations

"""Qlib experiment task service port - rd-agent to qlib automation pipeline."""


from abc import ABC, abstractmethod
from typing import Any


class QlibExperimentResult:
    """Result from a qlib experiment run."""

    def __init__(
        self,
        experiment_id: str,
        status: str,
        formula: str,
        backtest_result: dict[str, Any] | None = None,
        model_result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        self.experiment_id = experiment_id
        self.status = status
        self.formula = formula
        self.backtest_result = backtest_result or {}
        self.model_result = model_result or {}
        self.error = error

    @property
    def is_success(self) -> bool:
        return self.status == "completed" and self.error is None

    @property
    def sharpe_ratio(self) -> float:
        return self.backtest_result.get("sharpe_ratio", 0.0)

    @property
    def max_drawdown(self) -> float:
        return self.backtest_result.get("max_drawdown", 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "status": self.status,
            "formula": self.formula,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "backtest_result": self.backtest_result,
            "model_result": self.model_result,
            "error": self.error,
        }


class QlibTaskService(ABC):
    """Port for submitting qlib experiments from rd-agent.

    This is the core interface for the "Alpha Factory" architecture:
    - rd-agent generates factor expressions
    - This service runs them through qlib pipeline
    - Returns backtest + model results for evaluation
    """

    @abstractmethod
    def submit_experiment(
        self,
        formula: str,
        *,
        data_scope: dict[str, Any] | None = None,
        model_config: dict[str, Any] | None = None,
        backtest_config: dict[str, Any] | None = None,
    ) -> str:
        """Submit a single factor expression to qlib pipeline.

        Args:
            formula: Alpha factor expression (e.g., "rank(Ts_ArgMax(SUMS(returns_0_1, 20))")
            data_scope: Data scope config (market, start_date, end_date)
            model_config: Model training config (model_type, train_window, etc)
            backtest_config: Backtest config (risk_free, benchmark, etc)

        Returns:
            experiment_id: Unique identifier for tracking
        """
        raise NotImplementedError

    def submit_formula_set(
        self,
        formulas: list[str],
        *,
        data_scope: dict[str, Any] | None = None,
    ) -> list[str]:
        """Submit multiple formulas for batch experiment.

        Args:
            formulas: List of factor expressions
            data_scope: Shared data scope for all formulas

        Returns:
            List of experiment_ids
        """
        exp_ids = []
        for formula in formulas:
            exp_id = self.submit_experiment(
                formula,
                data_scope=data_scope,
            )
            exp_ids.append(exp_id)
        return exp_ids

    @abstractmethod
    def get_experiment_result(self, experiment_id: str) -> QlibExperimentResult:
        """Get result of a completed experiment."""
        raise NotImplementedError

    @abstractmethod
    def cancel_experiment(self, experiment_id: str) -> bool:
        """Cancel a running experiment."""
        raise NotImplementedError

    @abstractmethod
    def list_experiments(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List recent experiments."""
        raise NotImplementedError
