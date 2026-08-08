from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Factor orthogonalization service for multi-factor strategies."""


import numpy as np
import pandas as pd
from typing import Any

from app.core.registry import register_service


@register_service(name="factor_orthogonalization_service")
class FactorOrthogonalizationService:
    """Service for orthogonalizing (neutralizing) factors."""

    def orthogonalize(
        self,
        factors_df: pd.DataFrame,
        target_column: str,
        neutralize_columns: list[str] | None = None,
        market_column: str | None = None,
    ) -> pd.DataFrame:
        """
        Orthogonalize target factor against other factors or market.

        Args:
            factors_df: DataFrame with factor columns
            target_column: Column to orthogonalize
            neutralize_columns: Columns to orthogonalize against
            market_column: Optional market benchmark column

        Returns:
            DataFrame with orthogonalized target column (named {target_column}_ortho)
        """
        if target_column not in factors_df.columns:
            raise ValueError(f"Target column {target_column} not found")

        result = factors_df.copy()

        cols_to_neutralize = []
        if neutralize_columns:
            cols_to_neutralize = [c for c in neutralize_columns if c in factors_df.columns]

        if market_column and market_column in factors_df.columns:
            cols_to_neutralize.append(market_column)

        if not cols_to_neutralize:
            result[f"{target_column}_ortho"] = result[target_column]
            return result

        y = result[target_column].values
        X = result[cols_to_neutralize].values

        valid_mask = ~(np.isnan(y) | np.any(np.isnan(X), axis=1))
        y_valid = y[valid_mask]
        X_valid = X[valid_mask]

        try:
            coeffs, _, _, _ = np.linalg.lstsq(X_valid, y_valid, rcond=None)

            residuals = y_valid - X_valid @ coeffs

            result.loc[valid_mask, f"{target_column}_ortho"] = residuals
            result.loc[~valid_mask, f"{target_column}_ortho"] = np.nan

        except np.linalg.LinAlgError:
            result[f"{target_column}_ortho"] = result[target_column]

        return result

    def neutralize_portfolio_exposure(
        self,
        returns: pd.Series,
        factor_returns: pd.DataFrame,
    ) -> pd.Series:
        """
        Neutralize portfolio returns against factor exposures.

        Args:
            returns: Portfolio returns series
            factor_returns: DataFrame of factor returns

        Returns:
            Factor-neutral (alpha) returns
        """
        valid_mask = ~(returns.isna() | factor_returns.isna().any(axis=1))

        y = returns[valid_mask].values
        X = factor_returns.loc[valid_mask].values

        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            alpha = y - X @ coeffs

            result = pd.Series(index=returns.index, dtype=float)
            result[valid_mask] = alpha
            result[~valid_mask] = np.nan

            return result
        except np.linalg.LinAlgError:
            return returns

    def compute_factor_correlation_matrix(
        self,
        factors_df: pd.DataFrame,
        factor_columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Compute correlation matrix between factors."""
        if factor_columns is None:
            factor_columns = [c for c in factors_df.columns if c not in ["date", "symbol"]]

        available_cols = [c for c in factor_columns if c in factors_df.columns]

        if not available_cols:
            return pd.DataFrame()

        return factors_df[available_cols].corr()


@register_service(name="factor_self_correction_service")
class FactorSelfCorrectionService:
    """Service for self-correction of failed factors."""

    def __init__(self):
        self._factor_performance_history: dict[str, list[dict]] = {}

    def record_factor_performance(
        self,
        factor_name: str,
        period: str,
        ic: float,
        icir: float,
        return_pct: float,
    ) -> None:
        """Record factor performance for analysis."""
        if factor_name not in self._factor_performance_history:
            self._factor_performance_history[factor_name] = []

        self._factor_performance_history[factor_name].append({
            "period": period,
            "ic": ic,
            "icir": icir,
            "return_pct": return_pct,
        })

    def analyze_factor_degradation(
        self,
        factor_name: str,
        lookback_periods: int = 5,
    ) -> GenericResponseDTO:
        """Analyze if a factor has degraded over time."""
        history = self._factor_performance_history.get(factor_name, [])

        if len(history) < lookback_periods:
            return {
                "factor_name": factor_name,
                "status": "insufficient_data",
                "degradation_detected": False,
            }

        recent = history[-lookback_periods:]
        older = history[:-lookback_periods]

        if not older:
            return {
                "factor_name": factor_name,
                "status": "insufficient_baseline",
                "degradation_detected": False,
            }

        recent_ic = np.mean([h["ic"] for h in recent])
        older_ic = np.mean([h["ic"] for h in older])

        recent_return = np.mean([h["return_pct"] for h in recent])
        older_return = np.mean([h["return_pct"] for h in older])

        ic_degradation = older_ic - recent_ic
        return_degradation = older_return - recent_return

        degradation_threshold = 0.1

        degradation_detected = (
            ic_degradation > degradation_threshold or
            return_degradation > degradation_threshold
        )

        status = "healthy"
        recommendation = "Continue using factor"

        if degradation_detected:
            if ic_degradation > 0.2:
                status = "critical"
                recommendation = "Disable factor immediately - IC degraded significantly"
            else:
                status = "warning"
                recommendation = "Consider reducing factor weight or reviewing parameters"

        return {
            "factor_name": factor_name,
            "status": status,
            "degradation_detected": degradation_detected,
            "ic_degradation": ic_degradation,
            "return_degradation": return_degradation,
            "recent_ic": recent_ic,
            "older_ic": older_ic,
            "recommendation": recommendation,
        }

    def generate_prompt_improvement(
        self,
        factor_name: str,
        degradation_analysis: dict[str, Any],
    ) -> str:
        """Generate prompt improvement suggestions based on factor failure."""
        if not degradation_analysis.get("degradation_detected"):
            return f"Factor {factor_name} is performing well. No prompt changes needed."

        suggestions = [
            f"Factor {factor_name} has shown degradation.",
            f"IC degraded by {degradation_analysis.get('ic_degradation', 0):.2%}.",
            f"Return degraded by {degradation_analysis.get('return_degradation', 0):.2%}.",
        ]

        status = degradation_analysis.get("status", "unknown")
        if status == "critical":
            suggestions.append("Consider removing this factor from the ensemble.")
            suggestions.append("Try alternative factor definitions in the same category.")
        elif status == "warning":
            suggestions.append("Try adjusting the lookback period for this factor.")
            suggestions.append("Consider adding a confirmation filter.")

        return " ".join(suggestions)

    def get_all_factors_status(self) -> list[dict[str, Any]]:
        """Get status of all tracked factors."""
        results = []
        for factor_name in self._factor_performance_history.keys():
            analysis = self.analyze_factor_degradation(factor_name)
            results.append(analysis)
        return results