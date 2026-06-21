from __future__ import annotations
"""DTO validators using Pydantic."""


from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator, model_validator, ValidationError

from app.core.logger import get_logger

logger = get_logger(__name__)


class StockCodeValidator:
    """Validator for stock codes."""

    @staticmethod
    def validate(code: str) -> bool:
        """Validate stock code format."""
        if not code:
            return False

        if len(code) == 6 and code.isdigit():
            return True

        if code.startswith(("sh", "sz", "SH", "SZ")) and len(code) == 8:
            return code[2:].isdigit()

        return False

    @staticmethod
    def normalize(code: str) -> str:
        """Normalize stock code to 6-digit format."""
        if not code:
            return ""

        code = code.strip().lower()

        if len(code) == 6 and code.isdigit():
            return code

        if code.startswith(("sh", "sz")) and len(code) == 8:
            return code[2:]

        return code


class PriceValidator:
    """Validator for price values."""

    @staticmethod
    def validate(price: float) -> bool:
        """Validate price is reasonable."""
        return 0 < price < 1000000

    @staticmethod
    def validate_change(change: float) -> bool:
        """Validate price change is reasonable."""
        return -100 < change < 100


class QuantityValidator:
    """Validator for quantity values."""

    @staticmethod
    def validate(quantity: int) -> bool:
        """Validate quantity is reasonable."""
        return 0 < quantity < 100000000


class DateValidator:
    """Validator for date values."""

    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validate date string format."""
        try:
            datetime.fromisoformat(date_str)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def parse_date(date_str: str) -> datetime | None:
        """Parse date string to datetime."""
        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None


class StockRequestDTO(BaseModel):
    """Stock request DTO with validation."""

    code: str
    name: str = ""
    market: str = "CN"

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not StockCodeValidator.validate(v):
            raise ValueError(f"Invalid stock code: {v}")
        return StockCodeValidator.normalize(v)

    @field_validator("market")
    @classmethod
    def validate_market(cls, v: str) -> str:
        if v not in ["CN", "HK", "US"]:
            raise ValueError(f"Invalid market: {v}")
        return v.upper()


class QuoteRequestDTO(BaseModel):
    """Quote request DTO with validation."""

    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not StockCodeValidator.validate(v):
            raise ValueError(f"Invalid stock code: {v}")
        return StockCodeValidator.normalize(v)


class TradeRequestDTO(BaseModel):
    """Trade request DTO with validation."""

    code: str
    side: str
    quantity: int
    price: float

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not StockCodeValidator.validate(v):
            raise ValueError(f"Invalid stock code: {v}")
        return StockCodeValidator.normalize(v)

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in ["buy", "sell", "long", "short"]:
            raise ValueError(f"Invalid side: {v}")
        return v.lower()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if not QuantityValidator.validate(v):
            raise ValueError(f"Invalid quantity: {v}")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if not PriceValidator.validate(v):
            raise ValueError(f"Invalid price: {v}")
        return v


class AnalysisRequestDTO(BaseModel):
    """Analysis request DTO with validation."""

    code: str
    indicators: list[str] = []

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not StockCodeValidator.validate(v):
            raise ValueError(f"Invalid stock code: {v}")
        return StockCodeValidator.normalize(v)

    @model_validator(mode="after")
    def validate_indicators(self):
        valid_indicators = ["ma", "rsi", "macd", "kdj", "boll", "atr"]
        for ind in self.indicators:
            if ind.lower() not in valid_indicators:
                logger.warning(f"Unknown indicator: {ind}")
        return self


class BacktestRequestDTO(BaseModel):
    """Backtest request DTO with validation."""

    codes: list[str]
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003

    @field_validator("codes", mode="before")
    @classmethod
    def validate_codes(cls, v: list) -> list:
        if not v:
            raise ValueError("Codes cannot be empty")
        return [StockCodeValidator.normalize(c) for c in v if StockCodeValidator.validate(c)]

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_dates(cls, v: str) -> str:
        if not DateValidator.validate_date(v):
            raise ValueError(f"Invalid date format: {v}")
        return v

    @field_validator("initial_capital")
    @classmethod
    def validate_capital(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Initial capital must be positive")
        return v

    @field_validator("commission_rate")
    @classmethod
    def validate_commission(cls, v: float) -> float:
        if v < 0 or v > 0.01:
            raise ValueError("Commission rate must be between 0 and 1%")
        return v


class RiskAssessmentRequestDTO(BaseModel):
    """Risk assessment request DTO."""

    code: str
    position_value: float
    portfolio_value: float
    sector: str = "default"

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not StockCodeValidator.validate(v):
            raise ValueError(f"Invalid stock code: {v}")
        return StockCodeValidator.normalize(v)

    @field_validator("position_value", "portfolio_value")
    @classmethod
    def validate_values(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v


def validate_request(model_class: type[BaseModel], data: dict) -> BaseModel | None:
    """Validate request data against DTO model."""
    try:
        return model_class(**data)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return None


__all__ = [
    "StockCodeValidator",
    "PriceValidator",
    "QuantityValidator",
    "DateValidator",
    "StockRequestDTO",
    "QuoteRequestDTO",
    "TradeRequestDTO",
    "AnalysisRequestDTO",
    "BacktestRequestDTO",
    "RiskAssessmentRequestDTO",
    "validate_request",
]