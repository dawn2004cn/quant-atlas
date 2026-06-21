"""Backward-compat re-export for ``InvestmentManagerService``."""
from __future__ import annotations

from app.modules.execution.services.investment_manager_service import (
    InvestmentManagerService,
)

__all__ = [
    "InvestmentManagerService",
]
