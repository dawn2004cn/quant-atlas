"""Domain-level user context model — framework-agnostic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QuickAction:
    id: str
    label: str
    journey: str | None = None
    route: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass(frozen=True)
class DashboardLayoutDTO:
    layout_id: str
    user_id: int
    cards: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str | None = None


@dataclass(frozen=True)
class JourneyHint:
    journey: str
    label: str
    reason: str
    target_route: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
