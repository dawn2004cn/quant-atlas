from __future__ import annotations

"""Internal Event Bus for decoupled service communication.

This is the system's neural hub.  Events flow between services, workflows,
and WebSocket adapters without direct coupling.

Persistence: Optional Redis Streams backend (RedisStreamBackend) records
every published event so subscribers can replay missed events after a
service restart.
"""


import json
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_websocket_enabled = False
_broadcast_func: Callable[[str, Any], int] | None = None

# Priority tiers for Quant Atlas 4.0 arbitration / truth events.
EVENT_PRIORITY_LOW = 0
EVENT_PRIORITY_MEDIUM = 10
EVENT_PRIORITY_NORMAL = 10
EVENT_PRIORITY_HIGH = 50
EVENT_PRIORITY_CRITICAL = 100


@dataclass
class _HandlerRegistration:
    priority: int
    handler: Callable[[Event], None]


@dataclass
class Event:
    """Base event class."""
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    priority: int = EVENT_PRIORITY_NORMAL
    ttl_seconds: float | None = None

    def is_expired(self, *, now: datetime | None = None) -> bool:
        if self.ttl_seconds is None:
            return False
        ref = now or datetime.now()
        return (ref - self.timestamp).total_seconds() > self.ttl_seconds

    @property
    def expires_at(self) -> datetime | None:
        if self.ttl_seconds is None:
            return None
        return self.timestamp + timedelta(seconds=self.ttl_seconds)


@dataclass
class EventEnvelope:
    event: str
    timestamp: str
    source: str
    priority: int
    ttl_seconds: float | None
    expires_at: str | None
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "timestamp": self.timestamp,
            "source": self.source,
            "priority": self.priority,
            "ttl_seconds": self.ttl_seconds,
            "expires_at": self.expires_at,
            "data": self.data,
        }


class EventSchemaError(ValueError):
    """Raised when an event envelope cannot be decoded."""


# ── lifecycle events (service / workflow) ────────────────────────────────

@dataclass
class ServiceStartedEvent(Event):
    """Emitted when a service is first resolved by ServiceRegistry."""
    service_name: str = ""
    scope: str = "singleton"


@dataclass
class ServiceStoppedEvent(Event):
    """Emitted during graceful shutdown."""
    service_name: str = ""


@dataclass
class WorkflowCompletedEvent(Event):
    """Emitted when a workflow finishes."""
    workflow_id: str = ""
    workflow_type: str = ""
    state: str = ""
    evidence_count: int = 0
    step_metrics: dict = field(default_factory=dict)


@dataclass
class CapabilityExecutedEvent(Event):
    """Emitted when a tool capability is invoked."""
    capability_name: str = ""
    success: bool = True
    duration_ms: float = 0.0


# ── domain events ────────────────────────────────────────────────────────

@dataclass
class TradeExecutedEvent(Event):
    """Event emitted when a trade is executed (requires provenance_id for audit lineage)."""
    user_id: str = ""
    symbol: str = ""
    action: str = ""
    quantity: float = 0
    price: float = 0
    amount: float = 0
    provenance_id: str = ""
    market: str = "CN"


@dataclass
class PositionChangedEvent(Event):
    """Event emitted when a position changes."""
    user_id: str = ""
    symbol: str = ""
    quantity_change: float = 0
    new_quantity: float = 0


@dataclass
class MarketDataUpdatedEvent(Event):
    """Event emitted when market data is updated."""
    symbol: str = ""
    market: str = ""


# ── market regime events ────────────────────────────────────────────────

@dataclass
class MarketRegimeChangedEvent(Event):
    """Emitted when market regime changes (bull/bear/sideways/crash/recovery)."""
    previous_regime: str = ""
    new_regime: str = ""
    market: str = "CN"
    confidence: float = 0.0
    trigger_reason: str = ""
    priority: int = EVENT_PRIORITY_HIGH
    ttl_seconds: float | None = 3600.0


# ── Quant Atlas 4.0 arbitration / truth events ───────────────────────────

@dataclass
class DebateRoundEvent(Event):
    """One round of multi-agent debate published to the bus."""
    symbol: str = ""
    market: str = ""
    round_num: int = 0
    agent_role: str = ""
    stance: str = ""
    evidence_summary: str = ""
    confidence: float = 0.0
    priority: int = EVENT_PRIORITY_NORMAL
    ttl_seconds: float | None = 300.0


