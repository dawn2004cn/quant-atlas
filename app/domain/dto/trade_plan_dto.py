from pydantic import BaseModel
from typing import Dict, Any, List

class TradePlanDTO(BaseModel):
    symbol: str
    target_price: float
    quantity: int
    total_amount: float
    risk_level: str
    scenario_cards: List[Dict[str, Any]]
    execution_instructions: Dict[str, Any]
