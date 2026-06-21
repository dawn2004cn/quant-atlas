"""Canvas Event Bridge — push mesh events to Research Canvas via SocketIO (9.0/10.0)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.event_bus import get_event_bus
from app.core.mesh.browser_node_adapter import get_browser_node_adapter
from app.domain.events import (
    ArbiterConsensusEvent,
    CorrectionIntentEvent,
    DebateRoundEvent,
    TradeExecutedEvent,
    TruthDeviationEvent,
    WorkflowCompletedEvent,
)

logger = logging.getLogger(__name__)


class CanvasEventBridge:
    """Bridge mesh events to Research Canvas via SocketIO.

    This service implements the live event streaming for the Research Canvas:
    - Subscribes to mesh events (debate, consensus, correction, etc.)
    - Subscribes to 10.0 resonance events (perception, execution, research trigger)
    - Translates them into canvas-friendly payloads
    - Pushes updates to connected browser nodes via BrowserNodeAdapter
    - Enables real-time visualization of multi-agent reasoning and neural resonance
    """

    def __init__(self) -> None:
        self._event_bus = get_event_bus()
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Subscribe to mesh events for canvas streaming."""
        # 9.0 events
        self._event_bus.subscribe(DebateRoundEvent, self._on_debate_round)
        self._event_bus.subscribe(ArbiterConsensusEvent, self._on_arbiter_consensus)
        self._event_bus.subscribe(CorrectionIntentEvent, self._on_correction_intent)
        self._event_bus.subscribe(TruthDeviationEvent, self._on_truth_deviation)
        self._event_bus.subscribe(TradeExecutedEvent, self._on_trade_executed)
        self._event_bus.subscribe(WorkflowCompletedEvent, self._on_workflow_completed)
        
        # 10.0 Neural Resonance events
        self._setup_resonance_handlers()

    def _setup_resonance_handlers(self) -> None:
        """Subscribe to 10.0 resonance events for canvas streaming."""
        try:
            from app.modules.system.services.mesh.perception_resonance_service import (
                ResonanceActionEvent,
                ResonanceTriggeredResearchEvent,
            )
            from app.modules.execution.services.self_healing_execution_service import (
                ExecutionFailoverEvent,
                ExecutionRecoveryEvent,
            )
            
            self._event_bus.subscribe(ResonanceActionEvent, self._on_resonance_action)
            self._event_bus.subscribe(ResonanceTriggeredResearchEvent, self._on_resonance_triggered_research)
            self._event_bus.subscribe(ExecutionFailoverEvent, self._on_execution_failover)
            self._event_bus.subscribe(ExecutionRecoveryEvent, self._on_execution_recovery)
            
            logger.debug("subscribed to 10.0 resonance events")
        except Exception as exc:
            logger.debug("10.0 resonance event subscription skipped: %s", exc)

    def _on_debate_round(self, event: DebateRoundEvent) -> None:
        """Push debate round updates to canvas."""
        payload = event.payload
        symbol = payload.get("symbol", "")
        agent_role = payload.get("agent_role", "")
        stance = payload.get("stance", "")
        confidence = payload.get("confidence", 0.0)
        evidence_summary = payload.get("evidence_summary", "")

        canvas_update = {
            "event_type": "debate_round",
            "symbol": symbol,
            "agent_role": agent_role,
            "stance": stance,
            "confidence": confidence,
            "evidence_summary": evidence_summary[:200],
            "round_num": payload.get("round_num", 0),
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas("canvas_debate_update", canvas_update, symbol=symbol)

    def _on_arbiter_consensus(self, event: ArbiterConsensusEvent) -> None:
        """Push arbiter consensus updates to canvas."""
        payload = event.payload
        symbol = payload.get("symbol", "")
        verdict = payload.get("verdict", "")
        confidence = payload.get("confidence", 0.0)
        mode = payload.get("mode", "")

        canvas_update = {
            "event_type": "arbiter_consensus",
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "mode": mode,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas("canvas_consensus_update", canvas_update, symbol=symbol)

    def _on_correction_intent(self, event: CorrectionIntentEvent) -> None:
        """Push correction intent updates to canvas."""
        payload = event.payload
        symbol = payload.get("symbol", "")
        change_type = payload.get("change_type", "")
        rationale = payload.get("rationale", "")

        canvas_update = {
            "event_type": "correction_intent",
            "symbol": symbol,
            "change_type": change_type,
            "rationale": rationale[:200],
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas("canvas_correction_update", canvas_update, symbol=symbol)

    def _on_truth_deviation(self, event: TruthDeviationEvent) -> None:
        """Push truth deviation alerts to canvas."""
        payload = event.payload
        symbol = payload.get("symbol", "")
        severity = payload.get("severity", "low")
        message = payload.get("message", "")

        canvas_update = {
            "event_type": "truth_deviation",
            "symbol": symbol,
            "severity": severity,
            "message": message[:200],
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas("canvas_alert_update", canvas_update, symbol=symbol)

    def _on_trade_executed(self, event: TradeExecutedEvent) -> None:
        """Push trade execution updates to canvas."""
        payload = event.payload
        symbol = payload.get("symbol", "")
        side = payload.get("side", "")
        quantity = payload.get("quantity", 0)
        price = payload.get("price", 0)

        canvas_update = {
            "event_type": "trade_executed",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas("canvas_trade_update", canvas_update, symbol=symbol)

    def _on_workflow_completed(self, event: WorkflowCompletedEvent) -> None:
        """Push workflow completion updates to canvas."""
        payload = event.payload
        workflow_id = payload.get("workflow_id", "")
        state = payload.get("state", "")

        canvas_update = {
            "event_type": "workflow_completed",
            "workflow_id": workflow_id,
            "state": state,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas("canvas_workflow_update", canvas_update)

    # ── 10.0 Neural Resonance event handlers ─────────────────────────────

    def _on_resonance_action(self, event: Any) -> None:
        """Push resonance action updates to canvas (10.0)."""
        canvas_update = {
            "event_type": "resonance_action",
            "action_type": getattr(event, "action_type", "unknown"),
            "similarity": getattr(event, "similarity", 0.0),
            "trigger_vector": getattr(event, "trigger_vector", {}),
            "action_result": getattr(event, "action_result", {}),
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        symbol = canvas_update["trigger_vector"].get("metadata", {}).get("symbol", "")
        self._broadcast_to_canvas("canvas_resonance_update", canvas_update, symbol=symbol or None)

    def _on_resonance_triggered_research(self, event: Any) -> None:
        """Push resonance-triggered research updates to canvas (10.0)."""
        canvas_update = {
            "event_type": "resonance_triggered_research",
            "symbol": getattr(event, "symbol", ""),
            "trigger_type": getattr(event, "trigger_type", ""),
            "signal": getattr(event, "signal", ""),
            "confidence": getattr(event, "confidence", 0.0),
            "reason": getattr(event, "reason", ""),
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas(
            "canvas_research_trigger_update",
            canvas_update,
            symbol=canvas_update["symbol"] or None,
        )

    def _on_execution_failover(self, event: Any) -> None:
        """Push execution failover updates to canvas (10.0)."""
        canvas_update = {
            "event_type": "execution_failover",
            "symbol": getattr(event, "symbol", ""),
            "original_venue": getattr(event, "original_venue", ""),
            "failover_venue": getattr(event, "failover_venue", ""),
            "error": getattr(event, "error", ""),
            "attempt": getattr(event, "attempt", 0),
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas(
            "canvas_execution_update",
            canvas_update,
            symbol=canvas_update["symbol"] or None,
        )

    def _on_execution_recovery(self, event: Any) -> None:
        """Push execution venue recovery updates to canvas (10.0)."""
        canvas_update = {
            "event_type": "execution_recovery",
            "venue_id": getattr(event, "venue_id", ""),
            "previous_status": getattr(event, "previous_status", ""),
            "new_status": getattr(event, "new_status", ""),
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        self._broadcast_to_canvas("canvas_execution_update", canvas_update)

    def _broadcast_to_canvas(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        symbol: str | None = None,
    ) -> int:
        """Broadcast event to all connected canvas browser nodes.

        Args:
            event_name: SocketIO event name
            payload: Event payload
            symbol: Optional symbol filter (only send to nodes subscribed to this symbol)

        Returns:
            Number of browser nodes that received the update
        """
        adapter = get_browser_node_adapter()
        if adapter is None:
            return 0

        channel = f"canvas:{symbol}" if symbol else "canvas:*"
        delivered = adapter.broadcast_event(
            event_name,
            payload,
            channel=channel,
        )

        if delivered > 0:
            logger.debug(
                "Canvas event %s delivered to %d browser nodes (symbol=%s)",
                event_name,
                delivered,
                symbol,
            )

        return delivered


_canvas_bridge: CanvasEventBridge | None = None


def get_canvas_event_bridge() -> CanvasEventBridge:
    """Get or create the global canvas event bridge instance."""
    global _canvas_bridge
    if _canvas_bridge is None:
        _canvas_bridge = CanvasEventBridge()
    return _canvas_bridge


__all__ = ["CanvasEventBridge", "get_canvas_event_bridge"]
