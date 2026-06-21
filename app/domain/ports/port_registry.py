from __future__ import annotations

"""Port registry for dependency inversion - centralizes infrastructure access."""

from typing import Any, Callable, Protocol

from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Public API ──────────────────────────────────────────────────────────


class PortAdapter(Protocol):
    """Protocol for port adapters."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class ResolverCallable(Protocol):
    """Signature for the optional application-layer fallback resolver."""

    def __call__(self, port_name: str) -> Any:
        ...


# Module-level fallback resolver — set during bootstrap wiring.
# This avoids importing application-layer code at domain import time.
_fallback_resolver: ResolverCallable | None = None


def set_fallback_resolver(resolver: ResolverCallable) -> None:
    """Inject the application-layer fallback resolver.

    Call this during application bootstrap (e.g. in bootstrap.py) so that
    the domain layer never imports application code directly.
    """
    global _fallback_resolver  # noqa: PLW0603
    _fallback_resolver = resolver


def resolve_infrastructure_port(port_name: str, **kwargs: Any) -> Any:
    """Resolve infrastructure port through registry or optional fallback.

    Resolution order:
    1. ``PortRegistry`` (pure domain layer)
    2. Application-layer fallback resolver (injected via ``set_fallback_resolver``)

    If neither has the port, returns ``None``.
    """
    adapter = PortRegistry.resolve(port_name)
    if adapter is not None:
        return adapter(**kwargs)

    # Optional application-layer fallback
    if _fallback_resolver is not None:
        try:
            return _fallback_resolver(port_name)
        except Exception:  # noqa: BLE001
            logger.warning("Fallback resolver failed for port '%s'", port_name)

    logger.warning("Could not resolve port '%s', returning None", port_name)
    return None


# ── PortRegistry ────────────────────────────────────────────────────────


class PortRegistry:
    """Central registry for port-to-adapter mappings.

    Enables dependency inversion by mapping interface ports
    to concrete infrastructure adapters.
    """

    _instance: PortRegistry | None = None
    _ports: dict[str, PortAdapter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, port_name: str, adapter_factory: PortAdapter) -> None:
        """Register a port adapter."""
        cls._ports[port_name] = adapter_factory
        logger.debug("Registered port adapter: %s", port_name)

    @classmethod
    def get(cls, port_name: str, **kwargs: Any) -> Any:
        """Get an adapter for the given port."""
        if port_name not in cls._ports:
            raise KeyError(f"Port '{port_name}' not registered")
        factory = cls._ports[port_name]
        return factory(**kwargs)

    @classmethod
    def resolve(cls, port_name: str, default: Any = None) -> Any:
        """Resolve a port, returning default if not registered."""
        if port_name not in cls._ports:
            return default
        return cls.get(port_name)

    @classmethod
    def has(cls, port_name: str) -> bool:
        """Check if a port is registered."""
        return port_name in cls._ports


# ── Decorator ───────────────────────────────────────────────────────────


def port(port_name: str):
    """Decorator to register a port adapter."""
    def decorator(func: PortAdapter):
        PortRegistry.register(port_name, func)
        return func
    return decorator


# ── Inline Protocols ────────────────────────────────────────────────────


class IStockCache(Protocol):
    """Port for stock cache access."""

    def get_quote(self, symbol: str, market: str) -> dict[str, Any] | None:
        ...

    def set_quote(self, symbol: str, market: str, data: dict[str, Any], ttl: int = 60) -> None:
        ...


class IQuoteProvider(Protocol):
    """Port for real-time quote providers."""

    def get_quote(self, symbol: str, market: str) -> dict[str, Any] | None:
        ...

    def get_quotes(self, symbols: list[str], market: str) -> list[dict[str, Any]]:
        ...
