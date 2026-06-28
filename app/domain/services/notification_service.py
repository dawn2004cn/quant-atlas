from __future__ import annotations
"""Notification system using event-driven architecture."""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections.abc import Callable

from abc import ABC, abstractmethod
from app.core.logger import get_logger

logger = get_logger(__name__)


class NotificationType(Enum):
    """Notification type enumeration."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    SIGNAL = "signal"
    ALERT = "alert"


class NotificationChannel(Enum):
    """Notification channel enumeration."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    DINGTALK = "dingtalk"


@dataclass
class Notification:
    """Notification entity."""
    id: str
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO

    recipient: str = ""
    channel: NotificationChannel = NotificationChannel.PUSH

    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.now)
    sent_at: datetime | None = None
    read_at: datetime | None = None

    def mark_read(self):
        """Mark notification as read."""
        self.read_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.notification_type.value,
            "channel": self.channel.value,
            "created_at": self.created_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }


class EventBusPort(ABC):
    """Domain port for event bus — implemented by infrastructure."""

    @abstractmethod
    def subscribe(self, event_type: Any, handler: Callable) -> None:
        ...

    @abstractmethod
    def publish(self, event_type: Any, payload: dict[str, Any] | None = None) -> None:
        ...


class NotificationService:
    """Notification domain service."""

    def __init__(self, event_bus: EventBusPort | None = None):
        self._notifications: list[Notification] = []
        self._handlers: dict[NotificationChannel, list[Callable]] = {
            channel: [] for channel in NotificationChannel
        }
        self._bus = event_bus
        if self._bus is not None:
            self._subscribe_to_events()
        logger.info("NotificationService initialized")

    def _subscribe_to_events(self):
        """Subscribe to relevant events."""
        from app.domain.events import EventType
        self._bus.subscribe(EventType.SIGNAL_GENERATED, self._on_signal)
        self._bus.subscribe(EventType.RISK_ALERT, self._on_risk_alert)
        self._bus.subscribe(EventType.POSITION_CLOSED, self._on_position_closed)
        self._bus.subscribe(EventType.ALERT_TRIGGERED, self._on_alert)
        self._bus.subscribe(EventType.TASK_COMPLETED, self._on_task_completed)
        self._bus.subscribe(EventType.TASK_FAILED, self._on_task_failed)

    async def _on_signal(self, event):
        """Handle signal generated event."""
        code = event.payload.get("code")
        signal_type = event.payload.get("signal_type")
        await self.send_notification(
            title=f"交易信号: {code}",
            message=f"检测到 {signal_type} 信号",
            notification_type=NotificationType.SIGNAL,
            metadata=event.payload,
        )

    async def _on_risk_alert(self, event):
        """Handle risk alert event."""
        code = event.payload.get("code")
        severity = event.payload.get("severity")
        message = event.payload.get("message")

        await self.send_notification(
            title=f"风控警告 [{severity}]: {code}",
            message=message,
            notification_type=NotificationType.ALERT,
            metadata=event.payload,
        )

    async def _on_position_closed(self, event):
        """Handle position closed event."""
        code = event.payload.get("code")
        pnl = event.payload.get("pnl")

        await self.send_notification(
            title=f"持仓平仓: {code}",
            message=f"平仓盈亏: {pnl:.2f}",
            notification_type=NotificationType.SUCCESS if pnl > 0 else NotificationType.ERROR,
            metadata=event.payload,
        )

    async def _on_alert(self, event):
        """Handle alert triggered event."""
        await self.send_notification(
            title="系统提醒",
            message=event.payload.get("message", ""),
            notification_type=NotificationType.WARNING,
            metadata=event.payload,
        )

    async def _on_task_completed(self, event):
        """Handle task completed event."""
        task_id = event.payload.get("task_id")
        await self.send_notification(
            title="任务完成",
            message=f"任务 {task_id} 已完成",
            notification_type=NotificationType.SUCCESS,
            metadata=event.payload,
        )

    async def _on_task_failed(self, event):
        """Handle task failed event."""
        task_id = event.payload.get("task_id")
        error = event.payload.get("error")
        await self.send_notification(
            title="任务失败",
            message=f"任务 {task_id} 失败: {error}",
            notification_type=NotificationType.ERROR,
            metadata=event.payload,
        )

    async def send_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        recipient: str = "",
        channel: NotificationChannel = NotificationChannel.PUSH,
        metadata: dict[str, Any] | None = None,
    ) -> Notification:
        """Send a notification."""
        from uuid import uuid4

        notification = Notification(
            id=str(uuid4()),
            title=title,
            message=message,
            notification_type=notification_type,
            recipient=recipient,
            channel=channel,
            metadata=metadata or {},
        )

        self._notifications.append(notification)
        await self._deliver(notification)

        logger.info(f"Notification sent: {title}")
        return notification

    async def _deliver(self, notification: Notification):
        """Deliver notification through appropriate channel."""
        handlers = self._handlers.get(notification.channel, [])
        for handler in handlers:
            try:
                await handler(notification)
                notification.sent_at = datetime.now()
            except Exception as e:
                logger.error(f"Failed to deliver notification: {e}")

    def register_handler(self, channel: NotificationChannel, handler: Callable):
        """Register a notification handler for a channel."""
        self._handlers[channel].append(handler)

    def get_notifications(
        self,
        limit: int = 50,
        notification_type: NotificationType | None = None,
        unread_only: bool = False,
    ) -> list[Notification]:
        """Get notifications."""
        result = self._notifications[-limit:]

        if notification_type:
            result = [n for n in result if n.notification_type == notification_type]

        if unread_only:
            result = [n for n in result if n.read_at is None]

        return result

    def mark_read(self, notification_id: str) -> bool:
        """Mark notification as read."""
        for n in self._notifications:
            if n.id == notification_id:
                n.mark_read()
                return True
        return False

    def clear_all(self):
        """Clear all notifications."""
        self._notifications.clear()


_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get global notification service."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


__all__ = [
    "NotificationType",
    "NotificationChannel",
    "Notification",
    "NotificationService",
    "get_notification_service",
]
