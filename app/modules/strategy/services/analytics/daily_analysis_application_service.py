from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Daily analysis and reporting service."""


import asyncio
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)


class DailyAnalysisApplicationService:
    """Drive daily automated analysis flow."""

    def __init__(self, agents_service, market_narrative_service=None):
        self._agents_service = agents_service
        self._narrative_service = market_narrative_service

    async def run_daily_watchlist_analysis(self, user_id: int) -> GenericResponseDTO:
        """Run daily analysis for user's watchlist."""
        logger.info(f"Starting daily watchlist analysis for user {user_id}...")
        watchlist = []
        if self._agents_service and hasattr(self._agents_service, '_watchlist_service'):
            watchlist = self._agents_service._watchlist_service.list_symbols(user_id=user_id)

        reports = []
        for ticker in watchlist:
            logger.info(f"Analyzing ticker: {ticker}")
            result = await self._agents_service.run_research(
                ticker=ticker,
                query="请给出今日决策仪表盘分析。",
                user_id=user_id,
            )
            if result.get("ok"):
                reports.append({
                    "ticker": ticker,
                    "dashboard": result.get("decision_dashboard", "分析失败"),
                })

        return {
            "status": "success",
            "count": len(reports),
            "reports": reports,
            "timestamp": datetime.now().isoformat(),
        }

    async def run_market_review(self, market: MarketCode) -> str:
        """Run market-wide daily review."""
        logger.info(f"Generating {market.value} market review...")
        return "Market review placeholder"