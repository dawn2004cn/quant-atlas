from __future__ import annotations

"""Observer pattern for state transitions."""

from abc import ABC, abstractmethod
from typing import Any


class StateObserver(ABC):
    """Observer interface for state changes."""
    @abstractmethod
    def on_transition(self, state_id: str, old_state: str, new_state: str, context: dict[str, Any]) -> None:
        """Called on state transition."""
        pass

class ObservableStateMachine:
    """A wrapper or base to support state observers."""
    def __init__(self):
        self._observers: list[StateObserver] = []

    def attach(self, observer: StateObserver):
        self._observers.append(observer)

    def notify(self, state_id: str, old_state: str, new_state: str, context: dict[str, Any]):
        for observer in self._observers:
            observer.on_transition(state_id, old_state, new_state, context)
