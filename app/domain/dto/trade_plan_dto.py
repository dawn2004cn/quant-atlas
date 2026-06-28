from typing import Any

from pydantic import BaseModel


class TradePlanDTO(BaseModel):
    symbol: str
    target_price: float
    quantity: int
    total_amount: float
    risk_level: str
    scenario_cards: list[dict[str, Any]]
    execution_instructions: dict[str, Any]
