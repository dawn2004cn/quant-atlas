from __future__ import annotations

"""Quant Atlas public SDK surface."""

from app.sdk.core.client import QuantAtlasClient, create_client, strategy, StrategyDefinition
from app.sdk.facades import AlertsFacade, AttributionFacade, SnapshotsFacade

__all__ = [
    "AlertsFacade",
    "AttributionFacade",
    "QuantAtlasClient",
    "SnapshotsFacade",
    "StrategyDefinition",
    "create_client",
    "strategy",
]
