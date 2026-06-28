from __future__ import annotations
"""Walk-forward optimization for strategy parameter tuning."""


from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ...domain.ports.strategy_ports import (
    WalkForwardOptimizerPort,
    WalkForwardWindow,
    WalkForwardResult,
)


@dataclass
class OptimizationResult:
    """Result of parameter optimization on a dataset."""
    params: dict[str, float]
    score: float
    metrics: dict[str, float] = field(default_factory=dict)


class DefaultWalkForwardOptimizer(WalkForwardOptimizerPort):
    """Default implementation of walk-forward optimization."""

    def __init__(self, risk_free_rate: float = 0.03):
        self._rf = risk_free_rate

    def optimize(
        self,
        data: list[dict],
        param_space: dict[str, list[float]],
        objective: str = "sharpe_ratio",
        train_window_days: int = 252,
        test_window_days: int = 63,
        n_windows: int = 5,
    ) -> WalkForwardResult:
        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
        elif "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)

        if df.empty or len(df) < train_window_days + test_window_days:
            return WalkForwardResult(
                optimal_params={},
                windows=[],
                avg_train_return=0,
                avg_test_return=0,
                in_sample_score=0,
                out_sample_score=0,
                stability_score=0,
                conclusion="Insufficient data for walk-forward analysis",
            )

        windows = []
        train_end_idx = train_window_days
        test_end_idx = train_end_idx + test_window_days
        data_end_idx = len(df)

        for i in range(n_windows):
            train_data = df.iloc[:train_end_idx]
            test_data = df.iloc[train_end_idx:test_end_idx]

            if len(train_data) < 60 or len(test_data) < 20:
                break

            best_result = self._grid_search(train_data, param_space, objective)

            test_metrics = self._evaluate(test_data, best_result.params, objective)

            windows.append(WalkForwardWindow(
                train_start=train_data.index[0].strftime("%Y-%m-%d"),
                train_end=train_data.index[-1].strftime("%Y-%m-%d"),
                test_start=test_data.index[0].strftime("%Y-%m-%d"),
                test_end=test_data.index[-1].strftime("%Y-%m-%d"),
                train_return=best_result.metrics.get("total_return", 0),
                test_return=test_metrics.get("total_return", 0),
                params=best_result.params,
            ))

            train_end_idx = test_end_idx
            test_end_idx = test_end_idx + test_window_days
            if test_end_idx > data_end_idx:
                break

        if not windows:
            return WalkForwardResult(
                optimal_params={},
                windows=[],
                avg_train_return=0,
                avg_test_return=0,
                in_sample_score=0,
                out_sample_score=0,
                stability_score=0,
                conclusion="No valid windows generated",
            )

        optimal_params = windows[-1].params

        train_returns = [w.train_return for w in windows]
        test_returns = [w.test_return for w in windows]
        avg_train = float(np.mean(train_returns)) if train_returns else 0
        avg_test = float(np.mean(test_returns)) if test_returns else 0

        test_std = float(np.std(test_returns)) if len(test_returns) > 1 else 0
        stability = 1.0 - min(test_std / (abs(avg_test) + 0.001), 1.0) if avg_test != 0 else 0

        in_sample = avg_train
        out_sample = avg_test

        if out_sample > 0 and in_sample > 0:
            conclusion = f"Strategy shows positive out-of-sample performance. In-sample: {in_sample:.2%}, Out-of-sample: {out_sample:.2%}"
        elif out_sample < 0 and in_sample > 0:
            conclusion = f"Potential overfitting detected. In-sample: {in_sample:.2%}, Out-of-sample: {out_sample:.2%}"
        else:
            conclusion = f"Strategy underperforms in both train and test. In-sample: {in_sample:.2%}, Out-of-sample: {out_sample:.2%}"

        return WalkForwardResult(
            optimal_params=optimal_params,
            windows=windows,
            avg_train_return=avg_train,
            avg_test_return=avg_test,
            in_sample_score=in_sample,
            out_sample_score=out_sample,
            stability_score=stability,
            conclusion=conclusion,
        )

    def _grid_search(
        self,
        data: pd.DataFrame,
        param_space: dict[str, list[float]],
        objective: str,
    ) -> OptimizationResult:
        best_score = -float("inf")
        best_params = {}
        best_metrics = {}

        keys = list(param_space.keys())
        values = list(param_space.values())

        import itertools
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            metrics = self._evaluate(data, params, objective)
            score = metrics.get(objective, -999)

            if score > best_score:
                best_score = score
                best_params = params
                best_metrics = metrics

        return OptimizationResult(params=best_params, score=best_score, metrics=best_metrics)

    def _evaluate(
        self,
        data: pd.DataFrame,
        params: dict[str, float],
        objective: str,
    ) -> dict[str, float]:
        prices = data["Close"] if "Close" in data.columns else data.iloc[:, 0]

        period = int(params.get("period", 20))
        params.get("threshold", 0.02)

        if len(prices) < period + 1:
            return {"sharpe_ratio": -999, "total_return": -1}

        returns = prices.pct_change().dropna()

        if len(returns) < 2:
            return {"sharpe_ratio": -999, "total_return": -1}

        total_return = (prices.iloc[-1] / prices.iloc[0]) - 1

        mean_return = returns.mean() * 252
        std_return = returns.std() * np.sqrt(252)
        sharpe = (mean_return - self._rf) / std_return if std_return > 0 else 0

        mdd = self._compute_max_drawdown(prices)

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": mdd,
            "volatility": std_return,
            "mean_return": mean_return,
        }

    def _compute_max_drawdown(self, prices: pd.Series) -> float:
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        return drawdown.min()
