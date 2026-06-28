from __future__ import annotations

"""Event handlers for automatic service reactions.

This module demonstrates how services can react to events
instead of directly calling each other.
"""


from app.application.events.event_bus import Event, EventType, get_event_bus
from app.core.logger import get_logger

logger = get_logger(__name__)


class EventHandlerRegistry:
    """Registry for event handlers - auto-registers on import."""

    def __init__(self):
        self._bus = get_event_bus()
        self._register_handlers()

    def _register_handlers(self):
        """Register all event handlers."""
        # Data sync handlers
        self._bus.subscribe(EventType.DATA_SYNCED)(self._handle_data_synced)

        # Quote update handlers
        self._bus.subscribe(EventType.QUOTE_UPDATED)(self._handle_quote_updated)

        # Signal handlers
        self._bus.subscribe(EventType.SIGNAL_GENERATED)(self._handle_signal_generated)

        # Risk alert handlers
        self._bus.subscribe(EventType.RISK_ALERT)(self._handle_risk_alert)

        # Position handlers
        self._bus.subscribe(EventType.POSITION_OPENED)(self._handle_position_opened)
        self._bus.subscribe(EventType.POSITION_CLOSED)(self._handle_position_closed)

    def _handle_data_synced(self, event: Event):
        """Handle data sync completion."""
        logger.info("Event: Data synced for market %s", event.payload.get('market'))

        # Trigger related services
        from app.modules.system.services.helpers.quote_cache_access import get_quote_cache_port
        get_quote_cache_port().clear_expired()

    def _handle_quote_updated(self, event: Event):
        """Handle quote update."""
        code = event.payload.get('code')
        price = event.payload.get('price')
        logger.debug("Event: Quote updated for %s = %s", code, price)

    def _handle_signal_generated(self, event: Event):
        """Handle trading signal generation."""
        signal_code = event.payload.get('code')
        signal_type = event.payload.get('type')
        logger.info("Event: Signal generated - %s %s", signal_code, signal_type)

    def _handle_risk_alert(self, event: Event):
        """Handle risk alert."""
        level = event.payload.get('level')
        code = event.payload.get('code')
        logger.warning("Event: Risk alert - %s %s", level, code)

    def _handle_position_opened(self, event: Event):
        """Handle position opened."""
        code = event.payload.get('code')
        quantity = event.payload.get('quantity')
        logger.info("Event: Position opened - %s x%d", code, quantity)

    def _handle_position_closed(self, event: Event):
        """Handle position closed."""
        code = event.payload.get('code')
        pnl = event.payload.get('pnl')
        logger.info("Event: Position closed - %s PnL: %s", code, pnl)


# Auto-register handlers when module is imported
_handler_registry = EventHandlerRegistry()


def get_event_handlers() -> EventHandlerRegistry:
    """Get the event handler registry."""
    return _handler_registry
