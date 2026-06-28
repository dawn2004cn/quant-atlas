from __future__ import annotations

"""Borderless execution descriptors (Quant Atlas 9.0 Step Two)."""

from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import MarketCode


class ExecutionRouteDescriptor(BaseModel):
    """Resolved routing target for a symbol across markets."""

    symbol: str
    market: MarketCode
    driver_id: str
    exchange: str = ""
    currency: str = "CNY"
    mode: str = "paper"
    evidence: str = ""
    confidence: float = 0.9


class BorderlessOrderRequest(BaseModel):
    """Unified cross-market order submission."""

    symbol: str
    market: str | None = None
    side: str = "buy"
    order_type: str = "market"
    amount: float = 0.0
    quantity: float = 0.0
    price: float = 0.0
    exchange: str = ""
    provenance_id: str = ""
    client_order_id: str = ""
    user_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionManifest(BaseModel):
    """Cluster-wide execution capability manifest."""

    enabled: bool = True
    default_mode: str = "paper"
    markets: list[str] = Field(default_factory=list)
    drivers: list[dict[str, Any]] = Field(default_factory=list)
    mesh_linked: bool = False


__all__ = [
    "ExecutionRouteDescriptor",
    "BorderlessOrderRequest",
    "ExecutionManifest",
]
