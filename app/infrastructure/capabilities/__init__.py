"""Self-registering capability plugins.

Usage::

    from app.infrastructure.capabilities.registry import capability, CapabilityRegistry
    from app.domain.capabilities.base import BaseCapability

    @capability("my_tool")
    class MyToolCapability(BaseCapability):
        capability_name = "my_tool"

        def execute(self, **kwargs) -> tuple[Any, str]:
            ...
"""

from app.infrastructure.capabilities.registry import CapabilityRegistry, capability
from app.infrastructure.capabilities import (
    bars_capability,
    profile_capability,
    financial_capability,
    news_capability,
    backtest_capability,
    selector_capability,
)

__all__ = [
    "CapabilityRegistry",
    "capability",
]
