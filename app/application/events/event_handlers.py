from __future__ import annotations

"""Event handlers for automated service reactions."""


from app.application.events import EventType, get_event_bus
from app.core.logger import get_logger
from app.modules.system.services.architecture_integration import (
    get_portfolio_service,
    get_risk_service,
    get_signal_service,
)

logger = get_logger(__name__)


class RiskEventHandler:
    """Handler for risk-related events."""

    def __init__(self):
        self._bus = get_event_bus()
        self._bus.subscribe(EventType.RISK_ALERT)(self.handle_risk_alert)
        self._bus.subscribe(EventType.RISK_THRESHOLD_BREACHED)(self.handle_risk_threshold_breached)
        self._bus.subscribe(EventType.STOP_LOSS_TRIGGERED)(self.handle_stop_loss)
        self._bus.subscribe(EventType.TAKE_PROFIT_TRIGGERED)(self.handle_take_profit)

    async def handle_risk_alert(self, event):
        """Handle risk alert events."""
        code = event.payload.get("code")
        severity = event.payload.get("severity")
        message = event.payload.get("message")

        logger.warning(f"Risk Alert [{severity}] {code}: {message}")

        if severity == "critical":
            risk_service = get_risk_service()
            await risk_service._create_alert(
                code=code,
                alert_type="critical_risk",
                message=message,
                severity=severity
            )

    async def handle_risk_threshold_breached(self, event):
        """Handle risk threshold breach events."""
        event.payload.get("portfolio_id")
        threshold_type = event.payload.get("type")
        value = event.payload.get("value")

        logger.warning(f"Risk threshold breached: {threshold_type} = {value}")

    async def handle_stop_loss(self, event):
        """Handle stop loss triggered events."""
        code = event.payload.get("code")
        price = event.payload.get("price")
        reason = event.payload.get("reason", "stop_loss")

        logger.info(f"Stop loss triggered for {code} at {price}")

        portfolio_service = get_portfolio_service()
        await portfolio_service.close_position(code, price, reason)

    async def handle_take_profit(self, event):
        """Handle take profit triggered events."""
        code = event.payload.get("code")
        price = event.payload.get("price")
        reason = event.payload.get("reason", "take_profit")

        logger.info(f"Take profit triggered for {code} at {price}")

        portfolio_service = get_portfolio_service()
        await portfolio_service.close_position(code, price, reason)


class DataEventHandler:
    """Handler for data-related events."""

    def __init__(self):
        self._bus = get_event_bus()
        self._bus.subscribe(EventType.DATA_SYNCED)(self.handle_data_synced)
        self._bus.subscribe(EventType.QUOTE_UPDATED)(self.handle_quote_updated)
        self._bus.subscribe(EventType.HISTORY_UPDATED)(self.handle_history_updated)

    async def handle_data_synced(self, event):
        """Handle data sync completion."""
        market = event.payload.get("market")
        records = event.payload.get("records", 0)

        logger.info(f"Data synced for {market}: {records} records")

    async def handle_quote_updated(self, event):
        """Handle quote update events."""
        code = event.payload.get("code")
        price = event.payload.get("price")

        signal_service = get_signal_service()
        await signal_service._signal_cache.pop(code, None)

        logger.debug(f"Quote updated for {code}: {price}")

    async def handle_history_updated(self, event):
        """Handle history update events."""
        code = event.payload.get("code")
        period = event.payload.get("period")

        logger.debug(f"History updated for {code}: {period}")


class MarketEventHandler:
    """Handler for market-related events."""

    def __init__(self):
        self._bus = get_event_bus()
        self._bus.subscribe(EventType.MARKET_OPEN)(self.handle_market_open)
        self._bus.subscribe(EventType.MARKET_CLOSE)(self.handle_market_close)
        self._bus.subscribe(EventType.MARKET_REGIME_CHANGED)(self.handle_regime_changed)
        self._bus.subscribe(EventType.MARKET_SENTIMENT_UPDATED)(self.handle_sentiment_updated)

    async def handle_market_open(self, event):
        """Handle market open events."""
        market = event.payload.get("market")
        logger.info(f"Market opened: {market}")

    async def handle_market_close(self, event):
        """Handle market close events."""
        market = event.payload.get("market")
        logger.info(f"Market closed: {market}")

    async def handle_regime_changed(self, event):
        """Handle market regime change events."""
        old_regime = event.payload.get("old")
        new_regime = event.payload.get("new")

        logger.warning(f"Market regime changed: {old_regime} -> {new_regime}")

    async def handle_sentiment_updated(self, event):
        """Handle market sentiment update events."""
        market = event.payload.get("market")
        sentiment = event.payload.get("sentiment")

        logger.info(f"Market sentiment updated for {market}: {sentiment}")


class TaskEventHandler:
    """Handler for task-related events."""

    def __init__(self):
        self._bus = get_event_bus()
        self._bus.subscribe(EventType.TASK_COMPLETED)(self.handle_task_completed)
        self._bus.subscribe(EventType.TASK_FAILED)(self.handle_task_failed)
        self._bus.subscribe(EventType.TASK_SCHEDULED)(self.handle_task_scheduled)

    async def handle_task_completed(self, event):
        """Handle task completion events."""
        task_id = event.payload.get("task_id")
        event.payload.get("result")

        logger.info(f"Task completed: {task_id}")

    async def handle_task_failed(self, event):
        """Handle task failure events."""
        task_id = event.payload.get("task_id")
        error = event.payload.get("error")

        logger.error(f"Task failed: {task_id} - {error}")

    async def handle_task_scheduled(self, event):
        """Handle task scheduled events."""
        task_id = event.payload.get("task_id")
        scheduled_at = event.payload.get("scheduled_at")

        logger.info(f"Task scheduled: {task_id} at {scheduled_at}")


def initialize_event_handlers():
    """Initialize all event handlers."""
    RiskEventHandler()
    DataEventHandler()
    MarketEventHandler()
    TaskEventHandler()
    logger.info("All event handlers initialized")


__all__ = [
    "RiskEventHandler",
    "DataEventHandler",
    "MarketEventHandler",
    "TaskEventHandler",
    "initialize_event_handlers",
]
