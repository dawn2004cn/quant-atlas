from __future__ import annotations

"""Multi-factor orthogonalization interceptor.

This service checks if a new alpha has high correlation with existing
portfolio factors before deployment. If correlation > 0.7, reject deployment.
"""


from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrthogonalizationResult:
    """Result of orthogonalization check."""
    is_accepted: bool
    max_correlation: float
    correlated_factors: list[dict[str, Any]]
    recommendation: str


class FactorOrthogonalizationService:
    """Service for checking factor orthogonalization before deployment."""

    CORRELATION_THRESHOLD = 0.7

    def __init__(self, existing_factors: list[dict[str, Any]] | None = None):
        self._existing_factors = existing_factors or []
        self._factor_matrix: np.ndarray | None = None

    def register_factor(self, factor_id: str, factor_values: list[float]) -> None:
        """Register a new factor to the tracking matrix."""
        self._existing_factors.append({
            "id": factor_id,
            "values": factor_values,
        })
        self._factor_matrix = None
        logger.info(f"Registered factor: {factor_id}")

    def check_orthogonalization(
        self,
        new_factor_id: str,
        new_factor_values: list[float],
    ) -> OrthogonalizationResult:
        """Check if new factor is orthogonal to existing factors."""
        if not self._existing_factors:
            return OrthogonalizationResult(
                is_accepted=True,
                max_correlation=0.0,
                correlated_factors=[],
                recommendation="No existing factors, auto-accepted",
            )

        new_arr = np.array(new_factor_values)
        if len(new_arr) < 2:
            return OrthogonalizationResult(
                is_accepted=False,
                max_correlation=0.0,
                correlated_factors=[],
                recommendation="Insufficient data for correlation",
            )

        correlated = []
        max_corr = 0.0

        for existing in self._existing_factors:
            existing_arr = np.array(existing["values"])

            if len(existing_arr) != len(new_arr):
                continue

            if np.std(existing_arr) > 0 and np.std(new_arr) > 0:
                corr = np.corrcoef(existing_arr, new_arr)[0, 1]
                corr = abs(corr) if not np.isnan(corr) else 0.0

                if corr > max_corr:
                    max_corr = corr

                if corr > self.CORRELATION_THRESHOLD:
                    correlated.append({
                        "factor_id": existing["id"],
                        "correlation": corr,
                    })

        is_accepted = max_corr < self.CORRELATION_THRESHOLD

        if is_accepted:
            recommendation = f"Accepted (max corr: {max_corr:.2f})"
        else:
            recommendation = f"Rejected - correlated with {len(correlated)} factors"

        logger.info(f"Orthogonalization check: {new_factor_id} - {recommendation}")

        return OrthogonalizationResult(
            is_accepted=is_accepted,
            max_correlation=max_corr,
            correlated_factors=correlated,
            recommendation=recommendation,
        )

    def get_factor_correlation_matrix(self) -> np.ndarray:
        """Get correlation matrix of all tracked factors."""
        if not self._existing_factors:
            return np.array([])

        n = len(self._existing_factors)
        matrix = np.zeros((n, len(self._existing_factors[0]["values"])))

        for i, f in enumerate(self._existing_factors):
            matrix[i] = f["values"]

        return np.corrcoef(matrix)


_factor_orthogonalizer: FactorOrthogonalizationService | None = None


def get_factor_orthogonalizer() -> FactorOrthogonalizationService:
    """Get the global orthogonalization service."""
    global _factor_orthogonalizer
    if _factor_orthogonalizer is None:
        _factor_orthogonalizer = FactorOrthogonalizationService()
    return _factor_orthogonalizer
