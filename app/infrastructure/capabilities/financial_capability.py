from __future__ import annotations

"""A-share financial & research report capabilities."""


from typing import Any

from app.domain.capabilities.base import BaseCapability
from app.infrastructure.capabilities.registry import capability


@capability("cn_financial_bundle")
class FinancialBundleCapability(BaseCapability):
    """A-share financial bundle (balance sheet, income, cash flow)."""

    capability_name = "cn_financial_bundle"

    def __init__(self, **services: Any) -> None:
        self._fundamental_provider = services.get("fundamental_provider")

    def execute(self, symbol: str) -> Any:
        return self._fundamental_provider.fetch_financial_bundle(symbol)


@capability("cn_research_reports")
class ResearchReportsCapability(BaseCapability):
    """A-share research / 研报 reports."""

    capability_name = "cn_research_reports"

    def __init__(self, **services: Any) -> None:
        self._fundamental_provider = services.get("fundamental_provider")

    def execute(
        self, symbol: str, limit: int = 30
    ) -> tuple[list[dict[str, Any]], str | None]:
        return self._fundamental_provider.fetch_research_reports(symbol, limit=limit)
