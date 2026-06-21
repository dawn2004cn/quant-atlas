"""One-click API sub-package."""

from app.presentation.api.v1.one_click.action_routes import register_one_click_action_routes
from app.presentation.api.v1.one_click.blueprint import one_click_blueprint
from app.presentation.api.v1.one_click.evidence_routes import register_one_click_evidence_routes
from app.presentation.api.v1.one_click.runtime import OneClickRuntime

__all__ = [
    "OneClickRuntime",
    "one_click_blueprint",
    "register_one_click_action_routes",
    "register_one_click_evidence_routes",
]
