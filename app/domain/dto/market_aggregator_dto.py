from datetime import datetime

from pydantic import BaseModel, Field


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
