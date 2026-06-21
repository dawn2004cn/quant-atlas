from __future__ import annotations
"""
Behavioral Design Patterns
==========================

13. Chain of Responsibility - Handle requests through chain
14. Command - Encapsulate request as object
15. Iterator - Traverse collections
16. Mediator - Manage object communication
17. Memento - Capture and restore state
18. Observer - Event notification
19. State - State machine
20. Strategy - Interchangeable algorithms
21. Template Method - Algorithm skeleton
22. Visitor - Operations on object structure
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar, Iterable
from dataclasses import dataclass, field
from datetime import datetime


T = TypeVar('T')


class Handler(ABC):
    """Abstract handler in chain."""
    
    def __init__(self) -> None:
        self._next_handler: Handler | None = None
    
    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        return handler
    
    def handle(self, request: Any) -> Any:
        if self._can_handle(request):
            return self._handle(request)
        elif self._next_handler:
            return self._next_handler.handle(request)
        return None
    
    @abstractmethod
    def _can_handle(self, request: Any) -> bool:
        pass
    
    @abstractmethod
    def _handle(self, request: Any) -> Any:
        pass


class ConcreteHandlerA(Handler):
    """Concrete handler A."""
    
    def _can_handle(self, request: Any) -> bool:
        return isinstance(request, str) and request.startswith("A")
    
    def _handle(self, request: Any) -> Any:
        return f"HandlerA handled: {request}"


class ConcreteHandlerB(Handler):
    """Concrete handler B."""
    
    def _can_handle(self, request: Any) -> bool:
        return isinstance(request, str) and request.startswith("B")
    
    def _handle(self, request: Any) -> Any:
        return f"HandlerB handled: {request}"


class Command(ABC):
    """Abstract command."""
    
    @abstractmethod
    def execute(self) -> Any:
        pass
    
    @abstractmethod
    def undo(self) -> None:
        pass


class ConcreteCommand(Command):
    """Concrete command."""
    
    def __init__(self, receiver: Any, action: Callable) -> None:
        self._receiver = receiver
        self._action = action
        self._executed = False
    
    def execute(self) -> Any:
        self._executed = True
        return self._action()
    
    def undo(self) -> None:
        if self._executed:
            print(f"Undoing command: {self._action}")
            self._executed = False


class MacroCommand(Command):
    """Composite command."""
    
    def __init__(self, commands: list[Command]) -> None:
        self._commands = commands
    
    def execute(self) -> Any:
        results = [cmd.execute() for cmd in self._commands]
        return results
    
    def undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()


class CommandInvoker:
    """Command invoker with undo support."""
    
    def __init__(self) -> None:
        self._history: list[Command] = []
    
    def execute(self, command: Command) -> Any:
        result = command.execute()
        self._history.append(command)
        return result
    
    def undo(self) -> None:
        if self._history:
            command = self._history.pop()
            command.undo()


class Iterator(ABC, Generic[T]):
    """Abstract iterator."""
    
    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        pass
    
    @abstractmethod
    def __next__(self) -> T:
        pass


class ConcreteIterator(Iterator[T]):
    """Concrete iterator."""
    
    def __init__(self, collection: list[T]) -> None:
        self._collection = collection
        self._position = 0
    
    def __iter__(self) -> Iterator[T]:
        return self
    
    def __next__(self) -> T:
        if self._position >= len(self._collection):
            raise StopIteration
        item = self._collection[self._position]
        self._position += 1
        return item


class ReverseIterator(Iterator[T]):
    """Reverse iterator."""
    
    def __init__(self, collection: list[T]) -> None:
        self._collection = collection
        self._position = len(collection) - 1
    
    def __iter__(self) -> Iterator[T]:
        return self
    
    def __next__(self) -> T:
        if self._position < 0:
            raise StopIteration
        item = self._collection[self._position]
        self._position -= 1
        return item


class IterableCollection(Iterable[T]):
    """Iterable collection."""
    
    def __init__(self) -> None:
        self._items: list[T] = []
    
    def add(self, item: T) -> None:
        self._items.append(item)
    
    def __iter__(self) -> Iterator[T]:
        return ConcreteIterator(self._items)
    
    def reverse(self) -> Iterator[T]:
        return ReverseIterator(self._items)


class Mediator(ABC):
    """Abstract mediator."""
    
    @abstractmethod
    def notify(self, sender: object, event: str) -> None:
        pass


class ConcreteMediator(Mediator):
    """Concrete mediator."""
    
    def __init__(self) -> None:
        self._component_a: object | None = None
        self._component_b: object | None = None
    
    def set_components(self, a: object, b: object) -> None:
        self._component_a = a
        self._component_b = b
    
    def notify(self, sender: object, event: str) -> None:
        print(f"Mediator: {event} from {sender}")


class Colleague(ABC):
    """Abstract colleague."""
    
    def __init__(self, mediator: Mediator | None = None) -> None:
        self._mediator = mediator


class ConcreteColleagueA(Colleague):
    def do_action(self) -> None:
        if self._mediator:
            self._mediator.notify(self, "Action A")


class ConcreteColleagueB(Colleague):
    def do_action(self) -> None:
        if self._mediator:
            self._mediator.notify(self, "Action B")


@dataclass
class Memento(Generic[T]):
    """Memento for state capture."""
    
    state: T
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_state(self) -> T:
        return self._state
    
    def get_timestamp(self) -> datetime:
        return self._timestamp


class Originator(Generic[T]):
    """Originator that creates mementos."""
    
    def __init__(self, state: T) -> None:
        self._state = state
    
    def get_state(self) -> T:
        return self._state
    
    def set_state(self, state: T) -> None:
        self._state = state
    
    def save(self) -> Memento[T]:
        return Memento(state=self._state)
    
    def restore(self, memento: Memento[T]) -> None:
        self._state = memento.get_state()


class Caretaker(Generic[T]):
    """Caretaker managing mementos."""
    
    def __init__(self, originator: Originator[T]) -> None:
        self._originator = originator
        self._mementos: list[Memento[T]] = []
    
    def backup(self) -> None:
        self._mementos.append(self._originator.save())
    
    def undo(self) -> bool:
        if not self._mementos:
            return False
        memento = self._mementos.pop()
        self._originator.restore(memento)
        return True


class Observer(ABC):
    """Abstract observer."""
    
    @abstractmethod
    def update(self, data: Any) -> None:
        pass


class Subject(ABC):
    """Subject for observer pattern."""
    
    def __init__(self) -> None:
        self._observers: list[Observer] = []
    
    def attach(self, observer: Observer) -> None:
        if observer not in self._observers:
            self._observers.append(observer)
    
    def detach(self, observer: Observer) -> None:
        self._observers.remove(observer)
    
    def notify(self, data: Any) -> None:
        for observer in self._observers:
            observer.update(data)


class ConcreteObserver(Observer):
    """Concrete observer."""
    
    def __init__(self, name: str) -> None:
        self._name = name
    
    def update(self, data: Any) -> None:
        print(f"Observer {self._name} received: {data}")


class EventEmitter(Subject):
    """Event emitter with observer pattern."""
    
    def emit(self, event: str, data: Any = None) -> None:
        self.notify({"event": event, "data": data})


class State(ABC):
    """Abstract state."""
    
    @abstractmethod
    def handle(self, context: Context) -> None:
        pass


class Context:
    """Context for state pattern."""
    
    def __init__(self, state: State) -> None:
        self._state = state
    
    @property
    def state(self) -> State:
        return self._state
    
    @state.setter
    def state(self, state: State) -> None:
        self._state = state
    
    def request(self) -> None:
        self._state.handle(self)


class ConcreteStateA(State):
    def handle(self, context: Context) -> None:
        print("StateA handling")
        context.state = ConcreteStateB()


class ConcreteStateB(State):
    def handle(self, context: Context) -> None:
        print("StateB handling")
        context.state = ConcreteStateA()


class Strategy(ABC):
    """Abstract strategy."""
    
    @abstractmethod
    def execute(self, data: Any) -> Any:
        pass


class ContextStrategy:
    """Context for strategy pattern."""
    
    def __init__(self, strategy: Strategy) -> None:
        self._strategy = strategy
    
    @property
    def strategy(self) -> Strategy:
        return self._strategy
    
    @strategy.setter
    def strategy(self, strategy: Strategy) -> None:
        self._strategy = strategy
    
    def execute_strategy(self, data: Any) -> Any:
        return self._strategy.execute(data)


class ConcreteStrategyA(Strategy):
    def execute(self, data: Any) -> Any:
        return f"StrategyA: {data}"


class ConcreteStrategyB(Strategy):
    def execute(self, data: Any) -> Any:
        return f"StrategyB: {data}"


class TemplateMethod(ABC):
    """Abstract template method."""
    
    def template_method(self) -> str:
        result = []
        result.append(self.step1())
        result.append(self.step2())
        result.append(self.step3())
        return " -> ".join(result)
    
    @abstractmethod
    def step1(self) -> str:
        pass
    
    @abstractmethod
    def step2(self) -> str:
        pass
    
    def step3(self) -> str:
        return "Step3 (default)"


class ConcreteTemplate(TemplateMethod):
    def step1(self) -> str:
        return "Step1"
    
    def step2(self) -> str:
        return "Step2"


class Visitor(ABC):
    """Abstract visitor."""
    
    @abstractmethod
    def visit_element_a(self, element: ElementA) -> Any:
        pass
    
    @abstractmethod
    def visit_element_b(self, element: ElementB) -> Any:
        pass


class Element(ABC):
    """Abstract element."""
    
    @abstractmethod
    def accept(self, visitor: Visitor) -> Any:
        pass


class ElementA(Element):
    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_element_a(self)
    
    def operation_a(self) -> str:
        return "ElementA"


class ElementB(Element):
    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit_element_b(self)
    
    def operation_b(self) -> str:
        return "ElementB"


class ConcreteVisitor(Visitor):
    def visit_element_a(self, element: ElementA) -> Any:
        return f"Visitor: {element.operation_a()}"
    
    def visit_element_b(self, element: ElementB) -> Any:
        return f"Visitor: {element.operation_b()}"


__all__ = [
    'Handler',
    'ConcreteHandlerA',
    'ConcreteHandlerB',
    'Command',
    'ConcreteCommand',
    'MacroCommand',
    'CommandInvoker',
    'Iterator',
    'ConcreteIterator',
    'ReverseIterator',
    'IterableCollection',
    'Mediator',
    'ConcreteMediator',
    'Colleague',
    'ConcreteColleagueA',
    'ConcreteColleagueB',
    'Memento',
    'Originator',
    'Caretaker',
    'Observer',
    'Subject',
    'ConcreteObserver',
    'EventEmitter',
    'State',
    'Context',
    'ConcreteStateA',
    'ConcreteStateB',
    'Strategy',
    'ContextStrategy',
    'ConcreteStrategyA',
    'ConcreteStrategyB',
    'TemplateMethod',
    'ConcreteTemplate',
    'Visitor',
    'Element',
    'ElementA',
    'ElementB',
    'ConcreteVisitor',
]