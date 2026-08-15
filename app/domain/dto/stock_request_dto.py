from pydantic import BaseModel, Field


class StockSearchRequest(BaseModel):
    q: str = Field(default="", description="Search query")
    limit: int = Field(default=20, ge=1, le=100, description="Max results")
    market: str = Field(default="CN", description="Market code")
    tags: str = Field(default="", description="Comma or + separated tags")
    mode: str = Field(default="", description="Search mode")
    strict: str = Field(default="", description="Strict matching flag")


class StockQuoteRequest(BaseModel):
    symbol: str = Field(..., min_length=1, description="Stock symbol")
    market: str = Field(default="CN", description="Market code")


class StockHistoryRequest(BaseModel):
    start: str = Field(..., description="Start date YYYY-MM-DD")
    end: str = Field(..., description="End date YYYY-MM-DD")
    max_points: int = Field(default=0, ge=0, le=5000, description="Max data points")
    width: int = Field(default=0, ge=0, le=4000, description="Chart width for sampling")
    adjust: str = Field(default="qfq", description="Price adjust: qfq | hfq | raw")


class StockAnalysisRequest(BaseModel):
    user_hypothesis: str | None = Field(default=None, description="User hypothesis text")
    hypothesis_id: str | None = Field(default=None, description="Hypothesis ID")
