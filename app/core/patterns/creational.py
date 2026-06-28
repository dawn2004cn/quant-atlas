from __future__ import annotations

"""
Creational Design Patterns
===========================

1. Singleton - Ensure single instance with global access
2. Factory Method - Create objects via subclass determination
3. Abstract Factory - Create families of related objects
4. Builder - Construct complex objects step by step
5. Prototype - Clone existing objects
"""

import copy
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar('T')


class SingletonMeta(type):
    """Thread-safe Singleton implementation."""

    _instances: dict[type, object] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs) -> object:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def reset(cls, instance_class: type | None = None) -> None:
        """Reset singleton instance(s)."""
        with cls._lock:
            if instance_class:
                cls._instances.pop(instance_class, None)
            else:
                cls._instances.clear()


class Singleton(Generic[T], metaclass=SingletonMeta):
    """Base class for singleton objects."""

    @classmethod
    def get_instance(cls: type[T]) -> T:
        """Get singleton instance."""
        return cls()


class ThreadSafeSingleton(Generic[T]):
    """Thread-safe singleton with lazy initialization."""

    _instance: T | None = None
    _lock = threading.Lock()

    def __new__(cls: type[T], *args, **kwargs) -> T:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.__init__(*args, **kwargs)
        return cls._instance


class Factory(Generic[T]):
    """Generic factory for object creation."""

    def __init__(self) -> None:
        self._registry: dict[str, Callable[..., T]] = {}

    def register(self, key: str, creator: Callable[..., T]) -> None:
        """Register a creator function."""
        self._registry[key] = creator

    def create(self, key: str, *args, **kwargs) -> T | None:
        """Create object by key."""
        creator = self._registry.get(key)
        if creator:
            return creator(*args, **kwargs)
        return None

    def keys(self) -> list[str]:
        """Get all registered keys."""
        return list(self._registry.keys())


class FactoryMethod(ABC):
    """Abstract Factory Method pattern."""

    @abstractmethod
    def create_product(self, product_type: str) -> object | None:
        """Create product based on type."""
        pass


class ProductA(ABC):
    """Abstract Product A."""
    @abstractmethod
    def operation(self) -> str:
        pass


class ProductB(ABC):
    """Abstract Product B."""
    @abstractmethod
    def operation(self) -> str:
        pass


class ConcreteProductA(ProductA):
    def operation(self) -> str:
        return "ConcreteProductA"


class ConcreteProductB(ProductB):
    def operation(self) -> str:
        return "ConcreteProductB"


class AbstractFactory(ABC):
    """Abstract Factory for creating families of products."""

    @abstractmethod
    def create_product_a(self) -> ProductA:
        pass

    @abstractmethod
    def create_product_b(self) -> ProductB:
        pass


class ConcreteFactory(AbstractFactory):
    def create_product_a(self) -> ProductA:
        return ConcreteProductA()

    def create_product_b(self) -> ProductB:
        return ConcreteProductB()


@dataclass
class Builder(Generic[T]):
    """Builder pattern for complex object construction."""

    _result: T | None = None
    _reset_on_build: bool = True

    def reset(self: Builder[T]) -> Builder[T]:
        """Reset builder state."""
        return self

    def build(self) -> T:
        """Build and return the object."""
        if self._reset_on_build:
            result = self._result
            self._result = None
            return result
        return self._result


class Director:
    """Director for builder pattern."""

    def __init__(self, builder: Builder) -> None:
        self._builder = builder

    def build_minimal(self) -> object:
        """Build with minimal configuration."""
        return self._builder.build()

    def build_full(self) -> object:
        """Build with full configuration."""
        return self._builder.build()


class Cloneable(ABC):
    """Prototype interface."""

    @abstractmethod
    def clone(self) -> Cloneable:
        """Create a deep copy of this object."""
        pass


class Prototype(Cloneable):
    """Base prototype implementation."""

    def clone(self) -> Cloneable:
        """Create a deep clone."""
        return copy.deepcopy(self)


class ConcretePrototype(Prototype):
    """Concrete prototype example."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def __repr__(self) -> str:
        return f"ConcretePrototype({self.data})"


class Registry(Generic[T]):
    """Generic registry for factory/flyweight patterns."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def register(self, key: str, item: T) -> None:
        self._items[key] = item

    def get(self, key: str) -> T | None:
        return self._items.get(key)

    def unregister(self, key: str) -> bool:
        return self._items.pop(key, None) is not None

    def keys(self) -> list[str]:
        return list(self._items.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._items


def singleton(cls: type[T]) -> type[T]:
    """Decorator to make a class singleton."""
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


__all__ = [
    'SingletonMeta',
    'Singleton',
    'ThreadSafeSingleton',
    'Factory',
    'FactoryMethod',
    'ProductA', 'ProductB',
    'ConcreteProductA', 'ConcreteProductB',
    'AbstractFactory', 'ConcreteFactory',
    'Builder',
    'Director',
    'Cloneable',
    'Prototype',
    'ConcretePrototype',
    'Registry',
    'singleton',
]
