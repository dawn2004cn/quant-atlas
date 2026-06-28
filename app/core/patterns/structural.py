from __future__ import annotations
"""
Structural Design Patterns
===========================

6. Adapter - Convert interface to expected format
7. Bridge - Separate abstraction from implementation
8. Composite - Treat individual and composite uniformly
9. Decorator - Add responsibilities dynamically
10. Facade - Simplified interface to complex system
11. Flyweight - Share objects to save memory
12. Proxy - Controlled access to objects
"""

from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Callable


class Target(ABC):
    """Abstract target interface."""

    @abstractmethod
    def request(self) -> str:
        pass


class Adaptee:
    """Adaptee with incompatible interface."""

    def specific_request(self) -> str:
        return "Specific request from Adaptee"


class Adapter(Target):
    """Adapter that translates interface."""

    def __init__(self, adaptee: Adaptee) -> None:
        self._adaptee = adaptee

    def request(self) -> str:
        return f"Adapter: {self._adaptee.specific_request()}"


class AdapterWrapper(ABC):
    """Generic adapter wrapper."""

    @abstractmethod
    def adapt(self, obj: Any) -> Any:
        pass


class InterfaceAdapter(AdapterWrapper):
    """Generic interface adapter."""

    def __init__(self, adaptee: Any, method_map: dict[str, str] | None = None) -> None:
        self._adaptee = adaptee
        self._method_map = method_map or {}

    def adapt(self) -> Any:
        return self._adaptee

    def __getattr__(self, name: str) -> Callable:
        mapped = self._method_map.get(name, name)
        return getattr(self._adaptee, mapped)


class Abstraction(ABC):
    """Abstract abstraction."""

    @abstractmethod
    def operation(self) -> str:
        pass


class Implementation(ABC):
    """Abstract implementation."""

    @abstractmethod
    def implementation_operation(self) -> str:
        pass


class ConcreteImplementationA(Implementation):
    def implementation_operation(self) -> str:
        return "ConcreteImplementationA"


class ConcreteImplementationB(Implementation):
    def implementation_operation(self) -> str:
        return "ConcreteImplementationB"


class RefinedAbstraction(Abstraction):
    """Refined abstraction."""

    def __init__(self, implementation: Implementation) -> None:
        self._implementation = implementation

    def operation(self) -> str:
        return f"RefinedAbstraction: {self._implementation.implementation_operation()}"


class Component(ABC):
    """Abstract component."""

    @abstractmethod
    def operation(self) -> str:
        pass

    def add(self, component: Component) -> None:
        pass

    def remove(self, component: Component) -> None:
        pass

    def get_child(self, index: int) -> Component | None:
        return None


class Leaf(Component):
    """Leaf node in composite."""

    def __init__(self, name: str) -> None:
        self._name = name

    def operation(self) -> str:
        return f"Leaf({self._name})"


class Composite(Component):
    """Composite node."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._children: list[Component] = []

    def add(self, component: Component) -> None:
        self._children.append(component)

    def remove(self, component: Component) -> None:
        self._children.remove(component)

    def get_child(self, index: int) -> Component | None:
        return self._children[index] if 0 <= index < len(self._children) else None

    def operation(self) -> str:
        results = [child.operation() for child in self._children]
        return f"Composite({self._name}): [{', '.join(results)}]"


class ComponentDecorator(Component):
    """Base decorator."""

    def __init__(self, wrapped: Component) -> None:
        self._wrapped = wrapped

    def operation(self) -> str:
        return self._wrapped.operation()


class ConcreteDecoratorA(ComponentDecorator):
    """Concrete decorator adding behavior."""

    def __init__(self, wrapped: Component, extra: str = "") -> None:
        super().__init__(wrapped)
        self._extra = extra

    def operation(self) -> str:
        return f"DecoratorA({self._wrapped.operation()}){self._extra}"


class ConcreteDecoratorB(ComponentDecorator):
    """Concrete decorator adding behavior."""

    def operation(self) -> str:
        return f"DecoratorB({self._wrapped.operation()})"


def decorator(func: Callable) -> Callable:
    """Decorator function wrapper."""

    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


class Facade:
    """Facade providing simplified interface."""

    def __init__(self) -> None:
        self._subsystem_a: object | None = None
        self._subsystem_b: object | None = None

    def initialize(self, a: Any, b: Any) -> None:
        self._subsystem_a = a
        self._subsystem_b = b

    def simplified_operation(self) -> str:
        return "Facade: Simplified operation"


class FlyweightFactory:
    """Factory for flyweight objects."""

    def __init__(self) -> None:
        self._flyweights: dict[str, object] = {}

    def get_flyweight(self, key: str, creator: Callable[[], object]) -> object:
        if key not in self._flyweights:
            self._flyweights[key] = creator()
        return self._flyweights[key]


class Flyweight(ABC):
    """Abstract flyweight."""

    @abstractmethod
    def operation(self, extrinsic: str) -> None:
        pass


class ConcreteFlyweight(Flyweight):
    def __init__(self, intrinsic_state: str) -> None:
        self._intrinsic = intrinsic_state

    def operation(self, extrinsic: str) -> None:
        print(f"ConcreteFlyweight: {self._intrinsic}, {extrinsic}")


class UnsharedConcreteFlyweight(Flyweight):
    def __init__(self, state: str) -> None:
        self._state = state

    def operation(self, extrinsic: str) -> None:
        print(f"UnsharedConcreteFlyweight: {self._state}, {extrinsic}")


class Proxy(ABC):
    """Abstract proxy."""

    @abstractmethod
    def request(self) -> None:
        pass


class RealSubject(Proxy):
    """Real subject."""

    def request(self) -> None:
        print("RealSubject: Handling request")


class ProxySubject(Proxy):
    """Proxy with controlled access."""

    def __init__(self, real_subject: RealSubject | None = None) -> None:
        self._real_subject = real_subject
        self._access_granted = False

    def grant_access(self) -> None:
        self._access_granted = True

    def request(self) -> None:
        if self._access_granted:
            if self._real_subject is None:
                self._real_subject = RealSubject()
            self._real_subject.request()
        else:
            print("Proxy: Access denied")


class LazySubject(Proxy):
    """Lazy loading proxy."""

    _instance: Proxy | None = None

    def __init__(self) -> None:
        self._subject: RealSubject | None = None

    def request(self) -> None:
        if self._subject is None:
            self._subject = RealSubject()
        self._subject.request()


__all__ = [
    'Target',
    'Adaptee',
    'Adapter',
    'AdapterWrapper',
    'InterfaceAdapter',
    'Abstraction',
    'Implementation',
    'ConcreteImplementationA',
    'ConcreteImplementationB',
    'RefinedAbstraction',
    'Component',
    'Leaf',
    'Composite',
    'ComponentDecorator',
    'ConcreteDecoratorA',
    'ConcreteDecoratorB',
    'decorator',
    'Facade',
    'FlyweightFactory',
    'Flyweight',
    'ConcreteFlyweight',
    'UnsharedConcreteFlyweight',
    'Proxy',
    'RealSubject',
    'ProxySubject',
    'LazySubject',
]
