from __future__ import annotations
"""Memory optimization using Apache Arrow for zero-copy data sharing.

This implements the "Data Mesh" from quant_plan.md:
- Arrow-based zero-copy sharing between components
- Shared memory pools for real-time market data
- Efficient serialization for IPC
"""


import io
import json
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime


import logging
logger = logging.getLogger(__name__)
class ArrowMemoryPool:
    """Memory pool using Apache Arrow for zero-copy data sharing."""

    def __init__(self):
        self._buffers: dict[str, Any] = {}

    def create_table(self, name: str, data: list[dict]) -> bool:
        """Create an Arrow table from list of dicts."""
        try:
            import pyarrow as pa

            if not data:
                return False

            fields = []
            for key in data[0].keys():
                sample = data[0][key]
                if isinstance(sample, (int, bool)):
                    pa_type = pa.int64()
                elif isinstance(sample, float):
                    pa_type = pa.float64()
                else:
                    pa_type = pa.string()
                fields.append((key, pa_type))

            schema = pa.schema(fields)

            columns = {key: [] for key in data[0].keys()}

            for row in data:
                for key in columns:
                    val = row.get(key)
                    if val is None:
                        val = 0 if key in [k for k, t in fields if t == pa.int64()] else 0.0
                    columns[key].append(val)

            arrays = [pa.array(columns[key]) for key in columns]
            table = pa.Table.from_arrays(arrays, schema=schema)

            self._buffers[name] = table

            return True
        except ImportError:
            return self._create_fallback(name, data)

    def _create_fallback(self, name: str, data: list[dict]) -> bool:
        """Fallback to pickle if Arrow not available."""
        self._buffers[name] = data
        return True

    def get_table(self, name: str) -> Any:
        """Get the Arrow table by name."""
        return self._buffers.get(name)

    def get_as_pandas(self, name: str) -> Any:
        """Get data as pandas DataFrame (zero-copy if possible)."""
        table = self.get_table(name)
        if table is None:
            return None

        try:
            import pyarrow as pa

            if isinstance(table, pa.Table):
                return table.to_pandas()
        except ImportError as e:
            logger.warning("arrow_pool.py.get_as_pandas: %s", e)

        import pandas as pd
        return pd.DataFrame(table) if isinstance(table, list) else None

    def to_bytes(self, name: str) -> bytes:
        """Serialize table to bytes for IPC."""
        table = self.get_table(name)
        if table is None:
            return b""

        try:
            import pyarrow as pa

            if isinstance(table, pa.Table):
                return table.serialize()
        except ImportError as e:
            logger.warning("arrow_pool.py.to_bytes: %s", e)

        return json.dumps(table, ensure_ascii=False, default=str).encode("utf-8")

    def from_bytes(self, name: str, data: bytes) -> bool:
        """Deserialize table from bytes."""
        try:
            import pyarrow as pa

            table = pa.deserialize(data)
            self._buffers[name] = table
            return True
        except ImportError:
            return self._from_bytes_fallback(name, data)

    def _from_bytes_fallback(self, name: str, data: bytes) -> bool:
        self._buffers[name] = json.loads(data.decode("utf-8"))
        return True

    def clear(self, name: str | None = None) -> None:
        """Clear buffers."""
        if name:
            self._buffers.pop(name, None)
        else:
            self._buffers.clear()

    def list_tables(self) -> list[str]:
        """List all table names."""
        return list(self._buffers.keys())


class SharedMemoryManager:
    """Manager for shared memory pools across processes."""

    def __init__(self, pool_name: str = "quant_atlas"):
        self._pool_name = pool_name
        self._pools: dict[str, ArrowMemoryPool] = {}

    def get_pool(self, name: str | None = None) -> ArrowMemoryPool:
        """Get or create a memory pool."""
        pool_id = name or "default"
        if pool_id not in self._pools:
            self._pools[pool_id] = ArrowMemoryPool()
        return self._pools[pool_id]

    def create_shared_table(
        self,
        pool_name: str,
        table_name: str,
        data: list[dict],
    ) -> bool:
        """Create a shared table in the pool."""
        pool = self.get_pool(pool_name)
        return pool.create_table(table_name, data)

    def read_shared_table(self, pool_name: str, table_name: str) -> Any:
        """Read a shared table."""
        pool = self.get_pool(pool_name)
        return pool.get_table(table_name)


_global_manager: SharedMemoryManager | None = None


def get_global_memory_manager() -> SharedMemoryManager:
    """Get the global shared memory manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = SharedMemoryManager()
    return _global_manager


@dataclass
class StreamingDataUpdate:
    """Single data update for streaming feeds."""
    symbol: str
    field: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "market"


class StreamingDataFeed:
    """Real-time streaming data feed using Arrow.

    Enables efficient pub/sub for real-time market data
    with minimal memory overhead.
    """

    def __init__(self, name: str):
        self.name = name
        self._subscribers: dict[str, list[callable]] = {}
        self._latest: dict[str, dict[str, float]] = {}
        self._history: list[StreamingDataUpdate] = []
        self._max_history = 10000

    def subscribe(self, symbol: str, callback: callable) -> None:
        """Subscribe to updates for a symbol."""
        if symbol not in self._subscribers:
            self._subscribers[symbol] = []
        self._subscribers[symbol].append(callback)

    def publish(self, update: StreamingDataUpdate) -> None:
        """Publish a data update."""
        if update.symbol not in self._latest:
            self._latest[update.symbol] = {}
        self._latest[update.symbol][update.field] = update.value

        self._history.append(update)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        for callback in self._subscribers.get(update.symbol, []):
            try:
                callback(update)
            except Exception as e:
                logger.warning("arrow_pool.py.publish: %s", e)

    def get_latest(self, symbol: str, field: str | None = None) -> dict | float:
        """Get latest value(s) for a symbol."""
        if symbol not in self._latest:
            return {} if field is None else 0.0

        if field:
            return self._latest[symbol].get(field, 0.0)
        return self._latest[symbol]

    def get_history(self, symbol: str, field: str, limit: int = 100) -> list[float]:
        """Get historical values for a symbol/field."""
        values = []
        for update in reversed(self._history):
            if update.symbol == symbol and update.field == field:
                values.append(update.value)
                if len(values) >= limit:
                    break
        return values


_streaming_feeds: dict[str, StreamingDataFeed] = {}


def get_streaming_feed(name: str = "default") -> StreamingDataFeed:
    """Get or create a streaming data feed."""
    if name not in _streaming_feeds:
        _streaming_feeds[name] = StreamingDataFeed(name)
    return _streaming_feeds[name]