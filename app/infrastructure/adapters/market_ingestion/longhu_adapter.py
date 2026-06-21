"""Adapter for fetching Longhu Bang data."""

import asyncio
import logging
import pandas as pd
from app.domain.ports.market_data_ports import IMarketDataIngestor


from app.core.logger import get_logger

logger = get_logger(__name__)

class LonghuIngestorAdapter(IMarketDataIngestor):
    """Adapter for fetching Longhu Bang data from AkShare."""

    async def fetch_data(self, start_date: str, end_date: str) -> pd.DataFrame | None:
        return await asyncio.to_thread(self._sync_fetch, start_date, end_date)

    def _sync_fetch(self, start_date: str, end_date: str) -> pd.DataFrame | None:
        try:
            import akshare as ak
            return ak.stock_lhb_detail_em(start_date, end_date)
        except Exception as e:
            logger.error(f"Error fetching Longhu data from AkShare: {e}")
            return None