@dataclass
class TruthDeviationEvent(Event):
    """Multi-source price/reconciliation deviation exceeds threshold."""
    symbol: str = ""
    market: str = ""
    field: str = ""
    source_a: str = ""
    source_b: str = ""
    value_a: float | None = None
    value_b: float | None = None
    diff_pct: float | None = None
    threshold_pct: float = 0.5
    priority: int = EVENT_PRIORITY_CRITICAL
    ttl_seconds: float | None = 600.0


@dataclass
class AnalysisStaleEvent(Event):
    """Mark downstream AI analysis as pending verification."""
    symbol: str = ""
    market: str = ""
    reason: str = ""
    trigger_event: str = "TruthDeviationEvent"
    priority: int = EVENT_PRIORITY_HIGH
    ttl_seconds: float | None = 3600.0


# ── Quant Atlas 5.0 intent-driven orchestration ───────────────────────────

@dataclass
class ArbiterConsensusEvent(Event):
    """Arbiter reached a weighted or LLM consensus verdict."""
    provenance_id: str = ""
    symbol: str = ""
    market: str = ""
    verdict: str = ""
    confidence: float = 0.0
    mode: str = "heuristic"
    rounds_used: int = 0
    priority: int = EVENT_PRIORITY_HIGH
    ttl_seconds: float | None = 1800.0


@dataclass
class CrossTeamSiteAlertEvent(Event):
    """Emitted when multiple teams reach the same arbiter verdict on a symbol."""
    alert_id: str = ""
    symbol: str = ""
    market: str = "CN"
    verdict: str = ""
    team_count: int = 0
    avg_confidence: float = 0.0
    title: str = ""
    message: str = ""
    level: str = "info"
    room: str = "alerts"
    priority: int = EVENT_PRIORITY_HIGH
    ttl_seconds: float | None = 7200.0


@dataclass
class MetaArbiterActivatedEvent(Event):
    """Site-level meta-arbitration when cross-team consensus threshold is met."""
    activation_id: str = ""
    symbol: str = ""
    market: str = "CN"
    meta_verdict: str = ""
    meta_confidence: float = 0.0
    team_count: int = 0
    unanimous: bool = False
    rationale: str = ""
    room: str = "alerts"
    priority: int = EVENT_PRIORITY_HIGH
    ttl_seconds: float | None = 7200.0


@dataclass
class CorrectionIntentEvent(Event):
    """Arbiter requests trade-plan / strategy parameter correction."""
    intent_id: str = ""
    provenance_id: str = ""
    symbol: str = ""
    market: str = ""
    change_type: str = ""
    parameter_patch: dict = field(default_factory=dict)
    confidence: float = 0.0
    rationale: str = ""
    priority: int = EVENT_PRIORITY_HIGH
    ttl_seconds: float | None = 3600.0


@dataclass
class WatchlistAnomalyDetectedEvent(Event):
    """Emitted when watchlist agent detects an anomaly."""
    symbol: str = ""
    market: str = "CN"
    anomaly_type: str = ""
    severity: str = "info"
    score: float = 0.0
    message: str = ""
    priority: int = EVENT_PRIORITY_MEDIUM
    ttl_seconds: float | None = 1800.0


@dataclass
class MeshForwardedEvent(Event):
    """Remote mesh envelope re-injected into the local EventBus."""
    original_event: str = ""
    origin_node_id: str = ""
    origin_region: str = ""
    envelope_id: str = ""
    payload: dict = field(default_factory=dict)
    priority: int = EVENT_PRIORITY_NORMAL


@dataclass
class ApplicationEventForwardedEvent(Event):
    """Application-layer EventBus event forwarded to core bus with payload preserved."""
    app_event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = EVENT_PRIORITY_NORMAL


_EVENT_TYPES: dict[str, type[Event]] = {
    cls.__name__: cls
    for cls in (
        Event,
        ServiceStartedEvent,
        ServiceStoppedEvent,
        WorkflowCompletedEvent,
        CapabilityExecutedEvent,
        TradeExecutedEvent,
        PositionChangedEvent,
        MarketDataUpdatedEvent,
        MarketRegimeChangedEvent,
        DebateRoundEvent,
        TruthDeviationEvent,
        AnalysisStaleEvent,
        ArbiterConsensusEvent,
        CrossTeamSiteAlertEvent,
        MetaArbiterActivatedEvent,
        CorrectionIntentEvent,
        WatchlistAnomalyDetectedEvent,
        MeshForwardedEvent,
        ApplicationEventForwardedEvent,
    )
}


