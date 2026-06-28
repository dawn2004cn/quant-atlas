from __future__ import annotations

"""Workflow event handlers - Automated business process triggers.

This module implements Phase 8: Event-Driven architecture by providing
workflows that react to events automatically.
"""



from app.application.events.event_bus import Event, EventType, get_event_bus
from app.core.logger import get_logger
from app.domain.ports.stock_cache_port import StockCachePort

logger = get_logger(__name__)


class MarketDataWorkflow:
    """Workflow for market data processing."""

    def __init__(self, stock_cache: StockCachePort | None = None):
        self._bus = get_event_bus()
        self._stock_cache = stock_cache
        self._bus.subscribe(EventType.DATA_SYNCED)(self.on_data_synced)
        self._bus.subscribe(EventType.QUOTE_UPDATED)(self.on_quote_updated)

    async def on_data_synced(self, event: Event):
        """Handle data sync completion."""
        market = event.payload.get('market')
        records = event.payload.get('records', 0)

        logger.info(f"Market data synced: {market}, {records} records")

        # Trigger related workflows
        if market == 'CN':
            await self._update_market_sentiment()
            await self._refresh_rankings()

    async def on_quote_updated(self, event: Event):
        """Handle quote update."""
        code = event.payload.get('code')
        price = event.payload.get('price')

        # Check price alerts
        await self._check_price_alerts(code, price)

    async def _update_market_sentiment(self):
        """Update market sentiment after data sync."""
        if self._stock_cache is None:
            return
        try:
            cache = self._stock_cache

            stocks = cache.get_all_stocks(max_age_minutes=15)
            if not stocks:
                return

            up = sum(1 for s in stocks if float(s.get('change_pct', 0)) > 0)
            down = sum(1 for s in stocks if float(s.get('change_pct', 0)) < 0)
            flat = len(stocks) - up - down

            cache.save_sentiment("CN", up, down, flat)

            # Publish sentiment update event
            self._bus.publish(Event(
                type=EventType.DATA_SYNCED,
                payload={'market': 'CN', 'sentiment_updated': True},
                source='MarketDataWorkflow'
            ))

        except Exception as e:
            logger.warning(f"Failed to update sentiment: {e}")

    async def _refresh_rankings(self):
        """Refresh market rankings after data sync."""
        pass  # Could trigger ranking calculations

    async def _check_price_alerts(self, code: str, price: float):
        """Check and trigger price alerts."""
        try:
            # Load user price alerts
            from app.domain.ports.price_alert_port import NullPriceAlertRepository
            repo = NullPriceAlertRepository()
            alerts = repo.get_alerts_for_symbol(code)

            for alert in alerts:
                if alert.should_trigger(price):
                    self._bus.publish(Event(
                        type=EventType.RISK_ALERT,
                        payload={
                            'type': 'price',
                            'code': code,
                            'level': alert.level,
                            'message': f"{code} 达到 {alert.target_price}"
                        },
                        source='MarketDataWorkflow'
                    ))
        except Exception as e:
            logger.debug(f"Price alert check failed: {e}")


class SignalWorkflow:
    """Workflow for signal processing and notifications."""

    def __init__(self):
        self._bus = get_event_bus()
        self._bus.subscribe(EventType.SIGNAL_GENERATED)(self.on_signal_generated)

    async def on_signal_generated(self, event: Event):
        """Handle new signal generation."""
        code = event.payload.get('code')
        signal_type = event.payload.get('type')
        direction = event.payload.get('direction')

        logger.info(f"Signal workflow: {code} {signal_type} {direction}")

        # Auto-create watchlist entry for strong signals
        if event.payload.get('strength', 0) >= 3:
            await self._add_to_watchlist(code, signal_type)

    async def _add_to_watchlist(self, code: str, signal_type: str):
        """Auto-add strong signals to watchlist."""
        try:
            # This would integrate with watchlist service
            logger.debug(f"Would add {code} to watchlist (signal: {signal_type})")
        except Exception as e:
            logger.warning(f"Auto-watchlist failed: {e}")


class PositionWorkflow:
    """Workflow for position management."""

    def __init__(self):
        self._bus = get_event_bus()
        self._bus.subscribe(EventType.POSITION_OPENED)(self.on_position_opened)
        self._bus.subscribe(EventType.POSITION_CLOSED)(self.on_position_closed)

    async def on_position_opened(self, event: Event):
        """Handle position opened."""
        code = event.payload.get('code')
        quantity = event.payload.get('quantity')

        logger.info(f"Position opened: {code} x{quantity}")

        # Set up stop-loss monitoring
        await self._setup_monitoring(code)

    async def on_position_closed(self, event: Event):
        """Handle position closed."""
        code = event.payload.get('code')
        pnl = event.payload.get('pnl', 0)

        logger.info(f"Position closed: {code} PnL: {pnl}")

        # Record performance metrics
        await self._record_performance(code, pnl)

    async def _setup_monitoring(self, code: str):
        """Setup price monitoring for position."""
        pass

    async def _record_performance(self, code: str, pnl: float):
        """Record trade performance."""
        pass


# Auto-initialize workflows
_market_workflow = MarketDataWorkflow()
_signal_workflow = SignalWorkflow()
_position_workflow = PositionWorkflow()


def get_workflows():
    """Get all workflow instances."""
    return {
        'market': _market_workflow,
        'signal': _signal_workflow,
        'position': _position_workflow,
    }
