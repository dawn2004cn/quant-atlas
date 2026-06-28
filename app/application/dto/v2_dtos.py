"""DTOs for API v2 - v1-compatible request/response shapes."""

from typing import Any

from pydantic import BaseModel, Field

# ------------------------------------------------------------------ #
# Stock
# ------------------------------------------------------------------ #

class StockSearchDTO(BaseModel):
    """DTO for stock search."""
    keyword: str = Field(default="", description="Search keyword (name, code)")
    market: str = Field(default="CN", description="Market code")
    sector: str | None = Field(default=None, description="Sector filter")
    limit: int = Field(default=20, ge=1, le=200, description="Max results")


class StockHistoryDTO(BaseModel):
    """DTO for stock history query."""
    market: str = Field(default="CN", description="Market code")
    start_date: str | None = Field(default=None, description="YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="YYYY-MM-DD")
    count: int = Field(default=100, ge=1, le=10000, description="Number of bars")


# ------------------------------------------------------------------ #
# Prediction
# ------------------------------------------------------------------ #

class PredictionRequestDTO(BaseModel):
    """DTO for prediction request."""
    symbol: str = Field(..., min_length=1, description="Stock symbol")
    market: str = Field(default="CN", description="Market code")
    horizon: int = Field(default=10, ge=1, le=252, description="Prediction horizon (trading days)")


# ------------------------------------------------------------------ #
# News
# ------------------------------------------------------------------ #

class NewsRequestDTO(BaseModel):
    """DTO for news retrieval."""
    count: int = Field(default=20, ge=1, le=200, description="Number of news items")


# ------------------------------------------------------------------ #
# Portfolio
# ------------------------------------------------------------------ #

class PortfolioCreateDTO(BaseModel):
    """DTO for creating a portfolio."""
    name: str = Field(..., min_length=1, max_length=128, description="Portfolio name")
    description: str = Field(default="", max_length=512, description="Optional description")
    user_id: int = Field(default=0, ge=0, description="User ID")


class PortfolioDetailDTO(BaseModel):
    """DTO for portfolio detail query."""
    period: str = Field(default="daily", description="Analysis period")
    include_positions: bool = Field(default=True, description="Include positions")


class PortfolioRebalanceDTO(BaseModel):
    """DTO for portfolio rebalance."""
    target_weights: dict[str, float] = Field(
        ..., description="Symbol -> target weight mapping",
    )


# ------------------------------------------------------------------ #
# Common
# ------------------------------------------------------------------ #

class PaginationDTO(BaseModel):
    """Common pagination params."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ListResponseDTO(BaseModel):
    """Standard paginated list response."""
    items: list[Any] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
