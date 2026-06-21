from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from app.core.registry import ServiceRegistry
from app.core.event_bus import publish_event
from app.modules.strategy.services.strategy.strategy_sentinel_service import StrategyRegimeMismatchEvent
from app.core.logger import get_logger

logger = get_logger(__name__)

class NotificationService:
    """
    Handles the delivery of system alerts and AI recommendations to the user.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    async def send_alert(self, user_id: str, title: str, message: str, level: str = "info", action_url: Optional[str] = None) -> bool:
        """
        Send a notification to the user (via WebSocket, Email, or In-app toast).
        """
        # In a real implementation, this would push to a WebSocket client or a notification DB
        alert_payload = {
            "user_id": user_id,
            "title": title,
            "message": message,
            "level": level,
            "action_url": action_url,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        logger.info(f"Notification sent to {user_id}: [{level}] {title} - {message}")
        
        # We publish to the event bus so the frontend WebSocket adapter can pick it up
        publish_event("notification.send", alert_payload)
        return True

    def notify_regime_mismatch(self, event: StrategyRegimeMismatchEvent):
        """
        Specialized handler for StrategyRegimeMismatchEvent.
        """
        title = "⚠️ Strategy Regime Mismatch"
        message = (
            f"Your strategy '{event.strategy_name}' was designed for a different market regime. "
            f"Current regime is {event.current_regime}. We recommend switching to {event.recommended_category}."
        )
        action_url = "/strategy-wizard"
        
        # Using a dummy user_id for now
        asyncio.run(self.send_alert(
            user_id="current_user",
            title=title,
            message=message,
            level="warning",
            action_url=action_url
        ))
