from __future__ import annotations
"""Pydantic v2 schemas for Agent services."""


from typing import Any, List, Optional
from pydantic import BaseModel, Field

class SwarmRunRequest(BaseModel):
    preset: str = Field(default="investment_committee")
    symbol: str
    topic: Optional[str] = None
    context: Optional[dict[str, Any]] = None

class SwarmRunResponse(BaseModel):
    id: str
    status: str
    preset_name: str
    created_at: str

class ExpertSkillResponse(BaseModel):
    name: str
    content: str
    status: str = "ok"
    error: Optional[str] = None
