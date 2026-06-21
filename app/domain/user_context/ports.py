from __future__ import annotations

from abc import abstractmethod

from .models import DashboardLayoutDTO, JourneyHint, QuickAction


class UserContextPort:
    @abstractmethod
    def get_dashboard_layout(self, user_id: int) -> DashboardLayoutDTO: ...

    @abstractmethod
    def get_quick_actions(self, user_id: int, context: dict[str, object] | None = None) -> list[QuickAction]: ...

    @abstractmethod
    def get_journey_suggestions(
        self,
        user_id: int,
        last_journey: str | None = None,
        market_state: dict[str, object] | None = None,
    ) -> list[JourneyHint]: ...
