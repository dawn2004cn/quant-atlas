from pydantic import BaseModel
from typing import Any

class ConfigEntryDTO(BaseModel):
    key: str
    value: Any
    default: Any
    age_seconds: float
    last_updated: str
