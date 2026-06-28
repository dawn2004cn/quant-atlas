from __future__ import annotations

"""Standardized market data ingestion ports."""


from abc import ABC, abstractmethod

import pandas as pd


class IMarketDataIngestor(ABC):
    """Contract for all market data ingestion adapters."""

    @abstractmethod
    async def fetch_data(self, *args, **kwargs) -> pd.DataFrame | None:
        """Fetch market data from source asynchronously."""
        raise NotImplementedError
