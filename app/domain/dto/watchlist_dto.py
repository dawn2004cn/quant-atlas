from pydantic import BaseModel
from typing import List

class QuoteItem(BaseModel):
    code: str
    name: str
    price: float
    change_pct: float
    change_amount: float
    volume: int
    amount: float
    turnover: float
    industry: str

class WatchlistResponse(BaseModel):
    items: List[QuoteItem]
    total: int
    page: int
    page_size: int
    pages: int
