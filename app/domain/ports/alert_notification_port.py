from __future__ import annotations

"""Outbound alert notification channel port."""

from typing import Protocol

from app.domain.dto.alert_dto import AlertEventDTO


class AlertNotificationChannelPort(Protocol):
    """Send normalized alerts to an external channel."""

    @property
    def channel_name(self) -> str:
        ...

    def is_configured(self) -> bool:
        ...

    def send(self, *, title: str, body: str, items: list[AlertEventDTO]) -> bool:
        ...
