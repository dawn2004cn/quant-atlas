"""Retail assistant API sub-package."""

from app.presentation.api.v1.retail_assistant.hub_routes import register_retail_assistant_hub_routes
from app.presentation.api.v1.retail_assistant.insight_routes import register_retail_assistant_insight_routes
from app.presentation.api.v1.retail_assistant.psychology_routes import register_retail_assistant_psychology_routes
from app.presentation.api.v1.retail_assistant.runtime import RetailAssistantRuntime
from app.presentation.api.v1.retail_assistant.shadow_routes import register_retail_assistant_shadow_routes

__all__ = [
    "RetailAssistantRuntime",
    "register_retail_assistant_hub_routes",
    "register_retail_assistant_insight_routes",
    "register_retail_assistant_psychology_routes",
    "register_retail_assistant_shadow_routes",
]
