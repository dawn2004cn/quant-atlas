from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class AggregatedQuoteDTO(BaseModel):
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    source: str
    timestamp: datetime = Field(default_factory=datetime.now)

class MarketStatusDTO(BaseModel):
    source_statuses: dict[str, str]
