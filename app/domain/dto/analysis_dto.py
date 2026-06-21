from pydantic import BaseModel
from typing import List, Optional

class IndicatorDTO(BaseModel):
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    rsi: float = 50.0
    rsi_14: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    kdj_k: float = 50.0
    kdj_d: float = 50.0
    kdj_j: float = 50.0
    boll_upper: float = 0.0
    boll_middle: float = 0.0
    boll_lower: float = 0.0
    atr: float = 0.0

class TrendDTO(BaseModel):
    trend: str
    momentum: float
    ma5: float
    ma20: float

class SupportResistanceDTO(BaseModel):
    support: List[float]
    resistance: List[float]

class FibonacciDTO(BaseModel):
    levels: dict[str, float]
