from __future__ import annotations
"""Federated Agent Mesh descriptors (Quant Atlas 9.0)."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MeshRegion(str, Enum):
    CN = "CN"
    US = "US"
    HK = "HK"
    EU = "EU"
    GLOBAL = "GLOBAL"
    CLIENT = "CLIENT"


class MeshNodeRole(str, Enum):
    GATEWAY = "gateway"
    MACRO_AGENT = "macro_agent"
    TECHNICAL_AGENT = "technical_agent"
    SENTIMENT_AGENT = "sentiment_agent"
    ARBITER = "arbiter"
    DATA_SYNC = "data_sync"
    EXECUTION = "execution"
    BROWSER_CLIENT = "browser_client"


class MeshNodeDescriptor(BaseModel):
    """A federated mesh participant (physical or logical region node)."""

    node_id: str
    region: MeshRegion = MeshRegion.CN
    roles: list[MeshNodeRole] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    endpoint: str = ""
    agent_topology_id: str = ""
    status: str = "online"
    last_heartbeat: str = ""
    user_id: str | None = None
    session_id: str | None = None

    def matches_role(self, role: str) -> bool:
        return role in {r.value for r in self.roles} or role in self.capabilities


class MeshEventEnvelope(BaseModel):
    """Wire format for cross-node event propagation."""

    schema_version: str = "v1"
    envelope_id: str
    topic: str
    event_name: str
    origin_node_id: str
    origin_region: str = "CN"
    target_regions: list[str] = Field(default_factory=lambda: ["*"])
    priority: int = 10
    timestamp: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class MeshPublishRequest(BaseModel):
    topic: str = "quant.mesh.events"
    event_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    target_regions: list[str] = Field(default_factory=lambda: ["*"])
    priority: int = 10


__all__ = [
    "MeshRegion",
    "MeshNodeRole",
    "MeshNodeDescriptor",
    "MeshEventEnvelope",
    "MeshPublishRequest",
]
