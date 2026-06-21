"""Context Module definitions for Quant Atlas API.

This module defines the bounded contexts that group related routes and services.
Each ContextModule is self-describing and can be discovered automatically.

Usage:
    from app.presentation.api.context_modules import discover_context_modules
    
    for module in discover_context_modules():
        logger.debug("%s: %s", module.name, module.description)
"""

from __future__ import annotations

from app.core.registry import ContextModule


# Phase 2 — physically packaged context modules (register @register_module on import)
from app.modules.ai_agent.module import AIAgentContextModule  # noqa: E402, F401
from app.modules.collaboration.module import CollaborationContextModule  # noqa: E402, F401
from app.modules.data.module import DataContextModule  # noqa: E402, F401
from app.modules.execution.module import ExecutionContextModule  # noqa: E402, F401
from app.modules.market_data.module import MarketDataContextModule  # noqa: E402, F401
from app.modules.mesh.module import MeshContextModule  # noqa: E402, F401
from app.modules.misc.module import MiscContextModule  # noqa: E402, F401
from app.modules.perception.module import PerceptionContextModule  # noqa: E402, F401
from app.modules.portfolio.module import PortfolioContextModule  # noqa: E402, F401
from app.modules.portfolio_risk.module import PortfolioRiskContextModule  # noqa: E402, F401
from app.modules.research.module import ResearchContextModule  # noqa: E402, F401
from app.modules.strategy.module import StrategyContextModule  # noqa: E402, F401
from app.modules.system.module import SystemContextModule  # noqa: E402, F401
from app.modules.user.module import UserContextModule  # noqa: E402, F401


def get_all_context_modules() -> list[ContextModule]:
    """Get all registered context modules."""
    from app.core.registry import discover_modules
    return discover_modules()


def get_context_module(name: str) -> ContextModule | None:
    """Get a specific context module by name."""
    from app.core.registry import get_module
    return get_module(name)


def list_context_names() -> list[str]:
    """List all registered context names."""
    from app.core.registry import list_modules
    return list_modules()


__all__ = [
    "AIAgentContextModule",
    "CollaborationContextModule",
    "DataContextModule",
    "ExecutionContextModule",
    "MarketDataContextModule",
    "MeshContextModule",
    "MiscContextModule",
    "PerceptionContextModule",
    "PortfolioContextModule",
    "PortfolioRiskContextModule",
    "ResearchContextModule",
    "StrategyContextModule",
    "SystemContextModule",
    "UserContextModule",
    "get_all_context_modules",
    "get_context_module",
    "list_context_names",
]
