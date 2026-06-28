from __future__ import annotations

"""Example DTOs for API request validation."""


from pydantic import BaseModel, Field, field_validator


class QuoteRequestDTO(BaseModel):
    """Request DTO for market quotes endpoint."""
    market: str = Field(default="CN", description="Market code: CN, HK, US")
    symbols: list[str] = Field(default_factory=list, description="List of stock symbols")
    limit: int = Field(default=6000, ge=1, le=10000, description="Max results")

    @field_validator('market')
    @classmethod
    def validate_market(cls, v: str) -> str:
        return v.upper()


class StockSearchRequestDTO(BaseModel):
    """Request DTO for stock search."""
    query: str = Field(min_length=1, max_length=50)
    market: str = Field(default="CN")
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator('query')
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        return v.strip()


class PortfolioRequestDTO(BaseModel):
    """Request DTO for portfolio operations."""
    user_id: str
    action: str = Field(description="buy, sell, adjust")
    symbol: str
    quantity: float = Field(gt=0, description="Quantity must be positive")
    price: float | None = Field(default=None, description="Limit price")

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {'buy', 'sell', 'adjust'}
        if v.lower() not in allowed:
            raise ValueError(f'action must be one of: {allowed}')
        return v.lower()


__all__ = ["QuoteRequestDTO", "StockSearchRequestDTO", "PortfolioRequestDTO"]
