from __future__ import annotations
"""DTOs for Watchlist services."""


from pydantic import BaseModel, Field


class WatchlistAddSymbolDTO(BaseModel):
    """DTO for adding symbol to watchlist."""
    symbol: str = Field(..., min_length=1, description="Stock symbol")


class WatchlistCreateDTO(BaseModel):
    """DTO for creating a new watchlist."""
    name: str = Field(..., min_length=1, max_length=64, description="Watchlist name")
    description: str = Field(default="", max_length=256, description="Optional description")


class WatchlistUpdateDTO(BaseModel):
    """DTO for updating a watchlist."""
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=256)


class WatchlistAddStockDTO(BaseModel):
    """DTO for adding stock to watchlist."""
    stock_code: str | None = Field(default=None, description="Stock code")
    symbol: str | None = Field(default=None, description="Stock symbol (alias)")
    code: str | None = Field(default=None, description="Stock code (alias)")


class WatchlistRemoveStockDTO(BaseModel):
    """DTO for removing stock from watchlist."""
    stock_code: str | None = Field(default=None, description="Stock code")
    symbol: str | None = Field(default=None, description="Stock symbol (alias)")


class WatchlistBatchAddDTO(BaseModel):
    """DTO for batch adding stocks to watchlist."""
    symbols: list[str] = Field(..., min_length=1, description="List of stock symbols")


class WatchlistBatchRemoveDTO(BaseModel):
    """DTO for batch removing stocks from watchlist."""
    symbols: list[str] = Field(..., min_length=1, description="List of stock symbols")
