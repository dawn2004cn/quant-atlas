from datetime import datetime

from pydantic import BaseModel, Field


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
    support_levels: list[float]
    resistance_levels: list[float]
    current_position: str

class WatchlistRiskReportDTO(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now)
    symbols_analyzed: int
    alerts_count: int
    summary: RiskLevel
    alerts: list[RiskAlertDTO]
