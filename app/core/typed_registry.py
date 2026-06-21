"""Protocol-based service registry for quant-atlas.

This is the **single canonical registry** — a consolidation of the legacy
string-based ``ServiceRegistry`` and the prototype ``TypedServiceRegistry``.

Features:
- ``@registry.service(name="...", depends=[...])`` decorator for registration
- Protocol-based type hints for dependency injection
- Lazy factory registration via ``@registry.factory(name="...")``
- Topological ordering of dependencies
- Health checks and introspection
- Backward-compatible with old ``@register_service`` (delegates internally)

Usage::

    from app.core.typed_registry import TypedServiceRegistry, service

    registry = TypedServiceRegistry()

    @registry.service(name="db", depends=[])
    class Database:
        ...

    @registry.service(name="repo", depends=["db"])
    class Repository:
        def __init__(self, db: Database):
            self.db = db

    repo = registry.resolve("repo")  # type: Repository


Backward compatibility
-----------------------

Old code using ``@register_service``, ``register_factory()``, and
``ServiceRegistry`` from ``app.core.service_registry`` continues to work —
all calls delegate to the singleton ``TypedServiceRegistry`` instance.

The ``configure_service_registry()`` function from ``app.core.registry``
still creates a bootstrap registry; the new code uses ``TypedServiceRegistry``
internally and replaces the old ``ServiceRegistry`` class.

.. deprecated::
    ``app.core.service_registry`` is deprecated. Use
    ``app.core.typed_registry`` with ``@service()`` or ``@factory()``
    decorators for new code.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any, Callable, Protocol

logger = logging.getLogger(__name__)


# ── Protocols ──────────────────────────────────────────────────────────


class ServiceProtocol(Protocol):
    """Base protocol that all registered services should satisfy."""

    def health_check(self) -> dict[str, Any]:
        """Return service health status."""
        ...


# ── Registry entry ─────────────────────────────────────────────────────


class _ServiceEntry:
    """Internal descriptor for a registered service."""

    __slots__ = (
        "name", "instance", "factory", "depends",
        "is_factory", "cls", "scope",
    )

    def __init__(
        self,
        name: str,
        instance: Any | None = None,
        factory: Callable[..., Any] | None = None,
        depends: list[str] | None = None,
        scope: str = "singleton",
    ) -> None:
        self.name = name
        self.instance = instance
        self.factory = factory
        self.depends = list(depends or [])
        self.is_factory = factory is not None
        self.cls = instance.__class__ if instance is not None else None
        self.scope = scope


# ── TypedServiceRegistry ──────────────────────────────────────────────


class TypedServiceRegistry:
    """Type-safe service registry with decorator-based registration.

    This replaces both the old ``ServiceRegistry`` (string-based, runtime DI)
    and the prototype ``TypedServiceRegistry``. All legacy APIs are preserved
    via delegation.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._entries: dict[str, _ServiceEntry] = {}
        self._config = config or {}

    # ── Registration ─────────────────────────────────────────────────

    def register(
        self,
        name: str,
        service: Any,
        depends: list[str] | None = None,
        scope: str = "singleton",
    ) -> None:
        """Register a service instance or class with its dependencies."""
        existing = self._entries.get(name)
        if existing is not None and existing.is_factory:
            return
        if isinstance(service, type):
            entry = _ServiceEntry(name=name, depends=depends, scope=scope)
            entry.cls = service
            self._entries[name] = entry
            return
        self._entries[name] = _ServiceEntry(
            name=name,
            instance=service,
            depends=depends,
            scope=scope,
        )

    def register_factory(
        self,
        name: str,
        factory: Callable[..., Any],
        depends: list[str] | None = None,
    ) -> None:
        """Register a factory function for lazy service creation."""
        self._entries[name] = _ServiceEntry(
            name=name,
            factory=factory,
            depends=depends,
            scope="singleton",
        )

    def register_decorator(
        self,
        name: str | None = None,
        depends: list[str] | None = None,
        scope: str = "singleton",
    ) -> Callable[[Any], Any]:
        """Decorator-style registration on the registry instance.

        Usage::

            @registry.register_decorator(name="my_service", depends=["dep_a"])
            class MyService:
                def __init__(self, dep_a: DepService): ...
        """
        def decorator(obj: Any) -> Any:
            svc_name = name or (obj.__name__ if hasattr(obj, "__name__") else "")
            if callable(obj) and not isinstance(obj, type):
                self.register_factory(svc_name, obj, depends)
            else:
                self.register(svc_name, obj, depends, scope=scope)
            return obj
        return decorator

    def service(
        self,
        name: str | None = None,
        depends: list[str] | None = None,
        scope: str = "singleton",
    ) -> Callable[[Any], Any]:
        """Decorator to register a service class or instance.

        Usage::

            @registry.service(name="my_service", depends=["other_service"])
            class MyService:
                def __init__(self, other: OtherService):
                    ...
        """
        def decorator(obj: Any) -> Any:
            svc_name = name or (obj.__name__ if hasattr(obj, "__name__") else "")
            if callable(obj) and not isinstance(obj, type):
                self.register_factory(svc_name, obj, depends)
            else:
                self.register(svc_name, obj, depends, scope=scope)
            return obj
        return decorator

    def factory(
        self,
        name: str | None = None,
        depends: list[str] | None = None,
    ) -> Callable[[Any], Any]:
        """Decorator to register a factory function.

        Usage::

            @registry.factory(name="my_factory", depends=["dep_a"])
            def make_my_service(dep_a):
                return MyService(dep_a=dep_a)
        """
        def decorator(fn: Callable[..., Any]) -> Any:
            svc_name = name or (fn.__name__ if hasattr(fn, "__name__") else "")
            self.register_factory(svc_name, fn, depends)
            return fn
        return decorator

    # ── Resolution ───────────────────────────────────────────────────

    def resolve(self, name: str) -> Any:
        """Resolve a service by name, creating it from factory if needed."""
        if name not in self._entries:
            raise KeyError(f"Service '{name}' not registered. "
                           f"Available: {list(self._entries)}")
        entry = self._entries[name]

        # Already resolved singleton (not a bare class left from @register_service)
        if entry.instance is not None and not isinstance(entry.instance, type):
            return entry.instance

        if entry.is_factory:
            dep_names = entry.depends
            resolved_deps = {n: self.resolve(n) for n in dep_names}
            if resolved_deps:
                resolved_deps["_registry"] = self
                instance = entry.factory(**resolved_deps)
            else:
                instance = entry.factory(self)
            if entry.scope == "singleton":
                entry.instance = instance
            return instance

        # Plain class registration (@register_service) without factory
        service_cls = entry.cls
        if service_cls is None and isinstance(entry.instance, type):
            service_cls = entry.instance
        if service_cls is not None:
            dep_names = entry.depends
            resolved_deps = {n: self.resolve(n) for n in dep_names}
            try:
                instance = service_cls(**resolved_deps) if resolved_deps else service_cls()
            except TypeError:
                instance = service_cls()
            if entry.scope == "singleton":
                entry.instance = instance
            return instance

        if entry.instance is not None:
            return entry.instance

        raise RuntimeError(f"Cannot resolve service '{name}': no factory or instance")

    # ── Query helpers ────────────────────────────────────────────────

    def get_or_none(self, name: str) -> Any:
        """Resolve or return None (no-op if not registered)."""
        try:
            return self.resolve(name)
        except (KeyError, Exception):
            return None

    def get(self, service_type: type | str) -> Any:
        """Resolve a service by class or name.

        Respects ``enabled_by`` logic: if a service config key exists
        in ``_config`` and is falsy, returns None (via get_or_none path).
        """
        key = service_type if isinstance(service_type, str) else service_type.__name__

        # Check enabled_by
        entry = self._entries.get(key)
        if entry is not None and entry.cls is not None:
            enabled_by = getattr(entry.cls, "_enabled_by", None)
            if enabled_by and not self._config.get(enabled_by, True):
                logger.debug("Service %s disabled by config key %s", key, enabled_by)
                return None

        return self.resolve(key)

    def is_registered(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._entries

    def registered_names(self) -> list[str]:
        """Return all registered service names."""
        return list(self._entries.keys())

    def is_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled based on config."""
        entry = self._entries.get(service_name)
        if entry is None:
            return False
        enabled_by = getattr(entry.cls, "_enabled_by", None) or self._config.get(service_name + "_ENABLED")
        if not enabled_by:
            return True
        return bool(self._config.get(enabled_by, True))

    def list_enabled_services(self) -> list[str]:
        """List all services that are enabled based on config."""
        return [name for name in self._entries if self.is_enabled(name)]

    def list_disabled_services(self) -> list[str]:
        """List all services that are disabled based on config."""
        return [name for name in self._entries if not self.is_enabled(name)]

    def validate_dependencies(self) -> list[str]:
        """Strictly validate that all registered services have their dependencies resolved.

        Returns a list of missing or disabled dependencies.
        """
        missing = []
        for name, entry in self._entries.items():
            deps = entry.depends
            for dep in deps:
                if not self.is_enabled(dep):
                    missing.append(f"Service {name!r} depends on {dep!r}, but it is missing or disabled.")
        return missing

    # ── Ordering ─────────────────────────────────────────────────────

        """Return services in topological order (dependencies first)."""
        visited: set[str] = set()
        order: list[str] = []

        def visit(name: str) -> None:
            if name in visited or name not in self._entries:
                return
            visited.add(name)
            for dep in self._entries[name].depends:
                visit(dep)
            if name not in order:
                order.append(name)

        for name in self._entries:
            visit(name)
        return order

    def wire_to(self, services: Any) -> list[str]:
        """Populate a namespace object (e.g. BootstrapServices) from the registry.

        Only sets attributes that are unset or ``None`` on *services*.
        Avoids triggering dynamic ``__getattr__`` resolvers during wiring.
        Returns the list of attribute names that were wired.
        """
        wired: list[str] = []
        instance_dict = getattr(services, "__dict__", None)
        ordered = self.topological_order()
        for name in ordered:
            if isinstance(instance_dict, dict) and instance_dict.get(name) is not None:
                continue
            try:
                instance = self.get(name)
                if instance is not None:
                    setattr(services, name, instance)
                    wired.append(name)
            except Exception as exc:
                logger.warning("registry.wire_to skipped %s: %s", name, exc)
        return wired

    def topological_order(self) -> list[str]:
        """Return registered service names in dependency order (topological sort)."""
        visited: set[str] = set()
        order: list[str] = []
        visiting: set[str] = set()  # cycle detection

        def _visit(name: str) -> None:
            if name in order:
                return
            if name in visiting:
                logger.warning("Circular dependency detected for service '%s'", name)
                return
            entry = self._entries.get(name)
            if entry is None:
                return
            visiting.add(name)
            for dep in (entry.depends or []):
                _visit(dep)
            visiting.discard(name)
            order.append(name)

        for name in self._entries:
            _visit(name)
        return order

    def get_all(self, *, include_disabled: bool = False) -> dict[str, Any]:
        """Eagerly resolve and return all registered services."""
        result: dict[str, Any] = {}
        for key in list(self._entries):
            instance = self.get(key)
            if instance is not None or include_disabled:
                result[key] = instance
        return result

    # ── Health ───────────────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        """Check health of all registered services."""
        results: dict[str, Any] = {}
        for name, entry in self._entries.items():
            instance = entry.instance
            if instance is None:
                # Try to resolve
                try:
                    instance = self.get(name)
                except Exception:
                    results[name] = {"status": "unresolved"}
                    continue
            if instance is not None and hasattr(instance, "health_check"):
                try:
                    results[name] = instance.health_check()
                except Exception as e:
                    results[name] = {"status": "error", "error": str(e)}
            else:
                results[name] = {"status": "ok"}
        return results

    # ── Lifecycle ────────────────────────────────────────────────────

    def clear(self) -> None:
        """Clear all registrations and cached instances (tests only)."""
        self._entries.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._entries


# ── Module-level singleton ─────────────────────────────────────────────

_registry = TypedServiceRegistry()


def get_registry() -> TypedServiceRegistry:
    """Get the module-level registry singleton."""
    return _registry


def reset_registry() -> None:
    """Clear the registry singleton (tests only)."""
    global _registry
    _registry = TypedServiceRegistry()


# ── Standalone decorators ──────────────────────────────────────────────


def service(
    name: str | None = None,
    depends: list[str] | None = None,
    scope: str = "singleton",
) -> Callable[[Any], Any]:
    """Decorator to register a service class or instance on the global registry.

    Usage::

        @service(name="my_service", depends=["other_service"])
        class MyService:
            def __init__(self, other: OtherService):
                ...
    """
    def decorator(obj: Any) -> Any:
        svc_name = name or (obj.__name__ if hasattr(obj, "__name__") else "")
        if callable(obj) and not isinstance(obj, type):
            _registry.register_factory(svc_name, obj, depends)
        else:
            _registry.register(svc_name, obj, depends, scope=scope)
        return obj
    return decorator


def factory(
    name: str | None = None,
    depends: list[str] | None = None,
) -> Callable[[Any], Any]:
    """Decorator to register a factory function on the global registry.

    Usage::

        @factory(name="my_factory", depends=["dep_a"])
        def make_my_service(dep_a):
            return MyService(dep_a=dep_a)
    """
    def decorator(fn: Callable[..., Any]) -> Any:
        svc_name = name or (fn.__name__ if hasattr(fn, "__name__") else "")
        _registry.register_factory(svc_name, fn, depends)
        return fn
    return decorator


# ── Legacy bootstrap helper ────────────────────────────────────────────


def configure_service_registry(
    config: dict[str, Any] | None = None,
) -> TypedServiceRegistry:
    """Create a bootstrap registry with config (replaces old ServiceRegistry).

    This is the entry point used by ``bootstrap.py``. It creates a
    **new** TypedServiceRegistry instance (not modifying the global singleton)
    so that bootstrap wiring is isolated from any pre-existing registrations.

    .. deprecated::
        New code should use ``TypedServiceRegistry(config=...)`` directly.
    """
    return TypedServiceRegistry(config=config or {})


# ── Backward-compatible re-exports (wrap with deprecation warnings) ─────


def registered_service_names() -> list[str]:
    """Get names of all registered services (backward compat)."""
    warnings.warn(
        "registered_service_names() is deprecated. "
        "Use get_registry().registered_names() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _registry.registered_names()


def topological_service_order() -> list[str]:
    """Get services in topological order (backward compat)."""
    warnings.warn(
        "topological_service_order() is deprecated. "
        "Use get_registry().topological_order() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _registry.topological_order()


def clear_factories() -> None:
    """Clear all registered services (backward compat)."""
    warnings.warn(
        "clear_factories() is deprecated. "
        "Use get_registry().clear() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    _registry.clear()


def is_service_registered(name: str) -> bool:
    """Check if a service is registered (backward compat)."""
    warnings.warn(
        "is_service_registered() is deprecated. "
        "Use get_registry().is_registered() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return name in _registry


def register_service(
    cls=None,
    *,
    name: str | None = None,
    scope: str = "singleton",
    depends: list[str] | None = None,
    factory: Callable | None = None,
    enabled_by: str | None = None,
    lazy: bool = False,
):
    """Decorator that registers a service (backward compat -- deprecated)."""
    warnings.warn(
        "@register_service is deprecated. "
        "Use @service() from app.core.typed_registry instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    def _decorate(klass: type) -> type:
        key = name or klass.__name__
        if enabled_by:
            # Store enabled_by on class for registry resolution check
            klass._enabled_by = enabled_by  # type: ignore[attr-defined]

        if factory is not None:
            _registry.register_factory(key, factory, depends)
        else:
            _registry.register(key, klass, depends, scope=scope)
        return klass

    if cls is not None:
        return _decorate(cls)
    return _decorate


def register_factory(
    name: str,
    fn: Callable[..., Any],
    depends: list[str] | None = None,
) -> None:
    """Register a factory (backward compat -- deprecated)."""
    warnings.warn(
        "register_factory() is deprecated. "
        "Use @factory() or @registry.factory() from app.core.typed_registry instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    _registry.register_factory(name, fn, depends)


class ServiceRegistry:
    """Legacy runtime service container (delegates to TypedServiceRegistry).

    .. deprecated::
        Use ``TypedServiceRegistry`` directly.
    """

    def __init__(self, *, config: dict[str, Any] | None = None, **overrides: Any) -> None:
        self._config = config or {}
        self._overrides: dict[str, Any] = dict(overrides)
        # Delegate to a TypedServiceRegistry instance
        self._registry = TypedServiceRegistry(config=config)
        # Pre-populate overrides
        for key, instance in overrides.items():
            self._registry.register(key, instance, [])

    def get(self, service_type: type | str) -> Any:
        """Resolve a service by class or registered name."""
        key = service_type if isinstance(service_type, str) else service_type.__name__

        # Check overrides first
        if key in self._overrides:
            return self._overrides[key]

        # Check enabled_by
        entry = _registry._entries.get(key)
        if entry is not None and entry.cls is not None:
            enabled_by = getattr(entry.cls, "_enabled_by", None)
            if enabled_by and not self._config.get(enabled_by, True):
                logger.debug("Service %s disabled by config key %s", key, enabled_by)
                return None

        return self._registry.resolve(key)

    def get_or_none(self, service_type: type | str) -> Any:
        """Like ``get()`` but returns ``None`` instead of raising."""
        try:
            return self.get(service_type)
        except (KeyError, Exception):
            return None

    def get_all(self, *, include_disabled: bool = False) -> dict[str, Any]:
        """Eagerly resolve all registered services."""
        return self._registry.get_all(include_disabled=include_disabled)

    def is_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled based on config."""
        return self._registry.is_enabled(service_name)

    def list_enabled_services(self) -> list[str]:
        """List all services that are enabled based on config."""
        return self._registry.list_enabled_services()

    def list_disabled_services(self) -> list[str]:
        """List all services that are disabled based on config."""
        return self._registry.list_disabled_services()

    def wire_to(self, services: Any) -> list[str]:
        """Populate a namespace object from the registry."""
        return self._registry.wire_to(services)

    def register_factory(self, name: str, fn: Callable, depends: list[str] | None = None) -> None:
        self._registry.register_factory(name, fn, depends)


__all__ = [
    # Core classes
    "TypedServiceRegistry",
    "ServiceRegistry",
    "ServiceProtocol",
    # Global registry
    "get_registry",
    "reset_registry",
    _registry,
    # Decorators
    "service",
    "factory",
    "configure_service_registry",
    # Legacy backward-compat (deprecated)
    "registered_service_names",
    "topological_service_order",
    "clear_factories",
    "is_service_registered",
    "register_service",
    "register_factory",
]
