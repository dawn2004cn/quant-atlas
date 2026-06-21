"""Lifecycle optimization API sub-package."""

from app.presentation.api.v1.lifecycle.data_routes import register_lifecycle_data_routes
from app.presentation.api.v1.lifecycle.execution_routes import register_lifecycle_execution_routes
from app.presentation.api.v1.lifecycle.monitoring_routes import register_lifecycle_monitoring_routes
from app.presentation.api.v1.lifecycle.research_routes import register_lifecycle_research_routes
from app.presentation.api.v1.lifecycle.simulation_routes import register_lifecycle_simulation_routes

__all__ = [
    "register_lifecycle_data_routes",
    "register_lifecycle_execution_routes",
    "register_lifecycle_monitoring_routes",
    "register_lifecycle_research_routes",
    "register_lifecycle_simulation_routes",
]
