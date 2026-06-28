from __future__ import annotations

"""Mesh topic naming and federated event protocol constants."""

MESH_SCHEMA_VERSION = "v1"
MESH_CHANNEL_PREFIX = "quant.mesh"
MESH_EVENTS_CHANNEL = f"{MESH_CHANNEL_PREFIX}.events"
MESH_CONTROL_CHANNEL = f"{MESH_CHANNEL_PREFIX}.control"
MESH_HEARTBEAT_CHANNEL = f"{MESH_CHANNEL_PREFIX}.heartbeat"

DEFAULT_FANOUT_EVENTS = frozenset({
    "DebateRoundEvent",
    "ArbiterConsensusEvent",
    "MetaArbiterActivatedEvent",
    "CrossTeamSiteAlertEvent",
    "WorkflowCompletedEvent",
    "MarketDataUpdatedEvent",
    "TradeExecutedEvent",
    "TruthDeviationEvent",
    "AnalysisStaleEvent",
    "CorrectionIntentEvent",
})

REDIS_NODES_KEY = "quant:mesh:nodes"
REDIS_NODE_TTL_SECONDS = 90


def topic_for_event(event_name: str) -> str:
    return f"{MESH_EVENTS_CHANNEL}.{event_name}"


def region_filter_allows(target_regions: list[str], local_region: str) -> bool:
    if not target_regions or "*" in target_regions:
        return True
    return local_region.upper() in {r.upper() for r in target_regions}


__all__ = [
    "MESH_SCHEMA_VERSION",
    "MESH_EVENTS_CHANNEL",
    "MESH_CONTROL_CHANNEL",
    "MESH_HEARTBEAT_CHANNEL",
    "DEFAULT_FANOUT_EVENTS",
    "REDIS_NODES_KEY",
    "REDIS_NODE_TTL_SECONDS",
    "topic_for_event",
    "region_filter_allows",
]
