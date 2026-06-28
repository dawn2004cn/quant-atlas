from __future__ import annotations
"""Memory data store for backtesting to eliminate redundant I/O."""

from collections import OrderedDict

import pandas as pd

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_int

logger = get_logger(__name__)


class MemoryDataStore:
    """A singleton-like in-memory store for backtest datasets."""

    def __init__(self, max_entries: int | None = None) -> None:
        self._cache: OrderedDict[str, pd.DataFrame] = OrderedDict()
        self._max_entries = max_entries or get_runtime_int("BACKTEST_MEMORY_STORE_MAX", 64)
        self._enabled = True

    def get(self, key: str) -> pd.DataFrame | None:
        if not self._enabled:
            return None
        frame = self._cache.get(key)
        if frame is None:
            return None
        self._cache.move_to_end(key)
        return frame

    def set(self, key: str, df: pd.DataFrame) -> None:
        if not self._enabled:
            return
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = df
        while len(self._cache) > self._max_entries:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug("MemoryDataStore evicted key=%s (max=%s)", evicted_key, self._max_entries)

    def clear(self) -> None:
        self._cache.clear()
        logger.info("MemoryDataStore cleared.")

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


# Global store
memory_store = MemoryDataStore()
