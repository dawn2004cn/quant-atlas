"""Backward-compat re-export for ``FactorOrthogonalizationService`` and ``FactorSelfCorrectionService``."""
from __future__ import annotations

from app.modules.data.services.factor_orthogonalization_service import (
    FactorOrthogonalizationService,
    FactorSelfCorrectionService,
)

__all__ = [
    "FactorOrthogonalizationService",
    "FactorSelfCorrectionService",
]
