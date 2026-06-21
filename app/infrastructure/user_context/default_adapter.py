from __future__ import annotations

from typing import Any

from app.domain.user_context.models import DashboardLayoutDTO, JourneyHint, QuickAction
from app.domain.user_context.ports import UserContextPort

_JOURNEY_HINTS = [
    ("discovery", "发现"),
    ("research", "研究"),
    ("execution", "执行"),
    ("review", "复盘"),
    ("monitor", "监控"),
    ("manage", "管理"),
]


class DefaultUserContextAdapter(UserContextPort):
    def get_dashboard_layout(self, user_id: int) -> DashboardLayoutDTO:
        return DashboardLayoutDTO(layout_id=f"default_{user_id}", user_id=user_id)

    def get_quick_actions(self, user_id: int, context: dict[str, object] | None = None) -> list[QuickAction]:
        return [
            QuickAction(id="qa_market", label="市场全景", journey="discovery", route="/markets/CN/panorama", priority=10),
            QuickAction(id="qa_stock", label="个股详情", journey="discovery", route="/stocks", priority=9),
            QuickAction(id="qa_ai", label="AI 诊股", journey="research", route="/ai-hedge-fund/analyze", priority=8),
            QuickAction(id="qa_portfolio", label="组合概览", journey="execution", route="/portfolio/snapshot", priority=7),
        ]

    def get_journey_suggestions(
        self,
        user_id: int,
        last_journey: str | None = None,
        market_state: dict[str, object] | None = None,
    ) -> list[JourneyHint]:
        return [
            JourneyHint(journey=j, label=l, reason="推荐入口")
            for j, l in _JOURNEY_HINTS
        ]
