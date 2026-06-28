from pydantic import BaseModel
from typing import Any

class AIAnalysisResultDTO(BaseModel):
    code: str
    analysis: str

class ResearchReportDTO(BaseModel):
    code: str
    report: str

class DebateResultDTO(BaseModel):
    symbol: str
    decision: str
    votes: list[dict[str, Any]]

class CommandResultDTO(BaseModel):
    result: str
    command: str
