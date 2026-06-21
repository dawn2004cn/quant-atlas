from pydantic import BaseModel
from typing import List

class AnalysisStockRequestDTO(BaseModel):
    code: str
    name: str = ""
    history_prices: List[float] = []

class BatchAnalysisRequestDTO(BaseModel):
    stocks: List[AnalysisStockRequestDTO]
