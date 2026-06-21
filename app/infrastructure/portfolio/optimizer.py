from __future__ import annotations
"""Portfolio optimization implementations."""


import logging
import numpy as np
from typing import Any

from ...domain.ports.portfolio_ports import (
    PortfolioAsset,
    PortfolioOptimizerPort,
    AttributionAnalysisPort,
    OptimizationResult,
    EfficientFrontier,
)
from ...core.logger import get_logger



logger = get_logger(__name__)


class MarkowitzOptimizer(PortfolioOptimizerPort):
    """Markowitz Mean-Variance Portfolio Optimizer."""

    def __init__(self, risk_free_rate: float = 0.03) -> None:
        self._rf = risk_free_rate

    def optimize(
        self,
        assets: list[PortfolioAsset],
        *,
        method: str = "markowitz",
        target_return: float | None = None,
        risk_aversion: float = 1.0,
    ) -> OptimizationResult:
        if len(assets) < 2:
            return self._single_asset_result(assets)

        symbols = [a.symbol for a in assets]
        returns = np.array([a.expected_return for a in assets])
        volatilities = np.array([a.volatility for a in assets])

        cov_matrix = self._build_cov_matrix(volatilities)

        try:
            weights = self._solve_mv(
                returns, cov_matrix, target_return=target_return, risk_aversion=risk_aversion
            )
        except Exception as e:
            logger.warning("Markowitz optimization failed: %s, using equal weight", e)
            weights = np.ones(len(assets)) / len(assets)

        port_return = np.dot(weights, returns)
        port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        sharpe = (port_return - self._rf) / port_vol if port_vol > 0 else 0

        return OptimizationResult(
            optimal_weights=dict(zip(symbols, [round(w, 4) for w in weights])),
            expected_return=round(port_return, 4),
            volatility=round(port_vol, 4),
            sharpe_ratio=round(sharpe, 4),
            method=method,
        )

    def compute_frontier(
        self,
        assets: list[PortfolioAsset],
        *,
        n_points: int = 50,
    ) -> list[EfficientFrontier]:
        if len(assets) < 2:
            return []

        symbols = [a.symbol for a in assets]
        returns = np.array([a.expected_return for a in assets])
        volatilities = np.array([a.volatility for a in assets])
        cov_matrix = self._build_cov_matrix(volatilities)

        min_return = returns.min()
        max_return = returns.max()
        target_returns = np.linspace(min_return, max_return, n_points)

        frontier = []
        for target in target_returns:
            try:
                weights = self._solve_mv(returns, cov_matrix, target_return=target)
                port_ret = np.dot(weights, returns)
                port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
                sharpe = (port_ret - self._rf) / port_vol if port_vol > 0 else 0

                frontier.append(
                    EfficientFrontier(
                        expected_return=round(port_ret, 4),
                        volatility=round(port_vol, 4),
                        sharpe_ratio=round(sharpe, 4),
                        weights=dict(zip(symbols, [round(w, 4) for w in weights])),
                    )
                )
            except Exception:
                continue

        return frontier

    def _single_asset_result(self, assets: list[PortfolioAsset]) -> OptimizationResult:
        if not assets:
            return OptimizationResult(
                optimal_weights={},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                method="single",
            )
        a = assets[0]
        return OptimizationResult(
            optimal_weights={a.symbol: 1.0},
            expected_return=a.expected_return,
            volatility=a.volatility,
            sharpe_ratio=(a.expected_return - self._rf) / a.volatility if a.volatility > 0 else 0,
            method="single",
        )

    def _build_cov_matrix(self, volatilities: np.ndarray) -> np.ndarray:
        n = len(volatilities)
        cov = np.outer(volatilities, volatilities)
        np.fill_diagonal(cov, volatilities ** 2)
        return cov

    def _solve_mv(
        self,
        returns: np.ndarray,
        cov: np.ndarray,
        target_return: float | None = None,
        risk_aversion: float = 1.0,
    ) -> np.ndarray:
        n = len(returns)

        if target_return is not None:
            A = np.ones((n, 1))
            A = np.vstack([returns, A, np.eye(n)])
            b = np.array([target_return, 1.0] + [0] * n)
            constraints = np.linalg.lstsq(A, b, rcond=None)[0]
            weights = np.maximum(constraints[:n], 0)
            total = weights.sum()
            if total > 0:
                weights /= total
            return weights
        else:
            ones = np.ones(n)
            cov_inv = np.linalg.pinv(cov)
            icl = np.dot(cov_inv, returns - risk_aversion * np.dot(cov, ones))
            weights = icl / icl.sum()
            weights = np.maximum(weights, 0)
            return weights


