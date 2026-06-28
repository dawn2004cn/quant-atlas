from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
