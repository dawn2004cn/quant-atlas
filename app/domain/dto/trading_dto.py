from pydantic import BaseModel
from typing import List, Dict, Any

class BotStatusDTO(BaseModel):
    running_bots: List[str]
    open_trades_count: int

class BotActionResponseDTO(BaseModel):
    status: str
    strategy: str
    symbol: str

class BotDetailDTO(BaseModel):
    running: bool
    strategy: str
    symbol: str
