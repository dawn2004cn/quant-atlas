from __future__ import annotations

"""Redis Stream Signal Bus for Low-Latency Signal Processing.

Implements from strategy_plan2.md:
- Real-time signal streaming via Redis Streams
- Consumer groups for parallel processing
- Microsecond-level signal latency

Usage:
    bus = SignalBus()
    bus.publish_signal(signal)
    bus.subscribe_consumer_group("executor_group", ["worker1", "worker2"])
"""


from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StreamSignal:
    """Signal message for stream."""
    signal_id: str
    strategy_name: str
    manager_id: str
    symbol: str
    direction: str
    quantity: int
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None


class SignalBus:
    """Redis Stream-based signal bus."""

    STREAM_KEY = "signals:stream"
    SIGNAL_GROUP = "signal_processors"
    CONSUMER_PREFIX = "consumer"

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._handlers: dict[str, Callable] = {}
        self._pending_signals: list[StreamSignal] = []

    def publish_signal(self, signal: StreamSignal) -> str | None:
        """Publish signal to stream."""
        signal.signal_id = signal.signal_id or str(uuid4())[:8]

        message = {
            "signal_id": signal.signal_id,
            "strategy_name": signal.strategy_name,
            "manager_id": signal.manager_id,
            "symbol": signal.symbol,
            "direction": signal.direction,
            "quantity": signal.quantity,
            "price": signal.price,
            "timestamp": signal.timestamp.isoformat(),
            "trace_id": signal.trace_id or "",
            **signal.metadata,
        }

        if self._redis:
            try:
                self._redis.xadd(self.STREAM_KEY, message)
                logger.info(f"Published signal {signal.signal_id} to stream")
                return signal.signal_id
            except Exception as e:
                logger.error(f"Failed to publish signal: {e}")

        self._pending_signals.append(signal)
        logger.warning(f"Queued signal {signal.signal_id} (no Redis)")
        return signal.signal_id

    def subscribe_consumer_group(self, group_name: str, consumers: list[str]) -> bool:
        """Create consumer group for parallel processing."""
        if not self._redis:
            logger.warning("No Redis client, skipping group creation")
            return False

        try:
            self._redis.xgroup_create(self.STREAM_KEY, group_name, id="0", mkstream=True)
            for i, consumer in enumerate(consumers):
                self._redis.sadd(f"{group_name}:consumers", f"{consumer}_{i}")
            logger.info(f"Created consumer group {group_name} with {len(consumers)} consumers")
            return True
        except Exception as e:
            logger.error(f"Failed to create consumer group: {e}")
            return False

    def consume_signals(self, group_name: str, consumer_id: str, count: int = 10, block_ms: int = 1000) -> list[StreamSignal]:
        """Consume signals from stream."""
        if not self._redis:
            return self._pending_signals[:count]

        try:
            messages = self._redis.xread(
                {self.STREAM_KEY: None},
                count=count,
                block=block_ms,
                group=group_name,
                consumer=consumer_id,
            )

            signals = []
            for _stream_name, stream_messages in messages.items():
                for msg_id, msg in stream_messages:
                    signal = self._parse_message(msg_id, msg)
                    signals.append(signal)

            return signals
        except Exception as e:
            logger.error(f"Failed to consume signals: {e}")
            return []

    def ack_signal(self, group_name: str, signal_id: str) -> bool:
        """Acknowledge signal processing."""
        if not self._redis:
            return True

        try:
            self._redis.xack(self.STREAM_KEY, group_name, signal_id)
            return True
        except Exception as e:
            logger.error(f"Failed to ack signal: {e}")
            return False

    def get_stream_info(self) -> dict[str, Any]:
        """Get stream info."""
        if not self._redis:
            return {"pending": len(self._pending_signals), "connected": False}

        try:
            info = self._redis.xinfo_stream(self.STREAM_KEY)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry-id"),
                "last_entry": info.get("last-entry-id"),
                "connected": True,
            }
        except Exception as e:
            logger.error(f"Failed to get stream info: {e}")
            return {"connected": False}

    def register_handler(self, handler_name: str, handler: Callable) -> None:
        """Register signal handler."""
        self._handlers[handler_name] = handler
        logger.info(f"Registered handler {handler_name}")

    def process_pending(self) -> int:
        """Process pending signals with handlers."""
        processed = 0
        for signal in self._pending_signals[:]:
            for handler in self._handlers.values():
                try:
                    handler(signal)
                    processed += 1
                except Exception as e:
                    logger.error(f"Handler error: {e}")

        self._pending_signals.clear()
        return processed

    def _parse_message(self, msg_id: bytes | str, msg: dict) -> StreamSignal:
        """Parse stream message to signal."""
        ts = msg.get("timestamp", datetime.now().isoformat())
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        return StreamSignal(
            signal_id=msg.get("signal_id", ""),
            strategy_name=msg.get("strategy_name", ""),
            manager_id=msg.get("manager_id", ""),
            symbol=msg.get("symbol", ""),
            direction=msg.get("direction", ""),
            quantity=int(msg.get("quantity", 0)),
            price=float(msg.get("price", 0.0)),
            timestamp=ts,
            trace_id=msg.get("trace_id") or None,
        )


class SignalBusBridge:
    """Bridge between signal coordinator and signal bus."""

    def __init__(self, bus: SignalBus = None):
        self._bus = bus or SignalBus()

    def broadcast_signals(self, signals: list) -> int:
        """Broadcast signals from coordinator to bus."""
        count = 0
        for signal in signals:
            stream_signal = StreamSignal(
                signal_id=str(uuid4())[:8],
                strategy_name=signal.strategy_name,
                manager_id=signal.metadata.get("manager_id", "unknown"),
                symbol=signal.symbol,
                direction=signal.direction,
                quantity=int(signal.metadata.get("quantity", 0)),
                metadata=signal.metadata,
            )
            if self._bus.publish_signal(stream_signal):
                count += 1

        logger.info(f"Broadcast {count} signals to stream")
        return count


_global_signal_bus: SignalBus | None = None


def get_signal_bus() -> SignalBus:
    """Get global signal bus."""
    global _global_signal_bus
    if _global_signal_bus is None:
        _global_signal_bus = SignalBus()
    return _global_signal_bus
