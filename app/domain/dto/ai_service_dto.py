from pydantic import BaseModel
from typing import Dict, Any, List

class AIAnalysisResultDTO(BaseModel):
    code: str
    analysis: str

class ResearchReportDTO(BaseModel):
    code: str
    report: str

class DebateResultDTO(BaseModel):
    symbol: str
    decision: str
    votes: List[Dict[str, Any]]

class CommandResultDTO(BaseModel):
    result: str
    command: str
