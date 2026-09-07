from __future__ import annotations

"""Portfolio Optimizer - MVO / Black-Litterman / Risk Budgeting.

This module implements from strategy_plan1.md:
- Mean-Variance Optimization (MVO)
- Black-Litterman model for Bayesian updates
- Risk Budgeting allocation

Usage:
    optimizer = PortfolioOptimizer()
    weights = optimizer.optimize(returns, cov_matrix, target_return=0.15)
"""


from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    weights: dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0


class MeanVarianceOptimizer:
    """Mean-Variance Optimization (MVO) for portfolio construction."""

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        allow_short: bool = False,
    ):
        self._risk_free = risk_free_rate
        self._allow_short = allow_short

    def optimize(
        self,
        expected_returns: dict[str, float],
        cov_matrix: dict[str, dict[str, float]],
        target_return: float | None = None,
        max_volatility: float | None = None,
    ) -> dict[str, float]:
        """Optimize portfolio using MVO."""
        if not expected_returns or not cov_matrix:
            return {}

        tickers = list(expected_returns.keys())
        n = len(tickers)

        exp_ret = np.array([expected_returns[t] for t in tickers])
        cov = np.array([[cov_matrix.get(t1, {}).get(t2, 0) for t1 in tickers] for t2 in tickers])

        try:
            cov_inv = np.linalg.inv(cov + np.eye(n) * 1e-6)
        except np.linalg.LinAlgError:
            cov_inv = np.linalg.pinv(cov)

        ones = np.ones(n)
        numerator = cov_inv @ exp_ret
        denominator = ones @ cov_inv @ ones

        tangency_weights = numerator / denominator

        if target_return is not None:
            A = exp_ret @ cov_inv @ exp_ret
            B = ones @ cov_inv @ exp_ret
            C = ones @ cov_inv @ ones

            lambda_val = (C * target_return - B) / (A * C - B * B)
            mu_val = (A - B * target_return) / (A * C - B * B)

            optimal = lambda_val * cov_inv @ exp_ret + mu_val * cov_inv @ ones
        else:
            optimal = tangency_weights

        optimal = np.maximum(optimal, 0) if not self._allow_short else optimal
        optimal = optimal / np.sum(optimal) if np.sum(optimal) > 0 else optimal

        return {tickers[i]: float(optimal[i]) for i in range(n)}


