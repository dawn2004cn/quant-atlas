from __future__ import annotations

"""Trading workflows for new architecture services."""


from app.application.events.event_bus import Event, EventType, get_event_bus
from app.core.logger import get_logger

logger = get_logger(__name__)


class TradingWorkflow:
    """Workflow for trading signal and position management."""

    def __init__(self):
        self._bus = get_event_bus()
        self._bus.subscribe(EventType.SIGNAL_GENERATED)(self.on_signal_generated)
        self._bus.subscribe(EventType.POSITION_OPENED)(self.on_position_opened)
        self._bus.subscribe(EventType.POSITION_CLOSED)(self.on_position_closed)
        self._bus.subscribe(EventType.RISK_ALERT)(self.on_risk_alert)

    async def on_signal_generated(self, event: Event):
        """Handle new signal generated."""
        code = event.payload.get("code")
        signal_type = event.payload.get("signal_type")
        logger.info(f"Signal generated for {code}: {signal_type}")

    async def on_position_opened(self, event: Event):
        """Handle position opened."""
        code = event.payload.get("code")
        quantity = event.payload.get("quantity")
        logger.info(f"Position opened: {code}, qty: {quantity}")

    async def on_position_closed(self, event: Event):
        """Handle position closed."""
        code = event.payload.get("code")
        pnl = event.payload.get("pnl")
        reason = event.payload.get("reason", "unknown")
        logger.info(f"Position closed: {code}, PnL: {pnl:.2f}, reason: {reason}")

    async def on_risk_alert(self, event: Event):
        """Handle risk alert."""
        code = event.payload.get("code")
        severity = event.payload.get("severity")
        message = event.payload.get("message")
        logger.warning(f"Risk alert [{severity}] for {code}: {message}")


_trading_workflow: TradingWorkflow | None = None


def init_trading_workflow():
    """Initialize trading workflow."""
    global _trading_workflow
    if _trading_workflow is None:
        _trading_workflow = TradingWorkflow()
        logger.info("TradingWorkflow initialized")
    return _trading_workflow


__all__ = ["TradingWorkflow", "init_trading_workflow"]