class BlackLittermanOptimizer(PortfolioOptimizerPort):
    """Black-Litterman Portfolio Optimizer with analyst views."""

    def __init__(self, risk_free_rate: float = 0.03, tau: float = 0.05) -> None:
        self._rf = risk_free_rate
        self._tau = tau

    def optimize(
        self,
        assets: list[PortfolioAsset],
        *,
        method: str = "black_litterman",
        target_return: float | None = None,
        risk_aversion: float = 1.0,
        views: dict[str, float] | None = None,
    ) -> OptimizationResult:
        if len(assets) < 2:
            return self._single_asset_result(assets)

        symbols = [a.symbol for a in assets]
        returns = np.array([a.expected_return for a in assets])
        volatilities = np.array([a.volatility for a in assets])

        cov_matrix = self._build_cov_matrix(volatilities)

        posterior_returns = returns.copy()
        if views:
            for symbol, view_return in views.items():
                if symbol in symbols:
                    idx = symbols.index(symbol)
                    posterior_returns[idx] = 0.5 * returns[idx] + 0.5 * view_return

        try:
            weights = self._solve_mv(posterior_returns, cov_matrix, target_return, risk_aversion)
        except Exception as e:
            logger.warning("BL optimization failed: %s", e)
            weights = np.ones(len(assets)) / len(assets)

        port_return = np.dot(weights, posterior_returns)
        port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        sharpe = (port_return - self._rf) / port_vol if port_vol > 0 else 0

        return OptimizationResult(
            optimal_weights=dict(zip(symbols, [round(w, 4) for w in weights])),
            expected_return=round(port_return, 4),
            volatility=round(port_vol, 4),
            sharpe_ratio=round(sharpe, 4),
            method=method,
        )

    def compute_frontier(
        self,
        assets: list[PortfolioAsset],
        *,
        n_points: int = 50,
    ) -> list[EfficientFrontier]:
        return MarkowitzOptimizer(risk_free_rate=self._rf).compute_frontier(assets, n_points=n_points)

    def _single_asset_result(self, assets: list[PortfolioAsset]) -> OptimizationResult:
        if not assets:
            return OptimizationResult(
                optimal_weights={},
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                method="black_litterman",
            )
        a = assets[0]
        return OptimizationResult(
            optimal_weights={a.symbol: 1.0},
            expected_return=a.expected_return,
            volatility=a.volatility,
            sharpe_ratio=(a.expected_return - self._rf) / a.volatility if a.volatility > 0 else 0,
            method="black_litterman",
        )

    def _build_cov_matrix(self, volatilities: np.ndarray) -> np.ndarray:
        n = len(volatilities)
        cov = np.outer(volatilities, volatilities)
        np.fill_diagonal(cov, volatilities ** 2)
        return cov

    def _solve_mv(
        self,
        returns: np.ndarray,
        cov: np.ndarray,
        target_return: float | None,
        risk_aversion: float,
    ) -> np.ndarray:
        n = len(returns)

        if target_return is not None:
            A = np.ones((n, 1))
            A = np.vstack([returns, A, np.eye(n)])
            b = np.array([target_return, 1.0] + [0] * n)
            constraints = np.linalg.lstsq(A, b, rcond=None)[0]
            weights = np.maximum(constraints[:n], 0)
            total = weights.sum()
            if total > 0:
                weights /= total
            return weights
        else:
            ones = np.ones(n)
            cov_inv = np.linalg.pinv(cov)
            icl = np.dot(cov_inv, returns - risk_aversion * np.dot(cov, ones))
            weights = icl / icl.sum()
            weights = np.maximum(weights, 0)
            return weights


class DefaultAttributionAnalysis(AttributionAnalysisPort):
    """Default attribution analysis implementation."""

    def decompose(
        self,
        portfolio_return: float,
        benchmark_return: float,
        factor_exposures: dict[str, float],
        factor_returns: dict[str, float],
        alpha: float,
    ) -> dict[str, float]:
        beta = portfolio_return - benchmark_return - alpha
        style_return = sum(
            factor_exposures.get(f, 0) * factor_returns.get(f, 0)
            for f in set(factor_exposures) | set(factor_returns)
        )
        residual = portfolio_return - alpha - beta - style_return

        return {
            "alpha": round(alpha, 4),
            "beta_timing": round(beta, 4),
            "style_selection": round(style_return, 4),
            "total_return": round(portfolio_return, 4),
            "residual": round(residual, 4),
            "interpretation": self._interpret(beta, alpha, style_return),
        }

    def _interpret(self, beta: float, alpha: float, style: float) -> str:
        parts = []
        if abs(beta) > 0.1:
            parts.append("择时" + ("强" if beta > 0 else "弱"))
        if abs(alpha) > 0.02:
            parts.append("选股" + ("强" if alpha > 0 else "弱"))
        if abs(style) > 0.02:
            parts.append("风格暴露显著")
        return "，".join(parts) if parts else "收益主要来自基准暴露"