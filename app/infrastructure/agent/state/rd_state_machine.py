from __future__ import annotations
"""Concrete State Machine for RDAgent workflow."""

import json
from pathlib import Path
from typing import Any
from app.domain.state.machine import IStateMachine, IStatePersistence

class RDStatePersistence(IStatePersistence):
    """File-based state persistence for RDAgent runs."""
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, state_id: str, state: str, context: dict[str, Any]) -> None:
        path = self.storage_dir / f"{state_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump({"state": state, "context": context}, f)

    def load_snapshot(self, state_id: str) -> dict[str, Any] | None:
        path = self.storage_dir / f"{state_id}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

from app.domain.state.observer import ObservableStateMachine

class RDStateMachine(IStateMachine[str, dict[str, Any]], ObservableStateMachine):
    """Concrete FSM for RDAgent Run cycles with Observability."""

    def __init__(self, state_id: str, persistence: RDStatePersistence):
        super().__init__() # Initialize ObservableStateMachine
        self.state_id = state_id
        self.persistence = persistence
        snapshot = self.persistence.load_snapshot(state_id)
        self._current_state = snapshot["state"] if snapshot else "INITIALIZING"
        self._context = snapshot["context"] if snapshot else {}

    def transition_to(self, new_state: str, context: dict[str, Any]) -> None:
        old_state = self._current_state
        self._current_state = new_state
        self._context.update(context)
        self.persistence.save_snapshot(self.state_id, new_state, self._context)
        self.notify(self.state_id, old_state, new_state, self._context)

    def get_current_state(self) -> str:
        return self._current_state
