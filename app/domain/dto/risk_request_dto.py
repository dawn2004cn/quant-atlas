from pydantic import BaseModel, Field
from typing import Optional


class RiskCheckOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, description="Stock symbol")
    side: str = Field(..., pattern=r"^(buy|sell)$", description="Order side: buy or sell")
    quantity: int = Field(default=0, ge=0, description="Order quantity")
    price: float = Field(default=0.0, ge=0.0, description="Order price")
    account_id: str = Field(default="default", description="Account identifier")
    total_equity: float = Field(default=100000.0, ge=0.0, description="Total account equity")


class RiskCheckBatchRequest(BaseModel):
    orders: list[dict] = Field(..., min_length=1, description="List of orders to check")


class RiskVolatilityTargetRequest(BaseModel):
    symbol: str = Field(..., min_length=1, description="Stock symbol")
    target_vol: float = Field(default=0.15, gt=0.0, description="Target volatility")
    lookback: int = Field(default=60, ge=1, description="Lookback period in days")
    total_equity: float = Field(default=100000.0, ge=0.0, description="Total account equity")


class RiskKellyRequest(BaseModel):
    win_rate: float = Field(default=0.5, ge=0.0, le=1.0, description="Historical win rate")
    avg_win: float = Field(default=1.0, ge=0.0, description="Average win amount")
    avg_loss: float = Field(default=1.0, ge=0.0, description="Average loss amount")
    total_equity: float = Field(default=100000.0, ge=0.0, description="Total account equity")
    fraction: float = Field(default=0.25, ge=0.0, le=1.0, description="Kelly fraction multiplier")
