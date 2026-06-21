from pydantic import BaseModel
from typing import List, Optional

class ManagerStatsDTO(BaseModel):
    equity: float
    return_pct: float
    holdings_count: int
    last_update: Optional[str] = None

class StrategyPerformanceDTO(BaseModel):
    active_managers: int
    avg_return: float

class ManagerDTO(BaseModel):
    manager_id: str
    name: str
    return_pct: float
    equity: float
    period: str


class ManagerRow(BaseModel):
    manager_id: str
    strategy_id: str
    name: str
    bio: str
    cohort: str
    active: bool
    tagline: str
    specialty: str
