from __future__ import annotations

"""DTOs for Investment Manager services."""


from pydantic import BaseModel, Field


class LeaderboardQueryDTO(BaseModel):
    """DTO for leaderboard query."""
    cohort: str | None = Field(default=None, description="Filter by cohort")
    active_only: bool = Field(default=True, description="Show active only")
    limit: int = Field(default=50, ge=1, le=200, description="Result limit")


class ManagerProfileUpdateDTO(BaseModel):
    """DTO for updating manager profile."""
    name: str | None = Field(default=None, max_length=64)
    bio: str | None = Field(default=None, max_length=500)
    tagline: str | None = Field(default=None, max_length=128)
    specialty: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = None


class ManagerDeployDTO(BaseModel):
    """DTO for deploying a manager strategy."""
    strategy_id: str = Field(..., description="Strategy ID")
    name: str = Field(..., min_length=1, max_length=64, description="Manager name")
    bio: str = Field(default="", max_length=500, description="Manager bio")
    cohort: str = Field(..., description="Cohort identifier")
    specialty: str = Field(default="", max_length=64, description="Specialty")
