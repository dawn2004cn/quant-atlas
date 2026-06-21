"""Optimization phase API sub-package."""

from app.presentation.api.v1.optimization.budget_routes import register_optimization_budget_routes
from app.presentation.api.v1.optimization.compliance_routes import register_optimization_compliance_routes
from app.presentation.api.v1.optimization.dual_path_routes import register_optimization_dual_path_routes
from app.presentation.api.v1.optimization.evolution_routes import register_optimization_evolution_routes

__all__ = [
    "register_optimization_budget_routes",
    "register_optimization_compliance_routes",
    "register_optimization_dual_path_routes",
    "register_optimization_evolution_routes",
]
