"""Backward-compat re-export for ``ImmuneAgentService`` and related types."""
from __future__ import annotations

from app.modules.system.services.immune_agent_service import (
    ImmuneAgentService,
    ImmunityThreat,
    ImmunityVaccine,
    SyntheticFillPacket,
)

__all__ = [
    "ImmuneAgentService",
    "ImmunityThreat",
    "ImmunityVaccine",
    "SyntheticFillPacket",
]
