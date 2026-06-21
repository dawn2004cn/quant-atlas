from __future__ import annotations
"""Port for A-share fundamentals via AkShare/Tushare."""

from typing import Any, Protocol


class CnFundamentalsPort(Protocol):
    """Application-facing CN fundamentals access."""

    def fetch_financial_bundle(self, symbol_input: str) -> dict[str, Any]:
        ...

    def fetch_research_reports(
        self,
        symbol_input: str,
        *,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], str | None]:
        ...

    def fetch_stock_industry(self, symbol: str) -> str:
        ...
