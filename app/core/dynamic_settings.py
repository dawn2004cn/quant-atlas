"""Dynamic configuration management."""

import json
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Any


class DynamicSettings:
    """Settings manager supporting dynamic updates."""

    def __init__(self, config_path: str | Path):
        self._path = Path(config_path)
        self._settings: dict[str, Any] = {}
        self._observers: list[Callable[[dict[str, Any]], None]] = []
        self._lock = RLock()
        self.reload()

    def reload(self) -> None:
        """Reload settings from disk."""
        if self._path.exists():
            with self._lock:
                with open(self._path, encoding="utf-8") as f:
                    self._settings = json.load(f)
                for observer in self._observers:
                    observer(self._settings)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._settings.get(key, default)

    def subscribe(self, observer: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._observers.append(observer)
            # Initial callback
            observer(self._settings)
