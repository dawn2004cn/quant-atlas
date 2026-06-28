from __future__ import annotations


from app.core.logger import get_logger
from app.domain.user_context.models import DashboardLayoutDTO, JourneyHint, QuickAction
from app.domain.user_context.ports import UserContextPort

logger = get_logger(__name__)


class UserContextEngine:
    def __init__(self, user_context_port: UserContextPort) -> None:
        self._port = user_context_port

    def get_dashboard_layout(self, user_id: int) -> DashboardLayoutDTO:
        return self._port.get_dashboard_layout(user_id)

    def get_quick_actions(self, user_id: int, context: dict[str, object] | None = None) -> list[QuickAction]:
        return self._port.get_quick_actions(user_id, context)

    def get_journey_suggestions(
        self,
        user_id: int,
        last_journey: str | None = None,
        market_state: dict[str, object] | None = None,
    ) -> list[JourneyHint]:
        return self._port.get_journey_suggestions(user_id, last_journey, market_state)
