from pydantic import BaseModel


class AnalysisStockRequestDTO(BaseModel):
    code: str
    name: str = ""
    history_prices: list[float] = []

class BatchAnalysisRequestDTO(BaseModel):
    stocks: list[AnalysisStockRequestDTO]
