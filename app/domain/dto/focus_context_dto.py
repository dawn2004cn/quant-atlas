from __future__ import annotations

from pydantic import BaseModel, Field


class FocusShareLinkDTO(BaseModel):
    page: str
    label: str
    href: str


class FocusContextDTO(BaseModel):
    symbol: str = ""
    market: str = "CN"
    query_string: str = ""
    share_links: list[FocusShareLinkDTO] = Field(default_factory=list)


__all__ = ["FocusContextDTO", "FocusShareLinkDTO"]