class BlackLittermanModel:
    """Black-Litterman model for Bayesian portfolio optimization."""

    def __init(
        self,
        market_cap_weights: dict[str, float] | None = None,
        risk_aversion: float = 2.5,
        tau: float = 0.05,
    ):
        self._market_weights = market_cap_weights or {}
        self._risk_aversion = risk_aversion
        self._tau = tau

    def compute_prior(
        self,
        cov_matrix: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """Compute prior expected returns from market equilibrium."""
        tickers = list(cov_matrix.keys())

        if not self._market_weights:
            self._market_weights = {t: 1.0 / len(tickers) for t in tickers}

        market_variance = sum(
            self._market_weights.get(t1, 0) * self._market_weights.get(t2, 0) * cov_matrix.get(t1, {}).get(t2, 0)
            for t1 in tickers
            for t2 in tickers
        ) ** 0.5

        prior = {}
        for ticker in tickers:
            prior[ticker] = self._risk_aversion * market_variance * self._market_weights.get(ticker, 0)

        return prior

    def incorporate_views(
        self,
        views: list[dict[str, Any]],
        cov_matrix: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """Incorporate investor views into prior."""
        tickers = list(cov_matrix.keys())
        prior = self.compute_prior(cov_matrix)

        if not views:
            return prior

        n_views = len(views)
        n_assets = len(tickers)

        P = np.zeros((n_views, n_assets))
        Q = np.zeros(n_views)
        omega = np.zeros((n_views, n_views))

        for i, view in enumerate(views):
            for asset, weight in view.get("assets", {}).items():
                if asset in tickers:
                    P[i, tickers.index(asset)] = weight
            Q[i] = view.get("return", 0)

        cov_array = np.array([[cov_matrix.get(t1, {}).get(t2, 0) for t1 in tickers] for t2 in tickers])

        tau_cov = self._tau * cov_array

        for i in range(n_views):
            P_i = P[i, :].reshape(-1, 1)
            omega[i, i] = float(P_i.T @ tau_cov @ P_i)

        try:
            inv_omega = np.linalg.inv(omega + np.eye(n_views) * 1e-6)
        except np.linalg.LinAlgError:
            inv_omega = np.eye(n_views)

        prior_array = np.array([prior.get(t, 0) for t in tickers])

        posterior_mean = prior_array + tau_cov @ P.T @ inv_omega @ (Q - P @ prior_array)

        posterior = {tickers[i]: float(posterior_mean[i]) for i in range(n_assets)}

        return posterior


class RiskBudgetAllocator:
    """Risk budgeting allocation - equal risk contribution."""

    def __init__(self, max_iterations: int = 100, tolerance: float = 1e-6):
        self._max_iter = max_iterations
        self._tolerance = tolerance

    def allocate(
        self,
        cov_matrix: dict[str, dict[str, float]],
        target_volatility: float | None = None,
    ) -> dict[str, float]:
        """Allocate using risk budgeting approach."""
        tickers = list(cov_matrix.keys())
        n = len(tickers)

        if n == 0:
            return {}

        cov = np.array([[cov_matrix.get(t1, {}).get(t2, 0) for t1 in tickers] for t2 in tickers])

        weights = np.ones(n) / n

        for _ in range(self._max_iter):
            portfolio_vol = float(np.sqrt(weights @ cov @ weights))

            if target_volatility and abs(portfolio_vol - target_volatility) < self._tolerance:
                break

            marginal_risk = (cov @ weights) / portfolio_vol
            risk_contribution = weights * marginal_risk

            target_rc = portfolio_vol / n
            risk_diff = target_rc - risk_contribution

            gradient = risk_contribution + (cov @ risk_diff) / portfolio_vol
            step = 0.5
            weights = np.maximum(weights + step * gradient, 0)
            weights = weights / np.sum(weights)

        return {tickers[i]: float(weights[i]) for i in range(n)}


class PortfolioOptimizer:
    """Complete portfolio optimizer combining all methods."""

    def __init__(
        self,
        mvo: MeanVarianceOptimizer | None = None,
        bl: BlackLittermanModel | None = None,
        risk_budget: RiskBudgetAllocator | None = None,
    ):
        self._mvo = mvo or MeanVarianceOptimizer()
        self._bl = bl or BlackLittermanModel()
        self._risk_budget = risk_budget or RiskBudgetAllocator()

    def compute_correlation_matrix(
        self,
        returns: dict[str, list[float]],
    ) -> dict[str, dict[str, float]]:
        """Compute correlation matrix from returns."""
        tickers = list(returns.keys())
        n = len(tickers)

        if n == 0:
            return {}

        returns_array = {t: np.array(r) for t, r in returns.items()}

        min_len = min(len(r) for r in returns_array.values())
        aligned = np.array([returns_array[t][:min_len] for t in tickers])

        corr = np.corrcoef(aligned)

        result = {}
        for i, t1 in enumerate(tickers):
            result[t1] = {}
            for j, t2 in enumerate(tickers):
                result[t1][t2] = float(corr[i, j])

        return result

    def compute_covariance(
        self,
        returns: dict[str, list[float]],
    ) -> dict[str, dict[str, float]]:
        """Compute covariance matrix from returns."""
        tickers = list(returns.keys())
        n = len(tickers)

        if n == 0:
            return {}

        returns_array = {t: np.array(r) for t, r in returns.items()}

        min_len = min(len(r) for r in returns_array.values())
        aligned = np.array([returns_array[t][:min_len] for t in tickers])

        cov = np.cov(aligned)

        result = {}
        for i, t1 in enumerate(tickers):
            result[t1] = {}
            for j, t2 in enumerate(tickers):
                result[t1][t2] = float(cov[i, j])

        return result

    def optimize_with_correlation(
        self,
        returns: dict[str, list[float]],
        expected_returns: dict[str, float],
        method: str = "mvo",
        target_return: float | None = None,
        correlation_threshold: float = 0.9,
    ) -> dict[str, float]:
        """Optimize with correlation-based risk adjustment."""
        cov = self.compute_covariance(returns)

        corr = self.compute_correlation_matrix(returns)

        high_corr_pairs = []
        tickers = list(corr.keys())
        for i, t1 in enumerate(tickers):
            for j, t2 in enumerate(tickers):
                if i < j and corr.get(t1, {}).get(t2, 0) > correlation_threshold:
                    high_corr_pairs.append((t1, t2))
                    logger.warning(f"High correlation detected: {t1}-{t2}")

        if method == "mvo":
            return self._mvo.optimize(expected_returns, cov, target_return)
        elif method == "risk_budget":
            return self._risk_budget.allocate(cov)
        elif method == "black_litterman":
            posterior_returns = self._bl.incorporate_views([], cov)
            return self._mvo.optimize(posterior_returns, cov, target_return)
        elif method == "hrp":
            from app.domain.quant.hrp import hrp_weights

            return hrp_weights(returns)
        else:
            return {t: 1.0 / len(tickers) for t in tickers}

    def get_portfolio_metrics(
        self,
        weights: dict[str, float],
        expected_returns: dict[str, float],
        cov_matrix: dict[str, dict[str, float]],
    ) -> PortfolioMetrics:
        """Calculate portfolio metrics."""
        tickers = list(weights.keys())
        w = np.array([weights.get(t, 0) for t in tickers])
        exp_ret = np.array([expected_returns.get(t, 0) for t in tickers])

        port_return = float(w @ exp_ret)

        cov_arr = np.array([[cov_matrix.get(t1, {}).get(t2, 0) for t1 in tickers] for t2 in tickers])
        port_vol = float(np.sqrt(w @ cov_arr @ w))

        sharpe = (port_return - 0.02) / port_vol if port_vol > 0 else 0

        return PortfolioMetrics(
            weights=weights,
            expected_return=port_return,
            volatility=port_vol,
            sharpe_ratio=sharpe,
        )


_global_optimizer: PortfolioOptimizer | None = None


def get_portfolio_optimizer() -> PortfolioOptimizer:
    """Get singleton portfolio optimizer."""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PortfolioOptimizer()
    return _global_optimizer
