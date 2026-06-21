"""Provenance domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProvenanceFingerprint:
    """3D fingerprint card for a specific data point."""

    symbol: str
    market: str
    trade_date: str
    point_label: str
    guardian: dict[str, Any]
    rust_core_metrics: dict[str, float] = field(default_factory=dict)
    memory_fabric_notes: list[dict] = field(default_factory=list)
    confidence_score: float = 0.0
