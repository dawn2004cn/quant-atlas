from __future__ import annotations
"""Service Locator - Simple DI for optional services with lazy loading.

This module provides a simple service locator pattern for services
that aren't part of the main ServiceBundle but need to be accessed
from various parts of the application. Supports on-demand initialization
for heavy-weight services.
"""


from collections.abc import Callable
from typing import Any, ClassVar


from app.core.logger import get_logger

logger = get_logger(__name__)


class ServiceLocator:
    """Simple service locator for lazy service resolution."""

    _instance: ServiceLocator | None = None
    _services: ClassVar[dict[str, Callable]] = {}
    _resolved: ClassVar[dict[str, Any]] = {}
    _lazy_services: ClassVar[set[str]] = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, name: str, factory: Callable[[], Any], lazy: bool = False) -> None:
        """Register a service factory.

        Args:
            name: Service name
            factory: Factory function to create the service
            lazy: If True, service is only instantiated when first accessed
        """
        cls._services[name] = factory
        if lazy:
            cls._lazy_services.add(name)

    @classmethod
    def get(cls, name: str) -> Any:
        """Get a service by name, lazy-loading if needed."""
        if name not in cls._resolved:
            if name in cls._services:
                if name in cls._lazy_services:
                    logger.debug(f"Lazy loading service: {name}")
                cls._resolved[name] = cls._services[name]()
            else:
                raise KeyError(f"Service '{name}' not registered")
        return cls._resolved[name]

    @classmethod
    def is_lazy(cls, name: str) -> bool:
        """Check if a service is marked for lazy loading."""
        return name in cls._lazy_services

    @classmethod
    def preload(cls, names: list[str] | None = None) -> None:
        """Preload specific services or all non-lazy services."""
        if names is None:
            names = [n for n in cls._services if n not in cls._lazy_services]
        for name in names:
            try:
                cls.get(name)
            except Exception as e:
                logger.warning(f"Failed to preload service {name}: {e}")

    @classmethod
    def reset(cls) -> None:
        """Reset all resolved services (mainly for testing)."""
        cls._resolved.clear()

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations and resolved services."""
        cls._services.clear()
        cls._resolved.clear()
        cls._lazy_services.clear()


def service(name: str, lazy: bool = False):
    """Decorator to register a service factory.

    Args:
        name: Service name
        lazy: If True, service is only instantiated when first accessed
    """
    def decorator(func: Callable[[], Any]):
        ServiceLocator.register(name, func, lazy=lazy)
        return func
    return decorator


def register_services() -> None:
    """Deprecated: bootstrap uses explicit wiring in bootstrap_components."""
    logger.warning(
        "register_services() is deprecated; use bootstrap_components.create_services()",
    )


def get_service(name: str) -> Any:
    """Deprecated: resolve services from app.extensions['service_bundle']."""
    logger.warning("get_service(%s) is deprecated; use service_bundle", name)
    return ServiceLocator.get(name)


# ---------------------------------------------------------------------------
# Fallback port resolver — domain layer calls this via delegation to avoid
# importing infrastructure classes directly.
# ---------------------------------------------------------------------------

def _resolve_stock_cache():
    from app.infrastructure.database.stock_cache_db import StockCache
    return StockCache()


def _resolve_quote_provider():
    from app.infrastructure.adapters.tencent_quote_gateway import TencentQuoteGateway
    return TencentQuoteGateway()


def _resolve_news_provider():
    from app.infrastructure.providers.news import AkshareNewsProvider
    return AkshareNewsProvider()


_FALLBACK_MAP: dict[str, Callable] = {
    "stock_cache": _resolve_stock_cache,
    "quote_provider": _resolve_quote_provider,
    "news_provider": _resolve_news_provider,
}


def _register_fallback_services() -> None:
    """Register fallback port resolvers with ServiceLocator on first call."""
    already = set(ServiceLocator._services.keys())
    for name in _FALLBACK_MAP:
        if name not in already:
            ServiceLocator.register(name, _FALLBACK_MAP[name], lazy=True)


class _FallbackResolver:
    """Thin wrapper so domain can call ServiceLocator.resolve_fallback()."""

    @staticmethod
    def resolve(port_name: str) -> Any:
        _register_fallback_services()
        return ServiceLocator.get(port_name)


# Expose as a module-level function that domain layer can call
def resolve_fallback(port_name: str) -> Any:
    """Delegate port fallback resolution to ServiceLocator.

    Raises KeyError/RuntimeError if the port is not registered and has no
    built-in fallback.  This allows the caller to distinguish "not found"
    from a legitimate missing-adapter scenario.

    Called from domain/ports/port_registry.py to keep the domain layer
    free of direct infrastructure imports.
    """
    return _FallbackResolver.resolve(port_name)
