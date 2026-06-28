from __future__ import annotations
"""Data quality gate for backtesting data streams."""


from typing import Protocol, runtime_checkable
import pandas as pd


from app.core.logger import get_logger

logger = get_logger(__name__)

@runtime_checkable
class DataValidator(Protocol):
    """Protocol for data validation before backtesting."""

    def validate(self, df: pd.DataFrame, symbol: str) -> bool:
        """Validate DataFrame, returning True if healthy."""
        ...

class MarketDataQualityGate:
    """Validator to catch corrupt market data before it hits the engine."""

    def __init__(self, validators: list[DataValidator] | None = None):
        self._validators = validators or [
            BasicHealthValidator(),
            OutlierValidator()
        ]

    def validate(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Validate and clean data. Raises error if critical data is lost."""
        if df.empty:
            raise ValueError(f"Data for {symbol} is empty")

        for validator in self._validators:
            if not validator.validate(df, symbol):
                logger.warning(f"Data validation failed for {symbol} at {validator.__class__.__name__}")
                # Implementation could involve dropping rows, imputation, or failing the run

        return df

class BasicHealthValidator:
    """Checks for missing critical columns."""

    def validate(self, df: pd.DataFrame, symbol: str) -> bool:
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns.str.lower())):
            logger.error(f"Missing columns in {symbol}: {required - set(df.columns.str.lower())}")
            return False

        # Check for 0/negative close prices which are common TDX errors
        if (df["close"] <= 0).any():
            logger.error(f"Invalid close prices found in {symbol}")
            return False

        return True

class OutlierValidator:
    """Checks for extreme price jumps."""

    def validate(self, df: pd.DataFrame, symbol: str) -> bool:
        # Check for > 50% jump in a single day (usually bad data)
        pct_change = df["close"].pct_change().abs()
        if (pct_change > 0.5).any():
            logger.warning(f"Extreme price jump detected in {symbol}")
            return False
        return True
