from __future__ import annotations
"""Command objects for market data operations."""

from pydantic import BaseModel
from datetime import datetime

class IngestMarketDataCommand(BaseModel):
    """Command to ingest market data."""
    start_date: datetime
    end_date: datetime
    data_source: str = "default"
    update_meta: bool = False
