from __future__ import annotations
"""API Response Envelopes and DTOs."""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class ResponseEnvelope(BaseModel, Generic[T]):
    """Standard API response structure."""
    code: int = 200
    data: T | None = None
    message: str = "success"
    meta: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success(cls, data: T, meta: dict[str, Any] | None = None) -> ResponseEnvelope[T]:
        return cls(data=data, meta=meta or {})

    @classmethod
    def error(cls, message: str, code: int = 500) -> ResponseEnvelope[Any]:
        return cls(code=code, message=message)

class SwarmRunRequest(BaseModel):
    symbol: str
    topic: str | None = None
    preset: str = "investment_committee"
