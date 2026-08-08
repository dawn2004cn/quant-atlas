"""Tick-level Data Support — real-time streaming, data lineage, cross-source alignment."""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TickRecord:
    """A single tick data point."""
    symbol: str
    market: str
    timestamp: str  # ISO format with microseconds
    price: float
    volume: int
    bid: float = 0.0
    ask: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    trade_flag: str = ""  # buy/sell/unknown
    source: str = ""


@dataclass
class DataLineageNode:
    """One node in the data lineage graph: tick → factor → signal → order."""
    node_id: str
    node_type: str  # tick / factor / signal / order
    symbol: str
    timestamp: str
    value: float
    parent_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossSourceAlignment:
    """Aligned data point from multiple sources."""
    symbol: str
    field: str  # close / open / high / low / volume
    timestamp: str
    values: dict[str, float]  # source_name → value
    consensus_value: float = 0.0
    max_deviation_pct: float = 0.0
    aligned: bool = True


class TickService:
    """Tick-level data ingestion, storage, and query."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._hot_store = root / "instance" / "tick_hot"
        self._hot_store.mkdir(parents=True, exist_ok=True)
        self._cold_store = root / "instance" / "tick_cold"
        self._cold_store.mkdir(parents=True, exist_ok=True)
        self._buffer: dict[str, deque[TickRecord]] = defaultdict(lambda: deque(maxlen=10000))
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._running = False

    def ingest_tick(self, tick: TickRecord):
        """Ingest a single tick record — hot path."""
        with self._lock:
            key = f"{tick.market}:{tick.symbol}"
            self._buffer[key].append(tick)
            # Notify subscribers
            for cb in self._subscribers.get(key, []):
                try:
                    cb(tick)
                except Exception as exc:
                    logger.warning("Tick subscriber error for %s: %s", key, exc)

    def ingest_batch(self, ticks: list[TickRecord]):
        """Ingest a batch of ticks."""
        for tick in ticks:
            self.ingest_tick(tick)

    def subscribe(self, symbol: str, market: str, callback: Callable):
        """Subscribe to real-time tick updates for a symbol."""
        key = f"{market}:{symbol}"
        with self._lock:
            self._subscribers[key].append(callback)
        logger.info("Tick subscriber added for %s", key)

    def get_recent_ticks(self, symbol: str, market: str, limit: int = 100) -> list[TickRecord]:
        """Get recent ticks from hot buffer."""
        key = f"{market}:{symbol}"
        with self._lock:
            buf = self._buffer.get(key, deque())
            return list(buf)[-limit:]

    def build_order_book(self, symbol: str, market: str) -> dict[str, Any]:
        """Build current order book snapshot from recent ticks."""
        ticks = self.get_recent_ticks(symbol, market, 1000)
        bids = [(t.bid, t.bid_size) for t in ticks if t.bid > 0]
        asks = [(t.ask, t.ask_size) for t in ticks if t.ask > 0]
        if not bids or not asks:
            return {"bids": [], "asks": [], "spread": 0}
        best_bid = max(b[0] for b in bids)
        best_ask = min(a[0] for a in asks)
        return {
            "bids": sorted(set(bids), key=lambda x: -x[0])[:10],
            "asks": sorted(set(asks), key=lambda x: x[0])[:10],
            "spread": round(best_ask - best_bid, 4),
            "mid_price": round((best_bid + best_ask) / 2, 4),
        }


class DataLineageService:
    """Full data lineage: tick → factor → signal → order."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "data_lineage.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)
        self._nodes: dict[str, DataLineageNode] = {}

    def record_node(self, node: DataLineageNode):
        """Record a lineage node."""
        self._nodes[node.node_id] = node
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(node.__dict__, ensure_ascii=False) + "\n")

    def trace_order(self, order_id: str) -> list[DataLineageNode]:
        """Trace an order back through the lineage graph."""
        nodes = []
        queue = [order_id]
        seen = set()
        while queue:
            nid = queue.pop(0)
            if nid in seen:
                continue
            seen.add(nid)
            node = self._nodes.get(nid)
            if node:
                nodes.append(node)
                queue.extend(node.parent_ids)
        return nodes

    def get_lineage_graph(self, order_id: str) -> dict[str, Any]:
        """Get full lineage graph for visualization."""
        nodes = self.trace_order(order_id)
        return {
            "nodes": [{"id": n.node_id, "type": n.node_type, "symbol": n.symbol, "value": n.value} for n in nodes],
            "edges": [(n.node_id, pid) for n in nodes for pid in n.parent_ids],
        }


class CrossSourceAlignmentService:
    """Multi-source data alignment and timestamp correction."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "cross_source_alignments.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def align(self, symbol: str, field: str, timestamp: str, source_values: dict[str, float]) -> CrossSourceAlignment:
        """Align values from multiple sources for the same data point."""
        values = [v for v in source_values.values() if v > 0]
        if not values:
            return CrossSourceAlignment(
                symbol=symbol, field=field, timestamp=timestamp,
                values=source_values, aligned=False,
            )

        consensus = sum(values) / len(values)
        deviations = [abs(v - consensus) / consensus * 100 for v in values]
        max_dev = max(deviations) if deviations else 0

        alignment = CrossSourceAlignment(
            symbol=symbol,
            field=field,
            timestamp=timestamp,
            values=source_values,
            consensus_value=round(consensus, 6),
            max_deviation_pct=round(max_dev, 4),
            aligned=max_dev < 0.5,  # < 0.5% deviation = aligned
        )
        self._persist(alignment)
        return alignment

    def correct_timestamp(self, source_ts: str, source_latency_ms: float) -> str:
        """Correct a timestamp based on known source latency."""
        dt = datetime.fromisoformat(source_ts.replace("Z", "+00:00"))
        corrected = dt.timestamp() - source_latency_ms / 1000
        return datetime.fromtimestamp(corrected, tz=timezone.utc).isoformat()

    def _persist(self, alignment: CrossSourceAlignment):
        try:
            with self._store.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(alignment.__dict__, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Alignment persist failed: %s", exc)
