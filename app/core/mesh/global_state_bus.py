"""Near-Memory Mesh - Global State Bus for microsecond-level synchronization (Phase 12.3)."""
from __future__ import annotations

import threading
import time
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class GlobalStateBus:
    """Distributed shared memory for microsecond-level state synchronization.

    All modules write their current confidence scores and risk levels to a shared region.
    Other modules can read these values without event queue latency.
    """

    def __init__(self):
        self._shared_state: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._version: int = 0

    def write_state(self, module_id: str, state: dict[str, Any]) -> None:
        """Write module state to shared memory."""
        with self._lock:
            self._shared_state[module_id] = {
                "confidence": state.get("confidence", 0.0),
                "risk_level": state.get("risk_level", 0.0),
                "timestamp": time.monotonic_ns(),
                **state,
            }
            self._version += 1

    def read_state(self, module_id: str) -> dict[str, Any] | None:
        """Read module state from shared memory."""
        with self._lock:
            return self._shared_state.get(module_id)

    def read_all_states(self) -> dict[str, Any]:
        """Read all module states (atomic snapshot)."""
        with self._lock:
            return {mid: dict(state) for mid, state in self._shared_state.items()}

    def get_version(self) -> int:
        """Get current state version for change detection."""
        with self._lock:
            return self._version


_global_bus: GlobalStateBus | None = None


def get_global_state_bus() -> GlobalStateBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = GlobalStateBus()
    return _global_bus


__all__ = ["GlobalStateBus", "get_global_state_bus"]