def event_schema(event_type: type[Event]) -> dict[str, Any]:
    if event_type not in _EVENT_TYPES.values():
        raise EventSchemaError(f"unknown_event_type:{event_type.__name__}")

    hints = getattr(event_type, "__annotations__", {})
    return {
        "event": event_type.__name__,
        "timestamp": "ISO-8601 datetime",
        "source": "string",
        "priority": "integer",
        "ttl_seconds": "float or null",
        "expires_at": "ISO-8601 datetime or null",
        "data": {
            name: _type_name(hints.get(name, Any))
            for name in (field_.name for field_ in fields(event_type))
            if name not in ("timestamp", "source", "priority", "ttl_seconds")
        },
    }


def event_to_envelope(event: Event) -> EventEnvelope:
    if not isinstance(event, Event):
        raise EventSchemaError("event_must_be_Event_instance")

    expires = event.expires_at
    return EventEnvelope(
        event=event.__class__.__name__,
        timestamp=event.timestamp.isoformat(),
        source=event.source,
        priority=event.priority,
        ttl_seconds=event.ttl_seconds,
        expires_at=expires.isoformat() if expires else None,
        data=_event_data(event),
    )


def event_from_envelope(envelope: dict[str, Any]) -> Event:
    required = ("event", "timestamp", "source", "priority", "ttl_seconds", "data")
    missing = [name for name in required if name not in envelope]
    if missing:
        raise EventSchemaError("missing_envelope_fields:" + ",".join(missing))

    event_name = envelope.get("event")
    event_type = _EVENT_TYPES.get(event_name)
    if event_type is None:
        raise EventSchemaError(f"unknown_event:{event_name}")

    data = envelope.get("data")
    if not isinstance(data, dict):
        raise EventSchemaError("event_data_must_be_object")

    kwargs = dict(data)
    kwargs.update(
        timestamp=_parse_datetime(envelope.get("timestamp")),
        source=str(envelope.get("source") or ""),
        priority=int(envelope.get("priority") or EVENT_PRIORITY_NORMAL),
        ttl_seconds=envelope.get("ttl_seconds"),
    )
    return event_type(**kwargs)


def event_to_json(event: Event) -> str:
    return json.dumps(event_to_envelope(event).to_dict(), ensure_ascii=False, sort_keys=True)


def event_from_json(payload: str | bytes) -> Event:
    try:
        envelope = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise EventSchemaError("invalid_event_json") from exc
    if not isinstance(envelope, dict):
        raise EventSchemaError("event_json_must_be_object")
    return event_from_envelope(envelope)


def _event_data(event: Event) -> dict[str, Any]:
    if not is_dataclass(event):
        raise EventSchemaError("event_must_be_dataclass")
    return {
        field_.name: _serializable_value(getattr(event, field_.name))
        for field_ in fields(event.__class__)
        if field_.name not in ("timestamp", "source", "priority", "ttl_seconds")
    }


