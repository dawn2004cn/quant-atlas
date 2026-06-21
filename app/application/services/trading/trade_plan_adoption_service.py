"""Backward-compat re-export for ``TradePlanAdoptionService``."""
from __future__ import annotations

from app.modules.execution.services.trade_plan_adoption_service import (
    TradePlanAdoptionService,
)

__all__ = [
    "TradePlanAdoptionService",
]
