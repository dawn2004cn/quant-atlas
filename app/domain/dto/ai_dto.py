from pydantic import BaseModel
from typing import List, Any

class AgentResultDTO(BaseModel):
    agent_id: str
    agent_name: str
    agent_role: str
    agent_avatar: str
    signal: str
    reasoning: str
    metrics: dict[str, Any]
    timestamp: str

class DebateResponseDTO(BaseModel):
    symbol: str
    market: str
    timestamp: str
    steps: List[AgentResultDTO]
    consensus: dict[str, Any]
