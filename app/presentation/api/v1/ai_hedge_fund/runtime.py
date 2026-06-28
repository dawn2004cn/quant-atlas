"""Shared runtime for AI hedge fund HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass

from app.integration.ai_hedge_fund.service import AIHedgeFundIntegrationService
from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class AiHedgeFundRuntime:
    ctx: ApiV1Context

    @property
    def service(self) -> AIHedgeFundIntegrationService:
        return AIHedgeFundIntegrationService(
            investment_committee_service=self.ctx.investment_committee_service,
        )
