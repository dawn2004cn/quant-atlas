from __future__ import annotations

"""Command objects for market data operations."""

from datetime import datetime

from pydantic import BaseModel


class IngestMarketDataCommand(BaseModel):
    """Command to ingest market data."""
    start_date: datetime
    end_date: datetime
    data_source: str = "default"
    update_meta: bool = False
