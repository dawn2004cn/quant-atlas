"""Service factories for optimization phase HTTP routes."""

from __future__ import annotations

from typing import Any


def get_dual_path_router() -> Any:
    from app.core.dual_path_router import get_dual_path_router as _get

    return _get()


def get_compliance_service() -> Any:
    from app.modules.system.services.compliance_service import ComplianceService

    return ComplianceService()


def get_complexity_budget_service() -> Any:
    from app.modules.system.services.complexity_budget_service import ComplexityBudgetService

    return ComplexityBudgetService()


def get_anti_decay_evolution_service() -> Any:
    from app.modules.system.services.anti_decay_evolution_service import AntiDecayEvolutionService

    return AntiDecayEvolutionService()
