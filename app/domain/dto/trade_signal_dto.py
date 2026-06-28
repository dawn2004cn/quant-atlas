from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"

class TradeSignalDTO(BaseModel):
    symbol: str
    direction: SignalDirection
    price: float
    quantity: int
    strategy_id: str
    user_id: int | None = None
    reasoning: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
