from pydantic import BaseModel


class BotStatusDTO(BaseModel):
    running_bots: list[str]
    open_trades_count: int

class BotActionResponseDTO(BaseModel):
    status: str
    strategy: str
    symbol: str

class BotDetailDTO(BaseModel):
    running: bool
    strategy: str
    symbol: str
