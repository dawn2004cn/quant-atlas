"""Consolidated signal, observation, and alert ports."""

from __future__ import annotations

from typing import Any, Protocol

# ── Signal Ports ────────────────────────────────────────────────────────


class SignalFlagPoolRepository(Protocol):
    """Port for signal flag pool operations."""

    def get_flags(self) -> list[dict[str, Any]]:
        ...

    def set_flag(self, symbol: str, flag: str) -> bool:
        ...


class SignalObservationRepository(Protocol):
    """Port for signal observation records."""

    def get_observations(self, symbol: str) -> list[dict[str, Any]]:
        ...


class StrategySnapshotPort(Protocol):
    """Port for strategy snapshot storage."""

    def save_snapshot(self, strategy_id: str, snapshot: dict[str, Any]) -> bool:
        ...

    def get_snapshot(self, strategy_id: str) -> dict[str, Any] | None:
        ...


# ── Alert Ports ─────────────────────────────────────────────────────────


class AlertNotificationChannelPort(Protocol):
    """Port for alert notification channels."""

    def send(self, message: str, channel: str) -> bool:
        ...


class PriceAlertRepository(Protocol):
    """Port for price alert management."""

    def get_alerts_for_symbol(self, symbol: str) -> list[dict[str, Any]]:
        ...
