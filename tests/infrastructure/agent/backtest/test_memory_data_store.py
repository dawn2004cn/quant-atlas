"""MemoryDataStore LRU eviction tests."""
from __future__ import annotations

import pandas as pd

from app.infrastructure.agent.backtest.data_store import MemoryDataStore


def test_memory_data_store_evicts_oldest_when_full():
    store = MemoryDataStore(max_entries=2)
    store.set("a", pd.DataFrame({"x": [1]}))
    store.set("b", pd.DataFrame({"x": [2]}))
    store.set("c", pd.DataFrame({"x": [3]}))

    assert store.size == 2
    assert store.get("a") is None
    assert store.get("b") is not None
    assert store.get("c") is not None


def test_memory_data_store_touch_moves_entry_to_recent():
    store = MemoryDataStore(max_entries=2)
    store.set("a", pd.DataFrame({"x": [1]}))
    store.set("b", pd.DataFrame({"x": [2]}))
    assert store.get("a") is not None
    store.set("c", pd.DataFrame({"x": [3]}))

    assert store.get("a") is not None
    assert store.get("b") is None
