from __future__ import annotations

"""Dependency Injection Container.

Provides simple DI for dependency inversion.
"""


from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class ServiceDescriptor:
    """Service descriptor."""

    def __init__(
        self,
        interface: type,
        factory: Callable,
        scope: str = "singleton",
    ):
        self.interface = interface
        self.factory = factory
        self.scope = scope


class DIContainer:
    """Simple dependency injection container."""

    _instance: DIContainer | None = None

    def __init__(self):
        self._descriptors: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, Any] = {}

    @classmethod
    def get_instance(cls) -> DIContainer:
        if cls._instance is None:
            cls._instance = DIContainer()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def register(
        self,
        interface: type[T],
        factory: Callable[[DIContainer], T],
        scope: str = "singleton",
    ) -> None:
        self._descriptors[interface] = ServiceDescriptor(interface, factory, scope)

    def register_singleton(
        self,
        interface: type[T],
        instance: T,
    ) -> None:
        self._descriptors[interface] = ServiceDescriptor(
            interface, lambda _: instance, "singleton"
        )
        self._singletons[interface] = instance

    def resolve(self, interface: type[T]) -> T:
        if interface in self._singletons:
            return self._singletons[interface]

        desc = self._descriptors.get(interface)
        if not desc:
            raise ValueError(f"Service not registered: {interface}")

        if desc.scope == "singleton":
            instance = desc.factory(self)
            self._singletons[interface] = instance
            return instance

        return desc.factory(self)

    def resolve_optional(self, interface: type[T]) -> T | None:
        try:
            return self.resolve(interface)
        except ValueError:
            return None

    def is_registered(self, interface: type) -> bool:
        return interface in self._descriptors


_container: DIContainer | None = None


def get_container() -> DIContainer:
    global _container
    if _container is None:
        _container = DIContainer.get_instance()
    return _container


def register_service(
    interface: type[T],
    factory: Callable[[DIContainer], T],
    scope: str = "singleton",
) -> None:
    get_container().register(interface, factory, scope)


def resolve_service(interface: type[T]) -> T:
    return get_container().resolve(interface)


def resolve_optional_service(interface: type[T]) -> T | None:
    return get_container().resolve_optional(interface)


__all__ = [
    "DIContainer",
    "ServiceDescriptor",
    "get_container",
    "register_service",
    "resolve_service",
    "resolve_optional_service",
]
