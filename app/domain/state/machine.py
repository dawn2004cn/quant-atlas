from __future__ import annotations

"""Generic State Machine interfaces for fault-tolerant workflows."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

TState = TypeVar("TState", bound=str)
TContext = TypeVar("TContext")

class IStateMachine(ABC, Generic[TState, TContext]):
    """Generic State Machine contract."""

    @abstractmethod
    def transition_to(self, new_state: TState, context: TContext) -> None:
        """Transition to a new state and update context."""
        raise NotImplementedError

    @abstractmethod
    def get_current_state(self) -> TState:
        """Get current state."""
        raise NotImplementedError

class IStatePersistence(ABC):
    """Contract for state snapshotting."""

    @abstractmethod
    def save_snapshot(self, state_id: str, state: str, context: dict[str, Any]) -> None:
        """Save a state snapshot."""
        raise NotImplementedError

    @abstractmethod
    def load_snapshot(self, state_id: str) -> dict[str, Any] | None:
        """Load a state snapshot."""
        raise NotImplementedError
