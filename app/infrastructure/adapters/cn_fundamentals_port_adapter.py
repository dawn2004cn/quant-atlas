from __future__ import annotations
"""Infrastructure adapter for ``CnFundamentalsPort``."""

from typing import Any

from app.domain.ports.cn_fundamentals_port import CnFundamentalsPort
from app.infrastructure.providers.cn_akshare_fundamentals import CnAkShareFundamentalsProvider


class CnFundamentalsPortAdapter(CnFundamentalsPort):
    """Delegates to ``CnAkShareFundamentalsProvider``."""

    def __init__(self, *, max_table_rows: int | None = None) -> None:
        kwargs: dict[str, Any] = {}
        if max_table_rows is not None:
            kwargs["max_table_rows"] = max_table_rows
        self._provider = CnAkShareFundamentalsProvider(**kwargs)

    def fetch_financial_bundle(self, symbol_input: str) -> dict[str, Any]:
        return self._provider.fetch_financial_bundle(symbol_input)

    def fetch_research_reports(
        self,
        symbol_input: str,
        *,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], str | None]:
        return self._provider.fetch_research_reports(symbol_input, limit=limit)

    def fetch_stock_industry(self, symbol: str) -> str:
        return self._provider.fetch_stock_industry(symbol)
