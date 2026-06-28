from __future__ import annotations

from app.domain.risk.risk_companion_models import EmpathyTone, RiskCompanionMessage, SentimentProfile
from app.domain.risk.risk_companion_models import RiskCompanionService as BaseRiskCompanionService


class RiskCompanionService(BaseRiskCompanionService):
    def compose_message(self, user_id: int, headline: str = "Risk reminder") -> RiskCompanionMessage:
        return RiskCompanionMessage(
            tone=EmpathyTone.CALM_REASSURING,
            headline=headline,
            body="No elevated risk signal detected.",
            actionable_suggestion="Continue following your trade plan.",
            risk_level="LOW",
        )

    def get_profile(self, user_id: int) -> SentimentProfile:
        return self.assess_user_risk_profile(user_id)
