from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RiskLevel(BaseModel):
    high_risk: int
    medium_risk: int
    low_risk: int
    opportunities: int

class RiskAlertDTO(BaseModel):
    symbol: str
    risk_level: str
    signal: str
    reasoning: str
    support_levels: List[float]
    resistance_levels: List[float]
    current_position: str

class WatchlistRiskReportDTO(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now)
    symbols_analyzed: int
    alerts_count: int
    summary: RiskLevel
    alerts: List[RiskAlertDTO]
