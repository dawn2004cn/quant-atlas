"""Context Module definitions for Quant Atlas API.

This module defines the bounded contexts that group related services and routes.
Each ContextModule is self-describing and can be discovered automatically.

Usage:
    from app.presentation.api.context_modules import discover_context_modules

    for module in discover_context_modules():
        logger.debug("%s: %s", module.name, module.description)
"""

from __future__ import annotations

from app.core.registry import ContextModule

# Lazy module loading map — avoids importing all 14 modules at startup,
# breaking circular dependencies between context modules.
_MODULE_IMPORT_MAP = {
    "AIAgentContextModule": "app.modules.ai_agent.module",
    "CollaborationContextModule": "app.modules.collaboration.module",
    "DataContextModule": "app.modules.data.module",
    "ExecutionContextModule": "app.modules.execution.module",
    "MarketDataContextModule": "app.modules.market_data.module",
    "MeshContextModule": "app.modules.mesh.module",
    "MiscContextModule": "app.modules.misc.module",
    "PerceptionContextModule": "app.modules.perception.module",
    "PortfolioContextModule": "app.modules.portfolio.module",
    "PortfolioRiskContextModule": "app.modules.portfolio_risk.module",
    "ResearchContextModule": "app.modules.research.module",
    "StrategyContextModule": "app.modules.strategy.module",
    "SystemContextModule": "app.modules.system.module",
    "UserContextModule": "app.modules.user.module",
}

_loaded_modules: dict[str, type] = {}


def _load_module(name: str) -> type:
    """Lazily import and cache a context module class."""
    if name not in _loaded_modules:
        import importlib
        mod_path = _MODULE_IMPORT_MAP[name]
        module = importlib.import_module(mod_path)
        _loaded_modules[name] = getattr(module, name)
    return _loaded_modules[name]


def __getattr__(name: str) -> type:
    """Lazy import for context module classes."""
    if name in _MODULE_IMPORT_MAP:
        return _load_module(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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


def ensure_all_modules_loaded() -> None:
    """Force-load all context modules (e.g., at app startup)."""
    for name in _MODULE_IMPORT_MAP:
        _load_module(name)


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
    "ensure_all_modules_loaded",
]
