"""Event type definitions for Quant Atlas.

This module contains all event dataclasses used by the EventBus,
the global _EVENT_TYPES registry, and serialization/deserialization
utilities.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

# Priority tiers for Quant Atlas 4.0 arbitration / truth events.
EVENT_PRIORITY_LOW = 0
EVENT_PRIORITY_MEDIUM = 10
EVENT_PRIORITY_NORMAL = 10
EVENT_PRIORITY_HIGH = 50
EVENT_PRIORITY_CRITICAL = 100


@dataclass
class _HandlerRegistration:
    priority: int
    handler: Any


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


# ── event type registry ──────────────────────────────────────────────────

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


# ── serialization utilities ──────────────────────────────────────────────


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


__all__ = [
    "Event",
    "EventEnvelope",
    "EventSchemaError",
    "ServiceStartedEvent",
    "ServiceStoppedEvent",
    "WorkflowCompletedEvent",
    "CapabilityExecutedEvent",
    "TradeExecutedEvent",
    "PositionChangedEvent",
    "MarketDataUpdatedEvent",
    "MarketRegimeChangedEvent",
    "DebateRoundEvent",
    "TruthDeviationEvent",
    "AnalysisStaleEvent",
    "ArbiterConsensusEvent",
    "CrossTeamSiteAlertEvent",
    "MetaArbiterActivatedEvent",
    "CorrectionIntentEvent",
    "WatchlistAnomalyDetectedEvent",
    "MeshForwardedEvent",
    "ApplicationEventForwardedEvent",
    "EVENT_PRIORITY_LOW",
    "EVENT_PRIORITY_MEDIUM",
    "EVENT_PRIORITY_NORMAL",
    "EVENT_PRIORITY_HIGH",
    "EVENT_PRIORITY_CRITICAL",
    "event_schema",
    "event_to_envelope",
    "event_from_envelope",
    "event_to_json",
    "event_from_json",
]
