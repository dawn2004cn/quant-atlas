from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime

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
    user_id: Optional[int] = None
    reasoning: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
