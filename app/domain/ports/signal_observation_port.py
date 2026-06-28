from __future__ import annotations

"""Port for signal observation / simulated position persistence."""

from abc import ABC, abstractmethod
from typing import Any


class SignalObservationRepository(ABC):
    @abstractmethod
    def create_observation(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_observation(
        self, observation_id: str, user_id: int, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def get_observation(self, observation_id: str, user_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def list_observations(
        self, user_id: int, status: str = "open", limit: int = 100
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def close_observation(self, observation_id: str, user_id: int, reason: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def update_notes(self, observation_id: str, user_id: int, notes: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create_position(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_positions(self, user_id: int, limit: int = 100) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_stats(self, user_id: int) -> dict[str, Any]:
        raise NotImplementedError
