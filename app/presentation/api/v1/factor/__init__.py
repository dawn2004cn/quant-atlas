"""Factor API sub-package."""

from app.presentation.api.v1.factor.ortho_routes import register_factor_ortho_routes
from app.presentation.api.v1.factor.self_correction_routes import register_factor_self_correction_routes
from app.presentation.api.v1.factor.calculate_routes import register_factor_calculate_routes

__all__ = [
    "register_factor_ortho_routes",
    "register_factor_self_correction_routes",
    "register_factor_calculate_routes",
]
