from __future__ import annotations

"""DTOs for Investment Manager services."""


from pydantic import BaseModel


class InvestmentManagerDTO(BaseModel):
    """Complete investment manager data."""
    manager_id: str
    strategy_id: str
    name: str
    bio: str = ""
    cohort: str
    deployed_at: str | None = None
    active: int = 0
    tagline: str = ""
    specialty: str = ""
    avatar_url: str = ""
    entry_time_display: str = ""


class ManagerProfileDTO(BaseModel):
    """Public-facing manager info."""
    manager_id: str
    strategy_id: str
    name: str
    bio: str
    cohort: str
    deployed_at: str | None = None
    active: int = 0
    tagline: str = ""
    specialty: str = ""
    avatar_url: str = ""
    entry_time_display: str = ""


class LeaderboardItemDTO(BaseModel):
    """Aggregated stats for the leaderboard."""
    manager_id: str
    name: str
    cohort: str
    strategy_id: str
    active: int
    tagline: str
    specialty: str
    avatar_url: str
    entry_time_display: str
    return_pct: float
    equity: float
    nav_date: str
    trade_count: int
    last_trade_date: str
