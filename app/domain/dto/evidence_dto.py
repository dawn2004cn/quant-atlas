from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class EvidenceType(Enum):
    ALPHA_FACTOR = "alpha_factor"
    TRADE_SIGNAL = "trade_signal"
    RISK_CHECK = "risk_check"
    OTHER = "other"

class EvidenceDTO(BaseModel):
    id: str
    type: EvidenceType
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] | None = None
