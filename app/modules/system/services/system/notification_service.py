from __future__ import annotations

import asyncio

from app.core.event_bus import NotificationSendEvent, StrategyRegimeMismatchEvent, publish_event
from app.core.logger import get_logger
from app.core.registry import ServiceRegistry

logger = get_logger(__name__)


class NotificationService:
    """Handles the delivery of system alerts and AI recommendations to the user."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    async def send_alert(
        self,
        user_id: str,
        title: str,
        message: str,
        level: str = "info",
        action_url: str | None = None,
    ) -> bool:
        """Send a notification to the user (via WebSocket, Email, or in-app toast)."""
        logger.info("Notification sent to %s: [%s] %s - %s", user_id, level, title, message)

        publish_event(
            NotificationSendEvent(
                source="notification_service",
                user_id=user_id,
                title=title,
                message=message,
                level=level,
                action_url=action_url,
            )
        )
        return True

    def notify_regime_mismatch(self, event: StrategyRegimeMismatchEvent):
        """Specialized handler for StrategyRegimeMismatchEvent."""
        title = "⚠️ Strategy Regime Mismatch"
        message = (
            f"Your strategy '{event.strategy_name}' was designed for a different market regime. "
            f"Current regime is {event.current_regime}. We recommend switching to {event.recommended_category}."
        )
        action_url = "/strategy-wizard"

        asyncio.run(
            self.send_alert(
                user_id="current_user",
                title=title,
                message=message,
                level="warning",
                action_url=action_url,
            )
        )
