"""Risk companion API sub-package."""

from app.presentation.api.v1.risk_companion.blueprint import risk_companion_blueprint
from app.presentation.api.v1.risk_companion.detect_routes import register_risk_companion_detect_routes
from app.presentation.api.v1.risk_companion.profile_routes import register_risk_companion_profile_routes
from app.presentation.api.v1.risk_companion.runtime import RiskCompanionRuntime

__all__ = [
    "RiskCompanionRuntime",
    "register_risk_companion_detect_routes",
    "register_risk_companion_profile_routes",
    "risk_companion_blueprint",
]
