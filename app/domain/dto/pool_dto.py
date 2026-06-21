from pydantic import BaseModel
from typing import List, Dict, Any

class PoolItemDTO(BaseModel):
    rank: int
    code: str
    name: str
    score: float
    change_pct: float
    price: float
    status: str
    reason: str

class PoolResponseDTO(BaseModel):
    market: str
    generated_at: str
    count: int
    pool: List[PoolItemDTO]