def _serializable_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {field_.name: _serializable_value(getattr(value, field_.name)) for field_ in fields(value)}
    if isinstance(value, dict):
        return {str(key): _serializable_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable_value(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise EventSchemaError("timestamp_must_be_iso_string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise EventSchemaError("invalid_timestamp") from exc


def _type_name(value: Any) -> str:
    if isinstance(value, str):
        return value
    return getattr(value, "__name__", str(value))


class RedisStreamBackend:
    """Persist events to Redis Streams for durability and replay.

    Each event type gets its own stream key: ``eventbus:{event_name}``.
    Consumer groups let subscribers track their read position independently,
    so a restart doesn't lose unprocessed events.
    """

    def __init__(self, redis_url: str, stream_maxlen: int = 10_000):
        self._redis_url = redis_url
        self._stream_maxlen = stream_maxlen
        self._client: Any = None
        self._lock = threading.RLock()

    def _get_client(self):
        if self._client is None:
            from app.infrastructure.redis_client import RedisClientPool
            pool = RedisClientPool.get(self._redis_url)
            self._client = pool.binary_client
        return self._client

    def save(self, event: Event) -> None:
        """Persist one event to its Redis stream."""
        try:
            js = event_to_json(event)
            stream = f"eventbus:{event.__class__.__name__}"
            self._get_client().xadd(
                stream,
                {"payload": js},
                maxlen=self._stream_maxlen,
                approximate=True,
            )
        except Exception as exc:
            logger.warning("RedisStreamBackend.save failed for %s: %s", event.__class__.__name__, exc)

    def ensure_consumer_group(self, event_type: type[Event], group: str = "default") -> None:
        """Create consumer group for an event type (idempotent)."""
        try:
            stream = f"eventbus:{event_type.__name__}"
            client = self._get_client()
            try:
                client.xgroup_create(stream, group, id="0", mkstream=True)
            except Exception:
                pass  # group already exists
        except Exception as exc:
            logger.warning("RedisStreamBackend.ensure_group failed for %s: %s", event_type.__name__, exc)

    def replay(self, event_type: type[Event], group: str = "default", consumer: str = "replay", count: int = 100) -> list[Event]:
        """Read unacknowledged events for a consumer group."""
        try:
            stream = f"eventbus:{event_type.__name__}"
            client = self._get_client()
            self.ensure_consumer_group(event_type, group)
            raw = client.xreadgroup(group, consumer, {stream: ">"}, count=count, block=1000)
            events: list[Event] = []
            for _stream_name, messages in raw:
                for _msg_id, msg_data in messages:
                    try:
                        evt = event_from_json(msg_data[b"payload"])
                        events.append(evt)
                    except Exception:
                        continue
            return events
        except Exception as exc:
            logger.warning("RedisStreamBackend.replay failed for %s: %s", event_type.__name__, exc)
            return []

    def acknowledge(self, event_type: type[Event], group: str = "default", event_ids: list[str] | None = None) -> None:
        """Acknowledge processed events so they are not replayed."""
        if not event_ids:
            return
        try:
            stream = f"eventbus:{event_type.__name__}"
            client = self._get_client()
            client.xack(stream, group, *event_ids)
        except Exception as exc:
            logger.warning("RedisStreamBackend.ack failed: %s", exc)

    def pending_count(self, event_type: type[Event], group: str = "default") -> int:
        """Return the number of pending (unacknowledged) events."""
        try:
            stream = f"eventbus:{event_type.__name__}"
            client = self._get_client()
            info = client.xpending(stream, group)
            return info.get("pending", 0) if isinstance(info, dict) else 0
        except Exception:
            return 0

    @property
    def is_connected(self) -> bool:
        try:
            return self._get_client().ping() if self._client is not None else False
        except Exception:
            return False


class EventBus:
    """In-memory event bus for pub/sub communication between services.

    Optionally backed by Redis Streams for durable persistence and replay.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subscribers: dict[str, list[_HandlerRegistration]] = {}
                cls._instance._recent_events = deque(maxlen=200)
                cls._instance._handler_failures = deque(maxlen=100)
                cls._instance._sub_lock = threading.Lock()
                cls._instance._redis_backend: RedisStreamBackend | None = None
            return cls._instance

    def set_redis_backend(self, backend: RedisStreamBackend) -> None:
        self._redis_backend = backend

    def subscribe(
        self,
        event_type: type[Event],
        handler: Callable[[Event], None],
        *,
        priority: int = 0,
    ) -> None:
        """Subscribe to a specific event type (higher handler priority runs first)."""
        event_name = event_type.__name__
        with self._sub_lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            existing = [reg.handler for reg in self._subscribers[event_name]]
            if handler not in existing:
                self._subscribers[event_name].append(
                    _HandlerRegistration(priority=priority, handler=handler)
                )
                self._subscribers[event_name].sort(key=lambda r: r.priority, reverse=True)
                logger.debug(f"Subscribed {handler.__name__} to {event_name} (priority={priority})")

    def unsubscribe(self, event_type: type[Event], handler: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type."""
        event_name = event_type.__name__
        with self._sub_lock:
            if event_name in self._subscribers:
                before = len(self._subscribers[event_name])
                self._subscribers[event_name] = [
                    reg for reg in self._subscribers[event_name] if reg.handler is not handler
                ]
                if len(self._subscribers[event_name]) < before:
                    logger.debug(f"Unsubscribed {handler.__name__} from {event_name}")

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers and optionally to WebSocket."""
        if event.is_expired():
            logger.debug(
                "Dropped expired event %s (ttl=%s)",
                event.__class__.__name__,
                event.ttl_seconds,
            )
            return

        event_name = event.__class__.__name__
        self._recent_events.appendleft(self._event_to_dict(event))

        # Persist to Redis Streams if available
        if self._redis_backend is not None:
            self._redis_backend.save(event)

        with self._sub_lock:
            registrations = list(self._subscribers.get(event_name, []))

        if not registrations:
            logger.debug(f"No subscribers for {event_name}")
            _broadcast_to_websocket(event)
            return

        logger.debug(
            "Publishing %s (priority=%s) to %s handlers",
            event_name,
            event.priority,
            len(registrations),
        )
        for reg in registrations:
            try:
                reg.handler(event)
            except Exception as e:
                logger.exception("Error in event handler %s for %s", reg.handler.__name__, event_name)
                self._handler_failures.appendleft({
                    "event": event_name,
                    "handler": reg.handler.__name__,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

        _broadcast_to_websocket(event)

    def clear(self) -> None:
        """Clear all subscriptions (useful for testing)."""
        with self._sub_lock:
            self._subscribers.clear()
        self._recent_events.clear()
        self._handler_failures.clear()

    def list_handler_failures(self, *, limit: int = 50) -> list[dict[str, Any]]:
        lim = min(max(1, limit), 100)
        return list(self._handler_failures)[:lim]

    def list_recent_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        lim = min(max(1, limit), 200)
        return list(self._recent_events)[:lim]

    def list_subscribers(self) -> dict[str, int]:
        with self._sub_lock:
            return {name: len(handlers) for name, handlers in self._subscribers.items()}

    def _event_to_dict(self, event: Event) -> dict[str, Any]:
        return event_to_envelope(event).to_dict()


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus

def publish_event(event: Event) -> None:
    """Publish an event to the global event bus."""
    get_event_bus().publish(event)


def enable_websocket_broadcast(broadcast_func: Callable[[str, Any], int]) -> None:
    """Enable WebSocket broadcasting for events.

    Usage:
        from app.infrastructure.realtime.websocket_adapter import broadcast_to_room
        enable_websocket_broadcast(broadcast_to_room)
    """
    global _websocket_enabled, _broadcast_func
    _websocket_enabled = True
    _broadcast_func = broadcast_func
    logger.info("WebSocket broadcasting enabled for event bus")


def _broadcast_to_websocket(event: Event) -> None:
    """Helper to broadcast event to WebSocket."""
    global _websocket_enabled, _broadcast_func
    if _websocket_enabled and _broadcast_func:
        try:
            envelope = event_to_envelope(event)
            room = envelope.data.get("room") or "market"
            _broadcast_func(room, envelope.event, envelope.to_dict())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            logger.exception("WebSocket broadcast failed")


def on_event(event_type: type[Event]):
    """Decorator to register an event handler.

    Usage:
        @on_event(TradeExecutedEvent)
        def handle_trade(event: TradeExecutedEvent):
            print(f"Trade executed: {event.symbol}")
    """
    def decorator(func: Callable[[Event], None]) -> Callable[[Event], None]:
        get_event_bus().subscribe(event_type, func)
        return func
    return decorator


def emit_trade_executed(
    *,
    user_id: str,
    symbol: str,
    action: str,
    quantity: float,
    price: float,
    provenance_id: str,
    market: str = "CN",
    source: str = "",
) -> None:
    """Publish a trade with mandatory provenance_id for audit lineage."""
    if not str(provenance_id or "").strip():
        raise ValueError("provenance_id_required_for_trade_lineage")
    amount = float(quantity) * float(price)
    get_event_bus().publish(
        TradeExecutedEvent(
            source=source,
            user_id=user_id,
            symbol=symbol,
            market=market,
            action=action,
            quantity=quantity,
            price=price,
            amount=amount,
            provenance_id=provenance_id,
        )
    )


def emit_workflow_completed(workflow_id: str, workflow_type: str, state: str, evidence_count: int = 0, step_metrics: dict | None = None) -> None:
    """Convenience helper to publish a WorkflowCompletedEvent."""
    evt = WorkflowCompletedEvent(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        state=state,
        evidence_count=evidence_count,
        step_metrics=step_metrics or {},
    )
    get_event_bus().publish(evt)


def emit_capability_executed(capability_name: str, success: bool = True, duration_ms: float = 0.0) -> None:
    """Convenience helper to publish a CapabilityExecutedEvent."""
    evt = CapabilityExecutedEvent(
        capability_name=capability_name,
        success=success,
        duration_ms=duration_ms,
    )
    get_event_bus().publish(evt)


__all__ = [
    "Event",
    "ServiceStartedEvent",
    "ServiceStoppedEvent",
    "WorkflowCompletedEvent",
    "CapabilityExecutedEvent",
    "TradeExecutedEvent",
    "PositionChangedEvent",
    "MarketDataUpdatedEvent",
    "DebateRoundEvent",
    "TruthDeviationEvent",
    "AnalysisStaleEvent",
    "ArbiterConsensusEvent",
    "CrossTeamSiteAlertEvent",
    "MetaArbiterActivatedEvent",
    "MeshForwardedEvent",
    "CorrectionIntentEvent",
    "EVENT_PRIORITY_LOW",
    "EVENT_PRIORITY_NORMAL",
    "EVENT_PRIORITY_HIGH",
    "EVENT_PRIORITY_CRITICAL",
    "EventBus",
    "get_event_bus",
    "on_event",
    "enable_websocket_broadcast",
    "emit_trade_executed",
    "emit_workflow_completed",
    "publish_event",
    "WatchlistAnomalyDetectedEvent",
]
