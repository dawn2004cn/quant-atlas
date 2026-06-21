"""Data optimizer API sub-package."""

from app.presentation.api.v1.data_optimizer.scenario_routes import register_data_optimizer_scenario_routes
from app.presentation.api.v1.data_optimizer.tdx_routes import register_data_optimizer_tdx_routes
from app.presentation.api.v1.data_optimizer.write_routes import register_data_optimizer_write_routes

__all__ = [
    "register_data_optimizer_scenario_routes",
    "register_data_optimizer_tdx_routes",
    "register_data_optimizer_write_routes",
]
