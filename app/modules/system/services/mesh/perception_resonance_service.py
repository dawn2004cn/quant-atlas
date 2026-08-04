"""Perception Resonance — 10.0 neural resonance bridge over CollectivePerceptionLayer."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from app.core.event_bus import Event, get_event_bus
from app.core.logger import get_logger
from app.core.mesh.perception_layer import get_perception_layer

logger = get_logger(__name__)


@dataclass
class ResonanceActionEvent(Event):
    """Fired when a perception vector triggers a subscribed resonance action."""

    action_type: str = ""
    similarity: float = 0.0
    trigger_vector: dict[str, Any] = field(default_factory=dict)
    action_result: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResonanceTriggeredResearchEvent(Event):
    """Fired when resonance confidence exceeds research trigger threshold."""

    symbol: str = ""
    trigger_type: str = ""
    signal: str = ""
    confidence: float = 0.0
    reason: str = ""


class PerceptionResonanceService:
    """Thin service facade for perception layer stats and resonance action history."""

    def __init__(self, *, perception_layer: Any | None = None) -> None:
        self._layer = perception_layer if perception_layer is not None else get_perception_layer()
        self._action_log: deque[dict[str, Any]] = deque(maxlen=500)
        self._event_bus = get_event_bus()

    def record_action(
        self,
        *,
        action_type: str,
        similarity: float,
        trigger_vector: dict[str, Any] | None = None,
        action_result: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "action_type": action_type,
            "similarity": similarity,
            "trigger_vector": trigger_vector or {},
            "action_result": action_result or {},
        }
        self._action_log.append(entry)
        try:
            self._event_bus.publish(
                ResonanceActionEvent(
                    source="perception_resonance_service",
                    action_type=action_type,
                    similarity=similarity,
                    trigger_vector=trigger_vector or {},
                    action_result=action_result or {},
                )
            )
        except Exception as exc:
            logger.debug("resonance action publish skipped: %s", exc)

    def trigger_research(
        self,
        *,
        symbol: str,
        trigger_type: str,
        signal: str,
        confidence: float,
        reason: str = "",
    ) -> None:
        try:
            self._event_bus.publish(
                ResonanceTriggeredResearchEvent(
                    source="perception_resonance_service",
                    symbol=symbol,
                    trigger_type=trigger_type,
                    signal=signal,
                    confidence=confidence,
                    reason=reason,
                )
            )
        except Exception as exc:
            logger.debug("resonance research publish skipped: %s", exc)

    def get_stats(self) -> dict[str, Any]:
        if self._layer is None:
            return {
                "ok": True,
                "enabled": False,
                "active_vectors": 0,
                "action_log_size": len(self._action_log),
            }
        manifest = self._layer.get_manifest()
        return {
            "ok": True,
            "enabled": True,
            "action_log_size": len(self._action_log),
            **manifest,
        }

    def get_action_log(self, *, limit: int = 100) -> list[dict[str, Any]]:
        cap = max(1, min(limit, 500))
        if self._layer is not None:
            recent = self._layer.get_manifest().get("recent_resonance") or []
            if recent:
                return list(recent)[-cap:]
        return list(self._action_log)[-cap:]


__all__ = [
    "PerceptionResonanceService",
    "ResonanceActionEvent",
    "ResonanceTriggeredResearchEvent",
]
