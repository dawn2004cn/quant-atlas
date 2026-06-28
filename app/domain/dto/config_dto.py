from typing import Any

from pydantic import BaseModel


class ConfigEntryDTO(BaseModel):
    key: str
    value: Any
    default: Any
    age_seconds: float
    last_updated: str
