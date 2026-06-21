from __future__ import annotations
"""Facade for unified market data access."""

from typing import Any, Dict, List
from app.modules.data.services.basic_market_data_service import BasicMarketDataService
from app.modules.market_data.services.market_service import MarketApplicationService

class MarketDataFacade:
    """Facade for aggregating market data service operations."""

    def __init__(
        self,
        basic_service: BasicMarketDataService,
        market_service: MarketApplicationService,
    ) -> None:
        self._basic_service = basic_service
        self._market_service = market_service

    def get_market_intelligence(self, symbol: str) -> Dict[str, Any]:
        """Unified entry point for comprehensive market intelligence."""
        # Aggregate data from multiple services
        return {
            "quotes": self._market_service.get_quotes([symbol]),
            "longhu": self._basic_service.longhu_for_stock(symbol),
            "fundamentals": self._basic_service.get_tdx_local_cn_snapshot(symbol),
            "intelligence_summary": "Aggregated view completed."
        }
