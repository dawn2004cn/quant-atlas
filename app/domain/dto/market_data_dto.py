from pydantic import BaseModel, Field
from typing import List, Optional, Any


class QuoteDTO(BaseModel):
    code: str
    name: str
    price: float
    change_pct: float
    change_amount: float
    volume: int
    amount: float
    turnover: float

class PanoramaDTO(BaseModel):
    market_status: str
    sentiment_score: float
    gainers: List[QuoteDTO]
    losers: List[QuoteDTO]
    amounts: List[QuoteDTO]
    turnovers: List[QuoteDTO]


class LonghuEntry(BaseModel):
    """Representing a single row from Longhu list."""
    trade_date: str
    code: str
    name: str
    reason: str
    raw: dict[str, Any] = Field(default_factory=dict)
