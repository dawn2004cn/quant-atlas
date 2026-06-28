from __future__ import annotations

import logging
from typing import Any

from app.core.base_service import BaseApplicationService
from app.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class FastPathTriggerService(BaseApplicationService):
    """
    The FastPathTriggerService is the 'spinal cord' of the system.
    It listens to the real-time event stream and triggers the FastPathOrchestrator
    based on pre‑computed parameters in the FastPathParameterStore.
    """

    def __init__(
        self,
        event_bus: EventBus,
        orchestrator: Any,
        parameter_store: Any,
    ):
        super().__init__()
        self._event_bus = event_bus
        self._orchestrator = orchestrator
        self._param_store = parameter_store

        # Subscribe to high‑frequency events
        from app.core.event_bus import AnalysisStaleEvent, MarketDataUpdatedEvent
        self._event_bus.subscribe(MarketDataUpdatedEvent, self._on_market_tick)
        # Placeholder for alpha signals – using AnalysisStaleEvent as a proxy
        self._event_bus.subscribe(AnalysisStaleEvent, self._on_alpha_signal)

        logger.info("FastPathTriggerService initialized and subscribed to reflex events.")

    def _on_market_tick(self, event: Event) -> None:
        """
        Reflex action on price tick.
        Check if the current price hits a pre‑computed trigger from the Slow Path.
        """
        # The MarketDataUpdatedEvent carries symbol and market; price is not part of the core event.
        # For demonstration, we use a placeholder "price" attribute if present.
        symbol = getattr(event, "symbol", None)
        current_price = getattr(event, "price", None)

        if not symbol or current_price is None:
            return

        # 1. Check for 'Auto-Trigger' settings in the Reflex Map
        trigger_price = self._param_store.get_parameter(symbol, "trigger_price")
        side = self._param_store.get_parameter(symbol, "trigger_side")  # 'buy' or 'sell'

        if trigger_price is None or side is None:
            return

        # 2. Reflex Condition Check
        should_execute = False
        if side == "buy" and current_price <= trigger_price:
            should_execute = True
        elif side == "sell" and current_price >= trigger_price:
            should_execute = True

        if should_execute:
            logger.info(
                "Reflex Trigger Hit [%s]: Price %s %s %s. Executing Fast Path...",
                symbol,
                current_price,
                "<=" if side == "buy" else ">=",
                trigger_price,
            )

            # Create a minimal trade request for the orchestrator
            trade_request = {
                "symbol": symbol,
                "side": side,
                "quantity": self._param_store.get_parameter(symbol, "trigger_qty", 100),
                "price": current_price,
                "type": "MARKET",
            }
            # Execute via Fast Path orchestrator
            self._orchestrator.execute_trade(trade_request)

    def _on_alpha_signal(self, event: Event) -> None:
        """
        Reflex action on Alpha Signal.
        If the AI's Alpha engine produces a high‑confidence signal, execute immediately.
        This handler works with any event that carries a ``symbol`` and ``confidence``
        attribute (e.g. a custom AlphaSignalEvent). We fall back gracefully if the
        expected fields are missing.
        """
        # Extract a dict‑like payload if present; otherwise read attributes.
        payload = getattr(event, "payload", None)
        if isinstance(payload, dict):
            signal_data = payload
        else:
            signal_data = {
                "symbol": getattr(event, "symbol", None),
                "confidence": getattr(event, "confidence", 0.0),
                "side": getattr(event, "side", "buy"),
                "suggested_qty": getattr(event, "suggested_qty", 100),
                "current_price": getattr(event, "current_price", None),
            }

        symbol = signal_data.get("symbol")
        confidence = signal_data.get("confidence", 0.0)

        if not symbol:
            return

        # Default threshold if not configured in the store
        threshold = self._param_store.get_parameter("global", "reflex_threshold", 0.85)

        if confidence >= threshold:
            logger.info(
                "Reflex Alpha Hit [%s]: Confidence %s >= %s. Executing...",
                symbol,
                confidence,
                threshold,
            )
            trade_request = {
                "symbol": symbol,
                "side": signal_data.get("side", "buy"),
                "quantity": signal_data.get("suggested_qty", 100),
                "price": signal_data.get("current_price"),
                "type": "MARKET",
            }
            # Only execute if we have a price to act on
            if trade_request["price"] is not None:
                self._orchestrator.execute_trade(trade_request)
